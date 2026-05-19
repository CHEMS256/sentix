from flask import Flask, render_template_string, request, jsonify, send_file, session, redirect, url_for
import os
import pandas as pd
import re
from pathlib import Path
import uuid
import tempfile
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from langdetect import detect
import warnings
import sqlite3
import datetime
import ast

warnings.filterwarnings("ignore")

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sentix_secret_key_strong_2026")

BASEDIR = Path(__file__).resolve().parent

# Configuration dossiers
if os.environ.get("VERCEL"):
    temp_dir = Path(tempfile.gettempdir())
    app.config["UPLOAD_FOLDER"] = temp_dir / "uploads"
    app.config["RESULT_FOLDER"] = temp_dir / "resultats_analyse"
    DB_PATH = temp_dir / "database.db"
else:
    app.config["UPLOAD_FOLDER"] = BASEDIR / "uploads"
    app.config["RESULT_FOLDER"] = BASEDIR / "resultats_analyse"
    DB_PATH = BASEDIR / "database.db"

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["RESULT_FOLDER"], exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 username TEXT UNIQUE NOT NULL,
                 password TEXT NOT NULL,
                 created_at TEXT
               )''')
    c.execute('''CREATE TABLE IF NOT EXISTS analyses (
                 id INTEGER PRIMARY KEY AUTOINCREMENT,
                 user_id INTEGER,
                 date TEXT,
                 filename TEXT,
                 total_avis INTEGER,
                 langues TEXT,
                 statut TEXT,
                 report_filename TEXT
               )''')
    conn.commit()
    conn.close()

init_db()

# ==================== TEMPLATES ====================
HTML_TEMPLATES = {}

def load_templates():
    templates = ['landing.html', 'index.html', 'login.html', 'register.html',
                 'user_login.html', 'user_dashboard.html', 'admin.html']
   
    for template in templates:
        try:
            file_path = BASEDIR / template
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    HTML_TEMPLATES[template] = f.read()
                print(f"✅ Template chargé : {template}")
            else:
                print(f"❌ Template NON trouvé : {template}")
        except Exception as e:
            print(f"Erreur chargement {template} : {e}")

load_templates()

def get_html_template(name):
    if name in HTML_TEMPLATES and HTML_TEMPLATES[name]:
        return HTML_TEMPLATES[name]
    else:
        return f"""
        <h1 style="color:red; text-align:center; margin-top:100px;">
            ❌ Erreur : Template "{name}" non trouvé<br><br>
            <small>Vérifiez que le fichier existe à la racine du projet</small>
        </h1>
        """

# ==================== CLASSES ANALYSE ====================
class APIIntelligente:
    def detecter_langue(self, texte):
        if not texte or pd.isna(texte):
            return "fr"
        texte_str = str(texte).lower()
        if re.search(r"[\u0600-\u06FF]", texte_str):
            if any(w in texte_str for w in ["زوين", "خير", "بزاف", "مزيان", "خايب"]):
                return "darija"
            return "ar"
        try:
            lang = detect(texte_str)
            return lang if lang in ["fr", "en"] else "fr"
        except:
            return "fr"

def analyser_expression_contextuelle(self, texte, langue=None):
    if not texte:
        return "neutre"
    
    texte = str(texte).lower()
    
    positif = [
        "bon", "excellent", "super", "génial", "parfait", "formidable",
        "satisfait", "content", "heureux", "ravi", "enthousiaste",
        "recommande", "recommande fortement", "à ne pas manquer",
        "fantastic", "brilliant", "impressive", "helpful", "positive",
        "wonderful", "nice", "awesome", "amazing",
        "زوين", "مزيان", "إيجابي", "جميل", "رائع", "ممتاز", "مذهل",
        "لطيف", "مشكور", "أحسنت", "good", "great"
    ]
    
    negatif = [
        "mauvais", "nul", "horrible", "خايب", "bad", "worst",
        "déçu", "insatisfait", "médiocre", "inacceptable", "lent",
        "inutile", "incompétent", "inattentif", "désagréable", "impoli",
        "problème", "dysfonctionnement", "erreur", "arnaque",
        "terrible", "awful", "disappointing", "unhelpful", "boring",
        "ennuyeux", "confusing", "weak", "unacceptable",
        "سيء", "سيئة", "ضعيف", "غير جيد", "فاشل", "مزعج", "خطير",
        "لا يعجبني", "غير راضٍ", "تجربة سيئة", "جودة سيئة", "غاضب",
        "كارثي", "مخيب للآمال", "غير مقبول", "للأسف", "شكوى"
    ]
    
    score_pos = sum(1 for mot in positif if mot in texte)
    score_neg = sum(1 for mot in negatif if mot in texte)
    
    score = score_pos - score_neg
    
    if score > 0:
        return "positif"
    elif score < 0:
        return "negatif"
    else:
        return "neutre"


class AnalyseurSentimentsNLPCloud:
    def __init__(self):
        self.api = APIIntelligente()

    def analyser_texte(self, texte):
        if len(str(texte).strip()) < 3:
            return "neutre"
        langue = self.api.detecter_langue(texte)
        return self.api.analyser_expression_contextuelle(texte, langue)

    def analyser_batch(self, df, col):
        df = df.copy()
        df["texte"] = df[col].fillna("").astype(str)
        df = df[df["texte"].str.len() > 2].reset_index(drop=True)
        if df.empty:
            return pd.DataFrame()
        df["langue"] = df["texte"].apply(self.api.detecter_langue)
        df["sentiment_final"] = df["texte"].apply(self.analyser_texte)
        return df.rename(columns={col: "avis"})[["avis", "langue", "sentiment_final"]]

class GestionnaireExcel:
    def __init__(self):
        self.analyseur = AnalyseurSentimentsNLPCloud()

    def detecter_colonne_avis(self, df):
        for c in df.columns:
            if any(word in str(c).lower() for word in ["avis", "comment", "text", "review", "message"]):
                return c
        return df.columns[0]

    def analyser_fichier_excel(self, path, output_dir):
        output_dir = Path(output_dir)
        if path.endswith((".xlsx", ".xls")):
            df = pd.read_excel(path)
        else:
            df = pd.read_csv(path, sep=None, engine='python')
       
        if df.empty:
            return None, None
        col = self.detecter_colonne_avis(df)
        df_res = self.analyseur.analyser_batch(df, col)
        if df_res.empty:
            return None, None
           
        out_path = output_dir / f"analyse_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df_res.to_excel(out_path, index=False)
        return df_res, out_path

gestionnaire = GestionnaireExcel()

# ====================== ROUTES ======================

@app.route("/")
def landing():
    return render_template_string(get_html_template("landing.html"))

@app.route("/analyse")
def analyse_page():
    return render_template_string(get_html_template("index.html"))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or not password:
            return render_template_string(get_html_template("register.html"), error="Tous les champs sont requis")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        try:
            hashed = generate_password_hash(password)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            c.execute("INSERT INTO users (username, password, created_at) VALUES (?, ?, ?)",
                      (username, hashed, now))
            conn.commit()
            return redirect(url_for("user_login"))
        except sqlite3.IntegrityError:
            return render_template_string(get_html_template("register.html"), error="Nom d'utilisateur déjà pris")
        finally:
            conn.close()
    return render_template_string(get_html_template("register.html"), error=None)

@app.route("/user_login", methods=["GET", "POST"])
def user_login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT id, password FROM users WHERE username = ?", (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session["user_id"] = user[0]
            session["username"] = username
            return redirect(url_for("user_dashboard"))
        return render_template_string(get_html_template("user_login.html"), error="Identifiants incorrects")
    return render_template_string(get_html_template("user_login.html"), error=None)

@app.route("/user_dashboard")
def user_dashboard():
    if not session.get("user_id"):
        return redirect(url_for("user_login"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, date, filename, total_avis, langues, report_filename FROM analyses WHERE user_id = ? ORDER BY id DESC", 
              (session["user_id"],))
    analyses = c.fetchall()
    conn.close()
    return render_template_string(get_html_template("user_dashboard.html"), 
                                  username=session.get("username", "Utilisateur"), 
                                  analyses=analyses)

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        if username == "admin" and password == "chems123":
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template_string(get_html_template("login.html"), error="Identifiants incorrects")
    return render_template_string(get_html_template("login.html"), error=None)

@app.route("/admin")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect(url_for("login"))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, date, filename, total_avis, langues, statut, report_filename FROM analyses ORDER BY id DESC LIMIT 100")
    analyses = c.fetchall()
    conn.close()
    historique = [list(row) for row in analyses]
    return render_template_string(get_html_template("admin.html"), historique=historique)

@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "Aucun fichier envoyé"}), 400
   
    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Fichier vide"}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{uuid.uuid4()}_{filename}"
    filepath = os.path.join(app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(filepath)

    try:
        df_result, result_path = gestionnaire.analyser_fichier_excel(filepath, app.config["RESULT_FOLDER"])
        if os.path.exists(filepath):
            os.remove(filepath)

        if df_result is None or df_result.empty:
            return jsonify({"error": "Aucun avis valide trouvé"}), 400

        total = len(df_result)
        sentiments = df_result['sentiment_final'].value_counts().to_dict()
        langues = df_result['langue'].value_counts().to_dict()
        preview = df_result[['avis', 'langue', 'sentiment_final']].head(50).to_dict(orient='records')

        # ==================== RAPPORT HTML AMÉLIORÉ ====================
        report_filename = f"rapport_{uuid.uuid4().hex[:8]}.html"
        report_filepath = os.path.join(app.config["RESULT_FOLDER"], report_filename)

        html_content = f"""
        <!DOCTYPE html>
        <html lang="fr">
        <head>
            <meta charset="UTF-8">
            <title>Rapport d'Analyse - Sentix</title>
            <style>
                body {{ font-family: 'Inter', sans-serif; background: #0f172a; color: #e2e8f0; padding: 40px; margin: 0; }}
                .container {{ max-width: 1000px; margin: auto; background: #1e2937; padding: 40px; border-radius: 20px; border: 1px solid #334155; }}
                h1 {{ color: #818cf8; text-align: center; margin-bottom: 8px; }}
                .subtitle {{ text-align: center; color: #94a3b8; margin-bottom: 40px; }}
                .stats {{ display: flex; justify-content: center; gap: 25px; flex-wrap: wrap; margin: 40px 0; }}
                .stat-box {{ 
                    background: #334155; 
                    padding: 25px 30px; 
                    border-radius: 16px; 
                    text-align: center; 
                    min-width: 160px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                }}
                .stat-box h2 {{ margin: 0; font-size: 2.8rem; }}
                .neutre {{ color: #fbbf24; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 30px; }}
                th, td {{ padding: 14px; text-align: left; border-bottom: 1px solid #475569; }}
                th {{ background: #334155; color: #c4d0ff; }}
                ul {{ line-height: 2.4; }}
                li {{ margin-bottom: 10px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>📊 Rapport d'Analyse Sentix</h1>
                <p class="subtitle">Généré le {datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')}</p>
                
                <div class="stats">
                    <div class="stat-box">
                        <h2>{total}</h2>
                        <p>Total Avis</p>
                    </div>
                    <div class="stat-box">
                        <h2 style="color:#34d399;">{sentiments.get('positif', 0)}</h2>
                        <p>Positifs</p>
                    </div>
                    <div class="stat-box">
                        <h2 style="color:#f87171;">{sentiments.get('negatif', 0)}</h2>
                        <p>Négatifs</p>
                    </div>
                    <div class="stat-box">
                        <h2 class="neutre">{sentiments.get('neutre', 0)}</h2>
                        <p>Neutres</p>
                    </div>
                </div>

                <h2>🌍 Langues détectées</h2>
                <ul style="color:#94a3b8; font-size:1.1rem;">
                    {"".join([f"<li><strong>{lang.upper()}</strong> : {count} avis</li>" for lang, count in langues.items()])}
                </ul>
            </div>
        </body>
        </html>
        """

        with open(report_filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        date_now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("""INSERT INTO analyses 
                     (user_id, date, filename, total_avis, langues, statut, report_filename)
                     VALUES (?, ?, ?, ?, ?, ?, ?)""",
                  (session.get("user_id"), date_now, filename, total, str(langues), "Succès", report_filename))
        conn.commit()
        conn.close()

        return jsonify({
            "status": "success",
            "total": total,
            "distribution": sentiments,
            "langues": langues,
            "preview": preview,
            "download_url": f"/download/{result_path.name}",
            "report_url": f"/download/{report_filename}"
        })

    except Exception as e:
        if os.path.exists(filepath):
            os.remove(filepath)
        return jsonify({"error": str(e)}), 500

@app.route("/download/<filename>")
def download_file(filename):
    try:
        safe_filename = secure_filename(filename)
        filepath = os.path.join(app.config["RESULT_FOLDER"], safe_filename)
        
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True, download_name=filename)
        
        # Recherche alternative
        for file in Path(app.config["RESULT_FOLDER"]).glob("*"):
            if safe_filename in file.name or filename in file.name:
                return send_file(file, as_attachment=True, download_name=file.name)
        
        return jsonify({"error": f"Fichier non trouvé : {filename}"}), 404
            
    except Exception as e:
        print(f"❌ Erreur download: {e}")
        return jsonify({"error": "Erreur lors du téléchargement du fichier"}), 500

@app.route("/user_logout")
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

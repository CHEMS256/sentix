# Sentix – Analyseur de sentiments multilingue

![Version](https://img.shields.io/badge/version-2.0-blue)
![Python](https://img.shields.io/badge/python-3.11-green)
![Flask](https://img.shields.io/badge/Flask-2.0-red)
![Docker](https://img.shields.io/badge/Docker-ready-blue)

**Sentix** est une application web d’analyse automatique des sentiments (opinion mining) capable de traiter des avis clients en **français, anglais, arabe standard et darija (arabe marocain)**. Elle offre une interface intuitive, la gestion d’utilisateurs avec historique personnel, un tableau de bord administrateur, et génère des rapports HTML exploitables.

---

## ✨ Fonctionnalités principales

- **🌍 Multilingue** : Détection automatique de la langue (fr, en, ar, darija) et analyse adaptée.
- **📁 Traitement batch** : Import de fichiers Excel (`.xlsx`, `.xls`) ou CSV, jusqu’à 16 Mo.
- **🤖 Moteur hybride** :
  - Appel à l’API NLPCloud pour le français (modèle neuronal).
  - Analyse par lexiques + négations + émojis pour les autres langues (dont darija).
- **👤 Gestion d’utilisateurs** :
  - Inscription / connexion sécurisée (mots de passe hachés).
  - Historique personnel des analyses téléchargeables.
- **👑 Administration** : Supervision de toutes les analyses effectuées (compte `admin`).
- **📊 Rapports** : Génération d’un fichier Excel enrichi (avis, langue, sentiment) et d’un rapport HTML récapitulatif (statistiques, répartition par langue).
- **🐳 Prêt pour Docker** : Image légère, persistance des données via volume, limitation des ressources.
- **☁️ Déployable sur Vercel** (serverless) ou tout VPS.

---

## 🧱 Architecture technique

| Composant          | Technologie                                           |
|--------------------|-------------------------------------------------------|
| Backend            | Flask (Python)                                        |
| Base de données    | SQLite (avec hachage des mots de passe)               |
| Analyse NLP        | NLPCloud API (français) + moteur règle-based maison   |
| Traitement données | Pandas, openpyxl                                      |
| Frontend           | HTML / CSS (effet glassmorphism) / JavaScript (Fetch) |
| Conteneurisation   | Docker, Docker Compose                                |
| Déploiement cloud  | Vercel (configuration fournie)                        |

---

## 🚀 Installation et exécution

### Prérequis
- Python 3.11+ (pour exécution locale)
- Docker & Docker Compose (optionnel mais recommandé)
- Une clé API [NLPCloud](https://nlpcloud.com/) (optionnelle, sinon le moteur règle-based est utilisé par défaut)

### 1. Exécution locale classique

```bash
git clone https://github.com/votre-utilisateur/sentix.git
cd sentix
pip install -r requirements.txt
export NLPCLOUD_API_KEY="votre_cle"   # facultatif
export SECRET_KEY="une_cle_secrete"
python app.py
## 2. Exécution avec Docker (recommandée pour production légère)

```bash
docker-compose up -d
```

L’application tourne sur `http://localhost:5000` avec :

- Un seul worker Gunicorn (faible consommation mémoire ~150 Mo).
- Un volume persistant `sentix_data` pour la base SQLite, les uploads et les rapports.
- Limites CPU/mémoire (`0.5 CPU / 512 Mo RAM`).

---

## 3. Déploiement sur Vercel

Le projet est livré avec un `vercel.json`.

Définissez les variables d’environnement dans le panneau Vercel :

- `SECRET_KEY`
- `NLPCLOUD_API_KEY`

Les fichiers sont stockés temporairement (`/tmp`) – attention : les données ne persistent pas entre les redéploiements.

---

# 📖 Utilisation

## En tant qu’utilisateur non connecté

1. Rendez-vous sur la page d’accueil → cliquez sur **Analyseur**.
2. Glissez-déposez un fichier Excel/CSV.
3. Les résultats s’affichent (statistiques, aperçu, rapport HTML téléchargeable).

---

## En tant qu’utilisateur enregistré

1. Créez un compte via `/register`.
2. Connectez-vous sur `/user_login`.
3. Après chaque analyse, celle-ci est automatiquement sauvegardée dans votre historique.
4. Retrouvez toutes vos analyses sur votre tableau de bord personnel (`/user_dashboard`).

---

## En tant qu’administrateur

Connectez-vous sur `/login` avec les identifiants par défaut :

```text
admin / chems123
```

> ⚠️ À changer impérativement en production.

Accédez à la supervision de toutes les analyses effectuées sur la plateforme.

---

# 🗂️ Structure du projet

```text
sentix/
├── app.py                  # Application Flask (routes, analyse, DB)
├── requirements.txt        # Dépendances Python
├── Dockerfile              # Construction image légère
├── docker-compose.yml      # Orchestration avec volume et limites
├── vercel.json             # Déploiement Vercel
├── templates/              # Fichiers HTML (lus par app.py)
│   ├── landing.html
│   ├── index.html
│   ├── register.html
│   ├── user_login.html
│   ├── user_dashboard.html
│   ├── login.html
│   └── admin.html
├── uploads/                # Dossier temporaire (local) ou volume /data
└── resultats_analyse/      # Dossier temporaire (local) ou volume /data
```

---

# ⚙️ Variables d’environnement

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé pour les sessions Flask | `sentix_secret_key_...` |
| `NLPCLOUD_API_KEY` | Clé API NLPCloud (français) | `""` (moteur règle-based) |
| `VERCEL` | Mode serverless (stockage dans `/tmp`) | `false` |
| `DATABASE_PATH` | Chemin vers la base SQLite (surcharge) | automatique |
| `UPLOAD_FOLDER` | Dossier d’upload | `/data/uploads` (Docker) |
| `RESULT_FOLDER` | Dossier des résultats | `/data/results` (Docker) |

---

# 🧪 Exemples de fichiers d’entrée

## CSV

(Séparateur virgule ou point-virgule – détection automatique)

```csv
avis,note
Ce produit est excellent, je recommande !,5
مزيان بزاف، شكرا,4
```

---

## Excel (`.xlsx / .xls`)

La colonne contenant les avis est automatiquement détectée  
(mots-clés : `"avis"`, `"comment"`, `"text"`, `"review"` ou première colonne texte).

---

# 📊 Résultats générés

- **Fichier Excel** : colonnes `avis`, `langue`, `sentiment_final`, `ligne_excel`.
- **Rapport HTML** : statistiques globales, répartition par sentiment, détails des langues détectées.

---

# 🔒 Sécurité

- Mots de passe hachés avec `werkzeug.security`.
- Noms de fichiers randomisés (`UUID`) pour éviter les collisions.
- Authentification obligatoire pour les tableaux de bord utilisateur et admin.
- En production, changez impérativement le mot de passe admin  
  (modifiez la condition dans `app.py` ou utilisez une variable d’environnement).

---

# 📈 Performances et limitations

- Taille maximale d’un fichier : **16 Mo**.
- Nombre d’avis traitables : dépend de la mémoire disponible  
  (testé avec succès jusqu’à **10 000 lignes**).
- Mémoire conteneur Docker : configurée à **512 Mo** (ajustable).
- Temps de réponse :
  - **1 000 avis** ≈ **30 secondes**
  - Pour des volumes plus importants, envisagez un mode asynchrone (`Celery`).

---

# 🛠️ Maintenance et évolutions possibles

- Remplacer SQLite par PostgreSQL pour une meilleure concurrence.
- Ajouter un système de suppression automatique des vieux rapports.
- Fine-tuner un modèle transformer (AraBERT) pour le darija.
- Exposer une API REST complète pour intégration tierce.
- Ajouter des graphiques (camembert, histogrammes) dans le rapport HTML.

---

# 📄 Licence

MIT – libre d’utilisation et de modification.

---

# ✍️ Auteurs

Développé par **CHEMS EDDOHA EL OTMANI** dans le cadre d’un Projet de Fin d’Études.  
Encadré par **MOHAMED HOUSNI**.

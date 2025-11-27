## 1. Présentation
**Ce projet met en place un système d’entretien d’embauche simulé, capable de :**
Lire un CV PDF
Récupérer une offre d’emploi (HasData / Indeed)
Générer un profil structuré
Produire des questions personnalisées
Mener un entretien vocal en temps réel via LiveKit
Utiliser un avatar Hedra pour la voix + lipsync

## 2. Architecture
CV (PDF) ─► cv_parser.py ─► last_cv.json
Job URL  ─► job_scraper.py ─► last_job.json

CV + Job ─► ManagerAgent ─► Question Agent ─► Live

LiveKit Realtime ─► Voix + Transcription  
Hedra Avatar ─► Animation + Lipsync

## 4. Configuration
OPENAI_API_KEY=...
HASDATA_API_KEY=...
HEDRA_API_KEY=...
HEDRA_AVATAR_ID=...

# Clonez le dépôt
git clone https://github.com/.../interview_prep_ai_agent.git
cd interview_prep_ai_agent

# Créez un environnement Python
python3 -m venv .venv
source .venv/bin/activate

# Installez les dépendances
pip install -r requirements.txt


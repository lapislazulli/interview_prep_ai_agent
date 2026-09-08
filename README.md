# Interview Prep AI Agent

Système multi-agents de simulation d'entretien d'embauche basé sur un CV PDF et une offre d'emploi réelle.

---

## 1. Présentation

Le projet génère automatiquement des questions d'entretien personnalisées en croisant le profil du candidat avec les exigences du poste, puis mène une simulation vocale complète avec retour coach.

**Fonctionnalités :**
- Lecture et structuration d'un CV PDF (OCR + LLM)
- Récupération d'une offre d'emploi via HasData / Indeed
- Génération de questions ciblées par `QuestionAgent`
- Simulation d'entretien vocale (TTS + STT Whisper) via `InterviewSimulator`
- Agent vocal en temps réel avec LiveKit + avatar animé Hedra
- Résumé coach post-entretien (points forts, axes d'amélioration, conseils)
- Export Notion ou Markdown local

---

## 2. Architecture

```
CV (PDF) ──► cv_parser.py ──► CVData
Job URL  ──► job_scraper.py ──► JobData
                │
                ▼
        QuestionAgent          ← génère les questions initiales
                │
                ▼
        ManagerAgent           ← orchestre l'entretien, gère la mémoire
                │
        ┌───────┴────────┐
        ▼                ▼
InterviewSimulator   LiveKit Agent
(Streamlit + STT/TTS) (voix temps réel + Hedra avatar)
        │
        ▼
   SummaryAgent              ← résumé coach post-entretien
        │
        ▼
  Notion / Markdown
```

---

## 3. Structure du projet

```
src/
├── agents/
│   ├── manager_agent.py      # Orchestrateur principal
│   ├── question_agent.py     # Génération des questions
│   └── summary_agent.py      # Résumé coach post-entretien
├── core/
│   └── interview_simulator.py # Boucle TTS/STT locale
├── models/
│   ├── data_models.py        # CVData, JobData, QAExchange
│   └── memory.py             # ConversationMemory
├── services/
│   ├── cv_parser.py          # OCR + structuration LLM du CV
│   ├── job_scraper.py        # Scraping offre via HasData
│   ├── stt_service.py        # Whisper STT
│   ├── tts_service.py        # OpenAI TTS
│   └── notion_export.py      # Export vers Notion
├── utils/
│   └── profile_export.py     # export_cv / export_job / load_cv / load_job
├── ui/
│   └── app.py                # Interface Streamlit alternative
├── livekit_interviewer_agent.py  # Agent vocal LiveKit + Hedra
├── main.py                   # Point d'entrée Streamlit principal
├── llm_client.py             # Wrapper OpenAI avec retry JSON
└── config.py                 # Variables d'environnement
```

---

## 4. Installation

```bash
# Cloner le dépôt
git clone https://github.com/lapislazulli/interview_prep_ai_agent.git
cd interview_prep_ai_agent

# Créer un environnement virtuel
python3 -m venv .venv
source .venv/bin/activate

# Installer les dépendances
pip install -r requirements.txt

# Installer Tesseract (OCR)
# macOS :
brew install tesseract
# Linux :
sudo apt install tesseract-ocr
```

---

## 5. Configuration

Créez un fichier `.env` à la racine du projet :

```env
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4o-mini        # optionnel, défaut : gpt-4o-mini

HASDATA_API_KEY=...              # pour le scraping Indeed

NOTION_API_KEY=...               # optionnel
NOTION_DATABASE_ID=...           # optionnel

LIVEKIT_API_KEY=...              # pour le mode vocal LiveKit
LIVEKIT_API_SECRET=...
LIVEKIT_URL=...

HEDRA_API_KEY=...                # pour l'avatar animé
HEDRA_AVATAR_ID=...

LIVEKIT_QUESTION_COUNT=3         # nombre de questions ManagerAgent (défaut : 3)
```

---

## 6. Lancement

### Interface Streamlit (recommandé)

```bash
streamlit run src/main.py
```

1. Uploadez votre CV (PDF)
2. Collez le lien d'une offre Indeed / LinkedIn
3. Choisissez le nombre de questions
4. Lancez la simulation vocale
5. Générez le résumé coach

### Agent vocal LiveKit

```bash
python src/livekit_interviewer_agent.py dev
```

Si `exports/last_cv.json` et `exports/last_job.json` n'existent pas encore, le script vous demandera le chemin du CV et l'URL de l'offre. Sinon, il utilise directement les fichiers générés par Streamlit.

---

## 7. Flux de données

1. `cv_parser.py` extrait le texte du PDF (OCR Tesseract + fallback pypdf) et le structure en JSON via le LLM.
2. `job_scraper.py` récupère le titre, l'entreprise, la localisation et la description du poste.
3. `QuestionAgent` croise CV + offre pour générer 5 à 8 questions ciblées.
4. `ManagerAgent` sert ces questions une par une, consulte le LLM pour d'éventuelles questions de suivi, et maintient l'historique via `ConversationMemory`.
5. `InterviewSimulator` lit les questions à voix haute (TTS) et enregistre les réponses (STT Whisper).
6. `SummaryAgent` analyse l'historique complet et produit un retour structuré en Markdown.

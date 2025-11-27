# src/ui/app.py

import os
import sys
import tempfile

import streamlit as st

# ---------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# ---------------------------------------------------------
# IMPORTS
# ---------------------------------------------------------
from llm_client import LLMClient
from agents.manager_agent import ManagerAgent
from agents.summary_agent import SummaryAgent
from models.data_models import CVData, JobData
from services.cv_parser import parse_cv
from services.job_scraper import scrape_job_url
from core.interview_simulator import InterviewSimulator

# ---------------------------------------------------------
# STREAMLIT CONFIG + CSS
# ---------------------------------------------------------
st.set_page_config(page_title="Interview Prep Studio", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f5f7;
        color: #111827;
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif;
    }
    .block-container {
        max-width: 1150px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .card {
        background: #ffffff;
        border-radius: 18px;
        padding: 1.2rem 1.5rem;
        border: 1px solid #e5e7eb;
        box-shadow: 0 10px 30px rgba(15,23,42,0.03);
        margin-bottom: 1rem;
    }
    .section-title {
        font-size: 0.9rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #6b7280;
        margin-top: 0.8rem;
        margin-bottom: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------
st.markdown("## Interview Prep Studio")
st.caption("Simulation d'entretien vocale basée sur un système multi-agents (CV + offre + mémoire).")
st.markdown("---")

# ---------------------------------------------------------
# STEP 1 · SETUP
# ---------------------------------------------------------
st.markdown('<div class="section-title">Étape 1 · Configuration</div>', unsafe_allow_html=True)
with st.form("setup_form"):
    c1, c2 = st.columns([0.5, 0.5])

    with c1:
        cv_file = st.file_uploader("CV (PDF)", type=["pdf"])

    with c2:
        job_url = st.text_input("Lien de l'offre (Indeed / LinkedIn)", placeholder="https://fr.indeed.com/...")

    num_questions = st.slider("Nombre de questions dans la simulation", 3, 10, 5)

    submit = st.form_submit_button("Analyser le CV et l'offre")

# ---------------------------------------------------------
# ANALYSE
# ---------------------------------------------------------
if submit:
    if not cv_file or not job_url:
        st.error("Merci d'uploader un CV et de coller un lien d'offre.")
    else:
        with st.spinner("Analyse du CV et de l'offre en cours…"):
            # Sauvegarde locale du PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(cv_file.getvalue())
                pdf_path = tmp.name

            llm = LLMClient()
            cv_data = parse_cv(pdf_path, llm)
            job_data = scrape_job_url(job_url)

            st.session_state["cv_data"] = cv_data
            st.session_state["job_data"] = job_data
            st.session_state["num_q"] = num_questions

        st.success("Analyse terminée. Faites défiler pour lancer la simulation.")

# ---------------------------------------------------------
# SI ANALYSE OK → AFFICHAGE + SIMULATION
# ---------------------------------------------------------
if "cv_data" in st.session_state and "job_data" in st.session_state:
    cv: CVData = st.session_state["cv_data"]
    job: JobData = st.session_state["job_data"]
    num_q: int = st.session_state["num_q"]

    # --- Étape 2 : Vue d'ensemble ---
    st.markdown('<div class="section-title">Étape 2 · Vue d’ensemble</div>', unsafe_allow_html=True)
    colA, colB = st.columns(2)

    with colA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("CV")
        st.write(cv.structured.get("name", "—"))
        contact = cv.structured.get("contact", "")
        if contact:
            st.caption(contact)

        skills = cv.structured.get("skills", []) or []
        if skills:
            st.write("**Compétences clés**")
            st.write(", ".join(skills[:12]))
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Offre d'emploi")
        st.write(job.structured.get("title", "—"))
        company = job.structured.get("company", "")
        location = job.structured.get("location", "")
        if company:
            st.caption(company)
        if location:
            st.caption(location)
        st.markdown("</div>", unsafe_allow_html=True)

    # --- Étape 3 : Simulation vocale ---
    st.markdown('<div class="section-title">Étape 3 · Simulation vocale</div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    st.write(
        "Cliquez sur **Lancer la simulation**. "
        "L'interviewer posera les questions à voix haute, vous répondez à l'oral, et le système enregistre l'historique."
    )

    if st.button("Lancer la simulation d'entretien"):
        llm = LLMClient()
        manager = ManagerAgent(llm=llm, cv=cv, job=job, base_questions=[])

        simulator = InterviewSimulator(
            manager=manager,
            max_questions=num_q,
            stt_duration=4,
            streamlit=st,
        )

        with st.spinner("Simulation en cours…"):
            history = simulator.run()

        st.session_state["history"] = history

    st.markdown("</div>", unsafe_allow_html=True)

    # --- Étape 4 : Feedback ---
    if "history" in st.session_state:
        st.markdown('<div class="section-title">Étape 4 · Feedback</div>', unsafe_allow_html=True)
        if st.button("Générer le résumé et les conseils"):
            history = st.session_state["history"]
            llm = LLMClient()
            summary_agent = SummaryAgent(llm, cv, job, history)
            summary_md = summary_agent.generate_notion_markdown()

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(summary_md)
            st.markdown("</div>", unsafe_allow_html=True)
else:
    st.info("Commence par uploader un CV et une offre, puis clique sur **Analyser le CV et l'offre**.")

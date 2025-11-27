# src/ui/app.py — Minimal Clean Interface (Option A)

import os
import sys
import tempfile

import streamlit as st

# Make src/ imports work
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.append(ROOT)

# ---------------------------------------------------------
# Project imports
# ---------------------------------------------------------
from llm_client import LLMClient
from models.data_models import CVData, JobData
from agents.manager_agent import ManagerAgent
from agents.summary_agent import SummaryAgent
from services.cv_parser import parse_cv
from services.job_scraper import scrape_job_url
from core.interview_simulator import InterviewSimulator, AVATAR_IDLE_HTML
from utils.profile_export import export_cv, export_job

# ---------------------------------------------------------
# Page config & styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Interview Prep Studio",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background: #f5f5f7;
        color: #111827;
        font-family: system-ui, -apple-system, BlinkMacSystemFont,
                     "SF Pro Text", sans-serif;
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1100px;
    }
    h1 {
        font-weight: 700;
        letter-spacing: -0.03em;
        margin-bottom: -0.2rem;
    }
    .header-sub {
        font-size: 0.95rem;
        color: #6b7280;
        margin-bottom: 1.5rem;
    }
    .card {
        background: #ffffff;
        border-radius: 18px;
        border: 1px solid #e5e7eb;
        padding: 1.3rem 1.6rem;
        box-shadow: 0 8px 26px rgba(0,0,0,0.04);
        margin-bottom: 1.5rem;
    }
    .section-title {
        margin-top: 0.5rem;
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #6b7280;
        font-weight: 600;
        letter-spacing: 0.07em;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ---------------------------------------------------------
# Header
# ---------------------------------------------------------
st.markdown("<h1>Interview Prep Studio</h1>", unsafe_allow_html=True)
st.markdown(
    '<div class="header-sub">Upload your CV + job offer link, then simulate a real interview with voice.</div>',
    unsafe_allow_html=True
)

st.markdown("<hr>", unsafe_allow_html=True)

# ---------------------------------------------------------
# Step 1 — Inputs
# ---------------------------------------------------------
st.markdown('<div class="section-title">Étape 1 · Charger vos documents</div>', unsafe_allow_html=True)
with st.form("setup"):
    c1, c2 = st.columns([0.5, 0.5])

    with c1:
        st.markdown("**CV (PDF)**")
        cv_file = st.file_uploader("Upload CV", type=["pdf"], label_visibility="collapsed")

    with c2:
        st.markdown("**Job offer link**")
        job_url = st.text_input(
            "Paste job offer URL",
            placeholder="https://fr.indeed.com/...",
            label_visibility="collapsed"
        )

    num_q = st.slider("Number of questions in simulation", 3, 10, 5)

    submitted = st.form_submit_button("Analyse")

# ---------------------------------------------------------
# Step 2 — Analysis
# ---------------------------------------------------------
if submitted:
    if not cv_file or not job_url:
        st.error("Please upload a CV and paste a job link.")
    else:
        with st.spinner("Analysing CV + job…"):
            # save temp PDF
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(cv_file.getvalue())
                pdf_path = tmp.name

            llm = LLMClient()
            cv_data = parse_cv(pdf_path, llm)
            job_data = scrape_job_url(job_url)

            # Save for LiveKit/Hedra worker
            export_cv(cv_data)
            export_job(job_data)

            # Save session
            st.session_state["cv"] = cv_data
            st.session_state["job"] = job_data
            st.session_state["num_q"] = num_q

        st.success("Documents analyzed successfully.")

# ---------------------------------------------------------
# If data exists → show preview
# ---------------------------------------------------------
if "cv" in st.session_state and "job" in st.session_state:
    cv: CVData = st.session_state["cv"]
    job: JobData = st.session_state["job"]
    num_q: int = st.session_state["num_q"]

    # ---------------- Preview ----------------
    st.markdown('<div class="section-title">Étape 2 · Aperçu des données</div>', unsafe_allow_html=True)

    cA, cB = st.columns(2)

    # CV card
    with cA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Résumé du CV")
        st.write(cv.structured.get("name", "—"))
        contact = cv.structured.get("contact", "")
        if contact:
            st.caption(contact)

        skills = cv.structured.get("skills", [])
        if skills:
            st.markdown("**Compétences clés**")
            st.write(", ".join(skills[:12]))

        st.markdown("</div>", unsafe_allow_html=True)

    # Job card
    with cB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Aperçu de l'offre")
        st.write(job.structured.get("title", "—"))
        company = job.structured.get("company", "")
        location = job.structured.get("location", "")
        if company:
            st.caption(company)
        if location:
            st.caption(location)

        desc = job.structured.get("clean_description", "")
        if desc:
            st.markdown("**Description (extrait)**")
            st.write(desc[:350] + ("…" if len(desc) > 350 else ""))
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # Step 3 — Voice Simulation
    # ---------------------------------------------------------
    st.markdown('<div class="section-title">Étape 3 · Simulation vocale</div>', unsafe_allow_html=True)

    colL, colR = st.columns([0.25, 0.75])

    with colL:
        avatar_ph = st.empty()
        avatar_ph.markdown(AVATAR_IDLE_HTML, unsafe_allow_html=True)

    with colR:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        log_ph = st.container()
        st.write(
            "Click below to start a **local voice-based interview simulation** "
            "(Whisper STT + TTS)."
        )

        if st.button("🎬 Start voice simulation"):
            llm_client = LLMClient()
            manager = ManagerAgent(
                llm=llm_client,
                cv=cv,
                job=job,
                base_questions=[],
            )
            sim = InterviewSimulator(
                manager=manager,
                max_questions=num_q,
                stt_duration=4,
                streamlit=st,
                avatar_placeholder=avatar_ph,
                log_placeholder=log_ph,
            )

            with st.spinner("Interview in progress…"):
                history = sim.run()

            st.session_state["history"] = history

        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<hr>", unsafe_allow_html=True)

    # ---------------------------------------------------------
    # Step 4 — Feedback summary
    # ---------------------------------------------------------
    if "history" in st.session_state:
        st.markdown('<div class="section-title">Étape 4 · Résumé</div>', unsafe_allow_html=True)

        if st.button("Generate summary of your interview"):
            llm = LLMClient()
            history = st.session_state["history"]
            summary_agent = SummaryAgent(llm, cv, job, history)
            summary_md = summary_agent.generate_notion_markdown()

            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(summary_md)
            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("Upload your CV & paste job offer link, then click Analyse.")

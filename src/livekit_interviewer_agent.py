# src/livekit_interviewer_agent.py
#
# LiveKit + OpenAI Realtime + Hedra
#
# Usage:
#   1. Run the Streamlit app first to generate exports/last_cv.json
#      and exports/last_job.json.
#   2. Then run:  python src/livekit_interviewer_agent.py dev
#
# Alternatively, call prepare_profile_via_cli() for a standalone CLI flow.

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv

from livekit.agents import (
    JobContext,
    AgentSession,
    Agent,
    RoomInputOptions,
    RoomOutputOptions,
    WorkerOptions,
)
from livekit.agents import cli
from livekit.plugins import openai as lk_openai
from livekit.plugins import hedra as lk_hedra

from llm_client import LLMClient
from agents.manager_agent import ManagerAgent
from models.data_models import CVData, JobData
from services.cv_parser import parse_cv
from services.job_scraper import scrape_job_url
from utils.profile_export import (
    export_cv,
    export_job,
    load_cv,
    load_job,
    CV_JSON_PATH,
    JOB_JSON_PATH,
)

load_dotenv()

logger = logging.getLogger(__name__)

HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
HEDRA_AVATAR_ID = os.getenv("HEDRA_AVATAR_ID")

# Number of ManagerAgent questions on top of the fixed intro question
MANAGER_QUESTION_COUNT = int(os.getenv("LIVEKIT_QUESTION_COUNT", "3"))
MAX_QUESTIONS = 1 + MANAGER_QUESTION_COUNT  # intro + N from ManagerAgent


# ---------------------------------------------------------
# Step 0 – CLI profile preparation (optional standalone flow)
# ---------------------------------------------------------
def prepare_profile_via_cli() -> None:
    """
    Asks the user for CV path + job URL, parses both, and writes
    exports/last_cv.json + exports/last_job.json so the LiveKit
    worker can load them without re-parsing.
    """
    print("\n[Setup] Prepare your interview profile")

    cv_path = input("Path to your CV PDF: ").strip()
    job_url = input("Job / Indeed URL: ").strip()

    print("[Setup] Initializing LLMClient for CV parsing…")
    llm = LLMClient()

    print(f"[Setup] Parsing CV from: {cv_path}")
    cv_obj = parse_cv(cv_path, llm)

    print(f"[Setup] Scraping job posting from: {job_url}")
    job_obj = scrape_job_url(job_url)

    export_cv(cv_obj)
    export_job(job_obj)

    print("\n[Setup] Export complete! Starting LiveKit…\n")


# ---------------------------------------------------------
# Worker entrypoint
# ---------------------------------------------------------
async def entrypoint(ctx: JobContext):
    logger.info("[LiveKit] Worker starting interview agent.")
    await ctx.connect()

    # Realtime voice model
    rt_model = lk_openai.realtime.RealtimeModel(voice="alloy")

    # Load structured profile from disk (written by Streamlit or CLI)
    llm = LLMClient()
    cv_data = load_cv()
    job_data = load_job()
    logger.info("[LiveKit] Profile loaded. CV name: %s", cv_data.structured.get("name", "—"))

    manager = ManagerAgent(
        llm=llm,
        cv=cv_data,
        job=job_data,
        base_questions=[],
        max_questions=MANAGER_QUESTION_COUNT,
    )

    session = AgentSession(llm=rt_model)

    # Hedra avatar (optional)
    if HEDRA_API_KEY and HEDRA_AVATAR_ID:
        try:
            avatar = lk_hedra.AvatarSession(avatar_id=HEDRA_AVATAR_ID)
            await avatar.start(session, room=ctx.room)
            logger.info("[Hedra] Avatar online.")
        except Exception as e:
            logger.warning("[Hedra] Failed to start avatar: %s", e)
    else:
        logger.warning("[Hedra] Avatar disabled (HEDRA_API_KEY / HEDRA_AVATAR_ID missing).")

    total_questions = 0

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------
    async def end_interview(message: str | None = None) -> None:
        farewell = message or (
            "Merci beaucoup pour cet entretien. "
            "Nous reviendrons vers vous prochainement. Bonne continuation !"
        )
        await session.generate_reply(
            instructions=(
                "Tu es Clara, recruteuse. "
                "Lis EXACTEMENT cette phrase, sans rien ajouter : "
                f'"{farewell}"'
            )
        )
        await asyncio.sleep(1)
        await session.close()

    async def ask_manager_question() -> None:
        nonlocal total_questions

        if total_questions >= MAX_QUESTIONS:
            await end_interview()
            return

        decision = manager.next_step()
        logger.info("[ManagerAgent] Decision: %s", decision)

        if decision.get("end"):
            await end_interview()
            return

        question = (decision.get("next_question") or "").strip()
        if not question:
            await end_interview()
            return

        logger.info("[Interviewer] Q%d: %s", total_questions + 1, question)
        await session.generate_reply(
            instructions=(
                "Tu joues STRICTEMENT le rôle de recruteuse en entretien. "
                "Ne donne jamais de conseils, ne fais pas de coaching, "
                "ne réponds jamais à la place du candidat. "
                "Lis EXACTEMENT la question suivante, mot pour mot, "
                "sans rien ajouter avant, après ou entre parenthèses : "
                f'"{question}"'
            )
        )
        total_questions += 1

    # ----------------------------------------------------------------
    # Handle candidate answers
    # ----------------------------------------------------------------
    async def handle_transcription(event) -> None:
        text = getattr(event, "text", "")
        logger.info("[Candidate] %s", text)

        if total_questions >= MAX_QUESTIONS:
            await end_interview()
            return

        manager.record_answer("", text)
        await ask_manager_question()

    @session.on("user_input_transcribed")
    def on_transcription(event):
        asyncio.create_task(handle_transcription(event))

    # ----------------------------------------------------------------
    # Start with a fixed intro question (counts as question #1)
    # ----------------------------------------------------------------
    async def start_interview() -> None:
        nonlocal total_questions

        intro = (
            "Bonjour, merci d'être présent(e) pour cet entretien. "
            "Pour commencer, pouvez-vous vous présenter brièvement "
            "et m'expliquer ce qui vous motive pour ce poste ?"
        )

        logger.info("[Interviewer] Intro question")
        await session.generate_reply(
            instructions=(
                "Tu es Clara, recruteuse IA francophone. "
                "Tu mènes un entretien d'embauche simulé. "
                "Ne donne aucun conseil, ne proposes pas de sujets de discussion. "
                "Lis EXACTEMENT la phrase suivante, mot pour mot, "
                "sans rien ajouter avant, après ou entre parenthèses : "
                f'"{intro}"'
            )
        )
        total_questions += 1

    # ----------------------------------------------------------------
    # Start LiveKit session
    # ----------------------------------------------------------------
    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions=(
                "Tu es Clara, une recruteuse IA francophone spécialisée en data et IA. "
                "Tu mènes un entretien d'embauche simulé. "
                "Tu ne dois JAMAIS dire des phrases de chatbot généraliste comme "
                '"De quoi avez-vous envie de discuter ?" ou "Comment puis-je vous aider ?". '
                "Tu ne donnes jamais de conseils, tu ne fais pas de coaching, "
                "tu ne réponds pas à la place du candidat. "
                "Tu parles uniquement pour poser les questions d'entretien "
                "ou pour clôturer l'entretien."
            )
        ),
        room_input_options=RoomInputOptions(
            audio_enabled=True,
            video_enabled=False,
            text_enabled=False,
        ),
        room_output_options=RoomOutputOptions(
            audio_enabled=True,
            transcription_enabled=True,
        ),
    )

    await start_interview()


# ---------------------------------------------------------
# Script entry point
# ---------------------------------------------------------
if __name__ == "__main__":
    # If exports don't exist yet, run the CLI setup flow
    if not CV_JSON_PATH.exists() or not JOB_JSON_PATH.exists():
        prepare_profile_via_cli()

    if len(sys.argv) == 1:
        sys.argv.append("dev")

    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))

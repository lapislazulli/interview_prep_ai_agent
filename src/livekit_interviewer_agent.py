# src/livekit_interviewer_agent.py
#
# LiveKit + OpenAI Realtime + Hedra
# Interview simulation:
# - Asks for CV PDF + job URL (CLI)
# - Parses & exports last_cv.json + last_job.json
# - Asks EXACTLY 4 questions in total (1 intro + 3 ManagerAgent)
# - Then ends the interview politely

import os
import sys
import json
import asyncio
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


# ---------------------------------------------------------
# Environment
# ---------------------------------------------------------
load_dotenv()

HEDRA_API_KEY = os.getenv("HEDRA_API_KEY")
HEDRA_AVATAR_ID = os.getenv("HEDRA_AVATAR_ID")

EXPORT_DIR = Path("exports")
CV_JSON_PATH = EXPORT_DIR / "last_cv.json"
JOB_JSON_PATH = EXPORT_DIR / "last_job.json"


# ---------------------------------------------------------
# Step 0 – Ask user for CV + job link
# ---------------------------------------------------------
def prepare_profile_via_cli() -> None:
    print("\n[Setup] Prepare your interview profile")

    cv_path = input("Path to your CV PDF: ").strip()
    job_url = input("Job / Indeed URL: ").strip()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    print("[Setup] Initializing LLMClient for CV parsing...")
    llm = LLMClient()

    print(f"[Setup] Parsing CV from: {cv_path}")
    cv_obj = parse_cv(cv_path, llm)

    print(f"[Setup] Scraping job posting from: {job_url}")
    job_obj = scrape_job_url(job_url)

    cv_struct = getattr(cv_obj, "structured", cv_obj)
    job_struct = getattr(job_obj, "structured", job_obj)

    print(f"[Setup] Writing {CV_JSON_PATH}")
    with CV_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(cv_struct, f, ensure_ascii=False, indent=2)

    print(f"[Setup] Writing {JOB_JSON_PATH}")
    with JOB_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(job_struct, f, ensure_ascii=False, indent=2)

    print("\n[Setup] Export complete! Starting LiveKit...\n")


# ---------------------------------------------------------
# Worker entrypoint
# ---------------------------------------------------------
async def entrypoint(ctx: JobContext):
    print("[LiveKit] Worker starting interview agent.")

    await ctx.connect()

    # Realtime model (we control behavior via instructions in Agent + generate_reply)
    rt_model = lk_openai.realtime.RealtimeModel(
        voice="alloy",
    )

    llm = LLMClient()

    print(f"[System] Loading CV from {CV_JSON_PATH}")
    with CV_JSON_PATH.open("r", encoding="utf-8") as f:
        cv_struct = json.load(f)

    print(f"[System] Loading Job from {JOB_JSON_PATH}")
    with JOB_JSON_PATH.open("r", encoding="utf-8") as f:
        job_struct = json.load(f)

    cv_data = CVData(raw_text="", structured=cv_struct)
    job_data = JobData(raw_text="", structured=job_struct)

    manager = ManagerAgent(
        llm=llm,
        cv=cv_data,
        job=job_data,
        base_questions=[],
    )

    session = AgentSession(llm=rt_model)

    # Hedra avatar
    if HEDRA_API_KEY and HEDRA_AVATAR_ID:
        try:
            avatar = lk_hedra.AvatarSession(avatar_id=HEDRA_AVATAR_ID)
            await avatar.start(session, room=ctx.room)
            print("[Hedra] Avatar online.")
        except Exception as e:
            print("[Hedra] Failed to start avatar:", e)
    else:
        print("[Hedra] ⚠ Avatar disabled (missing env vars).")

    # -----------------------------------------------------
    # EXACTLY 4 questions total (intro + 3 ManagerAgent)
    # -----------------------------------------------------
    total_questions = 0
    MAX_QUESTIONS = 4

    async def end_interview(final_message: str = None):
        """
        Ends the interview politely and closes the session.
        """
        message = final_message or (
            "Merci, l'entretien est terminé. Nous avons couvert les points essentiels."
        )
        await session.generate_reply(
            instructions=(
                "Tu es Clara, recruteuse. "
                "Lis EXACTEMENT cette phrase, sans rien ajouter : "
                f"\"{message}\""
            )
        )
        await asyncio.sleep(1)
        await session.close()

    # -----------------------------------------------------
    # Manager step: ask next question or end
    # -----------------------------------------------------
    async def run_manager_step():
        nonlocal total_questions

        # If we already reached the max, just end
        if total_questions >= MAX_QUESTIONS:
            await end_interview()
            return

        decision = manager.next_step()
        print("[ManagerAgent decision]", decision)

        # If ManagerAgent says "end", respect it, but still within our 4-question max
        if decision.get("end"):
            await end_interview("Merci, l'entretien est terminé.")
            return

        question = (decision.get("next_question") or "").strip()

        if not question:
            await end_interview("Nous arrivons au terme de cette démonstration.")
            return

        print("[Interviewer] ❓", question)

        # If asking this would exceed the limit, end instead
        if total_questions >= MAX_QUESTIONS:
            await end_interview()
            return

        await session.generate_reply(
            instructions=(
                "Tu joues STRICTEMENT le rôle de recruteuse en entretien. "
                "Ne donne jamais de conseils, ne fais pas de coaching, "
                "ne réponds jamais à la place du candidat. "
                "Lis EXACTEMENT la question suivante, mot pour mot, "
                "sans rien ajouter avant, après ou entre parenthèses : "
                f"\"{question}\""
            )
        )

        total_questions += 1


    # -----------------------------------------------------
    # Handle user transcription (answers)
    # -----------------------------------------------------
    async def handle_transcription(event):
        text = event.text
        print(f"[User] {text}")

        # If already at 4, ignore extra answers and end gracefully
        if total_questions >= MAX_QUESTIONS:
            await end_interview()
            return

        manager.record_answer("", text)
        await run_manager_step()

    @session.on("user_input_transcribed")
    def on_transcription(event):
        asyncio.create_task(handle_transcription(event))

    # -----------------------------------------------------
    # Intro: counts as Question #1
    # -----------------------------------------------------
    async def start_interview():
        nonlocal total_questions

        intro_question = (
            "Bonjour, merci d'être présente pour cet entretien. "
            "Pour commencer, pouvez-vous vous présenter brièvement "
            "et m'expliquer ce qui vous motive pour ce poste ?"
        )

        print("[Interviewer] Intro question")
        await session.generate_reply(
            instructions=(
                "Tu es Clara, recruteuse IA. "
                "Tu es déjà en plein entretien, pas un chatbot généraliste. "
                "Ne donne aucun conseil, ne proposes pas de sujets de discussion. "
                "Lis EXACTEMENT la phrase suivante, mot pour mot, "
                "sans rien ajouter avant, après ou entre parenthèses : "
                f"\"{intro_question}\""
            )
        )

        # Intro counts as question #1
        total_questions += 1

    # -----------------------------------------------------
    # Start LiveKit session
    # -----------------------------------------------------
    await session.start(
        room=ctx.room,
        agent=Agent(
            instructions=(
                "Tu es Clara, une recruteuse IA francophone spécialisée en data et IA. "
                "Tu mènes un entretien d'embauche simulé. "
                "Tu ne dois JAMAIS dire des phrases de chatbot généraliste comme "
                "\"De quoi avez-vous envie de discuter aujourd'hui ?\" ou "
                "\"Comment puis-je vous aider ?\". "
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

if __name__ == "__main__":
    prepare_profile_via_cli()

    if len(sys.argv) == 1:
        sys.argv.append("dev")

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

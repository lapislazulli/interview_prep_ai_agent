# src/core/interview_simulator.py

import logging
import time
from typing import List, Optional

from agents.manager_agent import ManagerAgent
from services.stt_service import stt_record_and_transcribe
from services.tts_service import generate_tts_audio
from models.data_models import QAExchange

logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Simple CSS avatar placeholder for the Streamlit UI
# ---------------------------------------------------------
AVATAR_IDLE_HTML = """
<div style="
    width: 120px; height: 120px;
    border-radius: 50%;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 3rem; box-shadow: 0 8px 24px rgba(99,102,241,0.25);
">🧑‍💼</div>
"""

AVATAR_SPEAKING_HTML = """
<div style="
    width: 120px; height: 120px;
    border-radius: 50%;
    background: linear-gradient(135deg, #10b981 0%, #059669 100%);
    display: flex; align-items: center; justify-content: center;
    font-size: 3rem; box-shadow: 0 8px 24px rgba(16,185,129,0.35);
    animation: pulse 1s infinite;
">🎙️</div>
"""


class InterviewSimulator:
    """
    Autonomous interview loop:
      1. Ask ManagerAgent for the next question.
      2. Play it via TTS.
      3. Record the candidate's answer via STT.
      4. Persist the exchange in ManagerAgent memory.
      5. Repeat until max_questions or ManagerAgent signals end.
    """

    def __init__(
        self,
        manager: ManagerAgent,
        max_questions: int = 5,
        stt_duration: int = 4,
        streamlit=None,
        avatar_placeholder=None,
        log_placeholder=None,
    ):
        self.manager = manager
        self.max_questions = max_questions
        self.stt_duration = stt_duration
        self.st = streamlit
        self.avatar_ph = avatar_placeholder  # st.empty() for avatar animation
        self.log_ph = log_placeholder        # st.container() for Q&A log

    # ----------------------------------------------------------------
    # Internal helpers
    # ----------------------------------------------------------------
    def _write(self, *args, **kwargs):
        """Write to Streamlit if available, otherwise log."""
        if self.st:
            self.st.write(*args, **kwargs)
        else:
            logger.info(str(args))

    def _info(self, msg: str):
        if self.st:
            self.st.info(msg)
        else:
            logger.info(msg)

    def _success(self, msg: str):
        if self.st:
            self.st.success(msg)
        else:
            logger.info(msg)

    def _set_avatar(self, speaking: bool):
        if self.avatar_ph:
            html = AVATAR_SPEAKING_HTML if speaking else AVATAR_IDLE_HTML
            self.avatar_ph.markdown(html, unsafe_allow_html=True)

    def _play_audio(self, path: str):
        if not path or not self.st:
            return
        try:
            with open(path, "rb") as f:
                audio_bytes = f.read()
            self.st.audio(audio_bytes, format="audio/wav")
        except Exception as e:
            logger.error("[Simulator] Error playing audio: %s", e)

    # ----------------------------------------------------------------
    # Main loop
    # ----------------------------------------------------------------
    def run(self) -> List[QAExchange]:
        history: List[QAExchange] = []
        count = 0

        self._write("### 🎤 Interview simulation started")
        self._info("After each question, answer aloud near your microphone.")
        self._set_avatar(speaking=False)

        while count < self.max_questions:
            # 1) Get next step from ManagerAgent
            step = self.manager.next_step()
            question: str = step.get("next_question", "").strip()
            end_flag: bool = step.get("end", False)

            if end_flag or not question:
                self._success("✅ Interview completed.")
                self._set_avatar(speaking=False)
                break

            count += 1
            self._write(f"**Interviewer [{count}/{self.max_questions}]:** {question}")
            logger.info("[Simulator] Q%d: %s", count, question)

            # 2) TTS — play the question
            self._set_avatar(speaking=True)
            audio_path = generate_tts_audio(question)
            if audio_path:
                self._play_audio(audio_path)
            self._set_avatar(speaking=False)

            # 3) STT — record candidate's answer
            self._info("🎙️ Listening… answer now.")
            answer: Optional[str] = stt_record_and_transcribe(duration=self.stt_duration)
            if not answer:
                answer = "(no answer detected)"
                logger.warning("[Simulator] STT returned empty for Q%d.", count)

            self._write(f"**You:** {answer}")
            logger.info("[Simulator] A%d: %s", count, answer[:120])

            # 4) Persist exchange
            self.manager.record_answer(question, answer)
            history.append(QAExchange(question=question, answer=answer))

            time.sleep(0.8)

        if count >= self.max_questions:
            self._success("✅ Maximum number of questions reached. Interview completed.")

        return history

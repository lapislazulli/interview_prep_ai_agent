# src/core/interview_simulator.py

import time
from typing import List

from agents.manager_agent import ManagerAgent
from services.stt_service import stt_record_and_transcribe
from services.tts_service import generate_tts_audio
from models.data_models import QAExchange


class InterviewSimulator:
    """
    Boucle d'entretien autonome:
    - demande une question à ManagerAgent
    - TTS pour la poser à voix haute
    - STT pour écouter la réponse
    - stocke dans la mémoire
    - répète jusqu'à max_questions ou fin
    """

    def __init__(self, manager: ManagerAgent, max_questions: int = 5, stt_duration: int = 4, streamlit=None):
        self.manager = manager
        self.max_questions = max_questions
        self.stt_duration = stt_duration
        self.st = streamlit

    def play_audio(self, path: str):
        try:
            with open(path, "rb") as f:
                audio = f.read()
            self.st.audio(audio, format="audio/wav")
        except Exception as e:
            print("[Simulator] ❌ Error playing audio:", e)

    def run(self) -> List[QAExchange]:
        history: List[QAExchange] = []
        count = 0

        self.st.write("### 🎤 Interview simulation started")
        self.st.info("Après chaque question, répondez à voix haute près de votre micro.")

        while count < self.max_questions:
            step = self.manager.next_step()
            question = step.get("next_question", "")
            end_flag = step.get("end", False)

            if end_flag or not question.strip():
                self.st.success("Entretien terminé.")
                break

            count += 1
            self.st.write(f"**Interviewer:** {question}")

            # 1) TTS : poser la question à voix haute
            audio_path = generate_tts_audio(question)
            if audio_path:
                self.play_audio(audio_path)

            # 2) STT : écouter la réponse
            self.st.info("🎙️ Écoute en cours… répondez maintenant.")
            answer = stt_record_and_transcribe(duration=self.stt_duration)
            if not answer:
                answer = "(aucune réponse détectée)"

            self.st.write(f"**Vous:** {answer}")

            # 3) mémoire
            self.manager.record_answer(question, answer)
            history.append(QAExchange(question=question, answer=answer))

            time.sleep(1.0)

        return history

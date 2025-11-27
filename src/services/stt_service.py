# src/services/stt_service.py

import os
import tempfile
from typing import Optional

import sounddevice as sd
from scipy.io import wavfile
from openai import OpenAI

SAMPLE_RATE = 16_000
CHANNELS = 1

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def record_audio(duration: int = 4) -> str:
    """
    Enregistre l'audio depuis le micro pendant `duration` secondes
    et retourne le chemin vers un fichier WAV temporaire.
    """
    audio = sd.rec(
        int(duration * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
    )
    sd.wait()

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    wavfile.write(tmp.name, SAMPLE_RATE, audio)
    tmp.close()
    return tmp.name


def stt_record_and_transcribe(duration: int = 4) -> Optional[str]:
    """
    Enregistre la voix puis envoie le fichier à l'API Whisper pour transcription.
    Retourne le texte (ou None en cas d'erreur).
    """
    audio_path = record_audio(duration)

    try:
        with open(audio_path, "rb") as f:
            resp = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        text = (resp.text or "").strip()
        return text or None

    except Exception as e:
        print("[STT] Error:", e)
        return None

    finally:
        try:
            os.remove(audio_path)
        except OSError:
            pass

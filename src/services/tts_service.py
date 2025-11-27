# src/services/tts_service.py

import os
import tempfile
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_tts_audio(text: str) -> str:
    """
    Génère un fichier .wav de synthèse vocale à partir d'un texte
    et retourne le chemin du fichier.
    """
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")

    try:
        audio = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            format="wav",
        )
        with open(tmp.name, "wb") as f:
            f.write(audio.read())
        return tmp.name

    except Exception as e:
        print("[TTS] Error:", e)
        return ""

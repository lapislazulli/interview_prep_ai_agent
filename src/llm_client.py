# src/llm_client.py

import os
import json
from openai import OpenAI

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"

class LLMClient:
    def __init__(self):
        # IMPORTANT: Read env variables here (AFTER load_dotenv ran)
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in .env")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        return resp.choices[0].message.content

    def chat_json(self, system_prompt: str, user_prompt: str, schema_hint: str):
        full = (
            f"{user_prompt}\n\n"
            "Répond STRICTEMENT en JSON.\n"
            f"Format attendu: {schema_hint}"
        )
        raw = self.chat(system_prompt, full)

        try:
            return json.loads(raw)
        except:
            start = raw.find("{")
            end = raw.rfind("}")
            return json.loads(raw[start:end+1])

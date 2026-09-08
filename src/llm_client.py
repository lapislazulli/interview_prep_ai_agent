# src/llm_client.py

import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_OPENAI_MODEL = "gpt-4o-mini"
MAX_JSON_RETRIES = 2


class LLMClient:
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)

        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY in environment / .env")

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def chat(self, system_prompt: str, user_prompt: str) -> str:
        """Call the LLM and return the plain text response."""
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""

    def chat_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema_hint: str,
        fallback: dict | None = None,
    ) -> dict:
        """
        Call the LLM and parse the response as JSON.

        Retries up to MAX_JSON_RETRIES times when the model returns
        malformed JSON. If all retries fail, returns `fallback` (or {}).
        """
        full_prompt = (
            f"{user_prompt}\n\n"
            "Répond STRICTEMENT en JSON valide, sans balises Markdown.\n"
            f"Format attendu :\n{schema_hint}"
        )

        for attempt in range(1, MAX_JSON_RETRIES + 2):  # +2 → 1 initial + retries
            raw = self.chat(system_prompt, full_prompt)
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                # Try to extract the first {...} block from the response
                start = raw.find("{")
                end = raw.rfind("}")
                if start != -1 and end != -1 and end > start:
                    try:
                        return json.loads(raw[start : end + 1])
                    except json.JSONDecodeError:
                        pass

                logger.warning(
                    "[LLMClient] JSON parse failed (attempt %d/%d). Raw response: %r",
                    attempt,
                    MAX_JSON_RETRIES + 1,
                    raw[:300],
                )

        logger.error("[LLMClient] All JSON retries exhausted. Returning fallback.")
        return fallback if fallback is not None else {}

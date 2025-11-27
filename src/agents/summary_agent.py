from typing import List
from llm_client import LLMClient
from models.data_models import CVData, JobData, QAExchange


class SummaryAgent:
    """
    Génère une page Notion (Markdown).
    """

    def __init__(self, llm: LLMClient, cv: CVData, job: JobData, history: List[QAExchange]):
        self.llm = llm
        self.cv = cv
        self.job = job
        self.history = history

    def generate_notion_markdown(self) -> str:
        system_prompt = """
Tu es un coach en entretien.
[... SAME PROMPT ...]
"""

        history_serialized = [
            {"question": h.question, "answer": h.answer}
            for h in self.history
        ]

        user_prompt = f"""
CV:
{self.cv.structured}

Fiche de poste:
{self.job.structured}

Historique:
{history_serialized}
"""

        return self.llm.chat(system_prompt, user_prompt)

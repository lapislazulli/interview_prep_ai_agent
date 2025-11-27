from typing import Dict, Any
from llm_client import LLMClient
from models.data_models import CVData, JobData


class QuestionAgent:
    """
    Génère les premières questions + un résumé du profil.
    """

    def __init__(self, llm: LLMClient, cv: CVData, job: JobData):
        self.llm = llm
        self.cv = cv
        self.job = job

    def generate_questions(self) -> Dict[str, Any]:
        system_prompt = """
Tu es un recruteur qui prépare un entretien.
[... SAME FIREWALL PROMPT ...]
"""

        user_prompt = f"""
Fiche de poste:
{self.job.structured}

CV:
{self.cv.structured}
"""

        schema_hint = """{
  "questions": ["Pouvez-vous me décrire un projet récent ?"],
  "profile_insights": ["Profil solide techniquement avec bonne expérience."]
}"""

        return self.llm.chat_json(system_prompt, user_prompt, schema_hint)

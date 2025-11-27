# models/memory.py

from typing import List
from models.data_models import QAExchange

class ConversationMemory:
    def __init__(self):
        self.history: List[QAExchange] = []

    def add_exchange(self, q: str, a: str):
        self.history.append(QAExchange(question=q, answer=a))

    def get_history(self):
        return self.history

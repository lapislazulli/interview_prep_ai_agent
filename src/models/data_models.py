# models/data_models.py

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CVData:
    raw_text: str
    structured: Dict[str, Any]

@dataclass
class JobData:
    raw_text: str
    structured: Dict[str, Any]

@dataclass
class QAExchange:
    question: str
    answer: str

# src/utils/profile_export.py
#
# Helpers to persist CV + job structured data to disk
# so the LiveKit/Hedra worker can load them without re-parsing.

import json
import logging
from pathlib import Path

from models.data_models import CVData, JobData

logger = logging.getLogger(__name__)

EXPORT_DIR = Path("exports")
CV_JSON_PATH = EXPORT_DIR / "last_cv.json"
JOB_JSON_PATH = EXPORT_DIR / "last_job.json"


def export_cv(cv: CVData) -> None:
    """Serialize CVData.structured → exports/last_cv.json."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with CV_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(cv.structured, f, ensure_ascii=False, indent=2)
    logger.info("[ProfileExport] CV written → %s", CV_JSON_PATH)


def export_job(job: JobData) -> None:
    """Serialize JobData.structured → exports/last_job.json."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    with JOB_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(job.structured, f, ensure_ascii=False, indent=2)
    logger.info("[ProfileExport] Job written → %s", JOB_JSON_PATH)


def load_cv() -> CVData:
    """Load CVData from exports/last_cv.json."""
    if not CV_JSON_PATH.exists():
        raise FileNotFoundError(f"[ProfileExport] {CV_JSON_PATH} not found. Run the Streamlit app first.")
    with CV_JSON_PATH.open("r", encoding="utf-8") as f:
        structured = json.load(f)
    return CVData(raw_text="", structured=structured)


def load_job() -> JobData:
    """Load JobData from exports/last_job.json."""
    if not JOB_JSON_PATH.exists():
        raise FileNotFoundError(f"[ProfileExport] {JOB_JSON_PATH} not found. Run the Streamlit app first.")
    with JOB_JSON_PATH.open("r", encoding="utf-8") as f:
        structured = json.load(f)
    return JobData(raw_text="", structured=structured)

# src/utils/profile_export.py
#
# 1) Ask user for CV file + job URL
# 2) Use your existing services (cv_parser + job_scraper)
# 3) Save structured JSON into exports/last_cv.json and exports/last_job.json

import os
import json
from pathlib import Path

from services.cv_parser import parse_cv  # adapt to your real function name
from services.job_scraper import scrape_job  # adapt to your real function name
from models.data_models import CVData, JobData


EXPORT_DIR = Path("exports")
CV_JSON_PATH = EXPORT_DIR / "last_cv.json"
JOB_JSON_PATH = EXPORT_DIR / "last_job.json"


def export_profile(cv_path: str, job_url: str) -> None:
    """
    Runs the multi-agent brain on the CV + job posting once
    and writes the structured result for the LiveKit worker.
    """

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1) Parse CV -------------------------------------------------
    print(f"[ProfileExport] 📄 Parsing CV: {cv_path}")
    cv: CVData = parse_cv(cv_path)  # make sure this returns a CVData

    # --- 2) Scrape / parse job posting ------------------------------
    print(f"[ProfileExport] 🔗 Scraping job posting: {job_url}")
    job: JobData = scrape_job(job_url)  # make sure this returns a JobData

    # --- 3) Dump structured data to JSON ----------------------------
    print(f"[ProfileExport] Writing {CV_JSON_PATH}")
    with CV_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(cv.structured, f, ensure_ascii=False, indent=2)

    print(f"[ProfileExport] Writing {JOB_JSON_PATH}")
    with JOB_JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(job.structured, f, ensure_ascii=False, indent=2)

    print("\n✅ Profile export complete.")
    print(f"   CV JSON : {CV_JSON_PATH}")
    print(f"   Job JSON: {JOB_JSON_PATH}")
    print("   You can now start the LiveKit + Hedra interviewer worker.\n")


if __name__ == "__main__":
    cv_path = input("Path to your CV PDF: ").strip()
    job_url = input("Indeed / job posting URL: ").strip()

    export_profile(cv_path, job_url)

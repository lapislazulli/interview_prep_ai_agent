# src/services/job_scraper.py

import os
import json
import datetime
import requests

# 🔧 FIXED: absolute imports (Streamlit compatible)
from models.data_models import JobData
from config import HASDATA_API_KEY, HASDATA_INDEED_JOB_URL


def scrape_job_url(job_url: str) -> JobData:
    """
    Récupère une fiche de poste via HasData et sauvegarde automatiquement un JSON.
    Lit correctement les infos dans raw_payload['job'].
    """

    if not HASDATA_API_KEY:
        print("[HasData] ERROR: HASDATA_API_KEY manquant.")
        return JobData(raw_text="", structured={})

    # --- Appel API HasData ---
    try:
        resp = requests.get(
            HASDATA_INDEED_JOB_URL,
            params={"url": job_url},
            headers={"x-api-key": HASDATA_API_KEY},
            timeout=30
        )
        resp.raise_for_status()
        data = resp.json()   # data = { "requestMetadata": ..., "job": {...} }
    except Exception as e:
        print(f"[HasData] ERREUR API: {e}")
        return JobData(raw_text="", structured={})

    # --- Accès au bloc "job" ---
    job_obj = data.get("job", {}) or {}

    title = job_obj.get("title", "")
    company = job_obj.get("company", "")
    location = job_obj.get("location", "")

    description = job_obj.get("description") or ""
    clean_description = " ".join(description.split())

    raw_text_parts = [x for x in [title, company, location, description] if x]
    raw_text = "\n\n".join(raw_text_parts)

    structured = {
        "title": title,
        "company": company,
        "location": location,
        "description": description,
        "clean_description": clean_description,
        "details": job_obj.get("details", {}),
        "benefits": job_obj.get("benefits", []),
        "raw_payload": data
    }

    # --- Sauvegarde JSON dans /exports ---
    os.makedirs("exports", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    path = os.path.join("exports", f"job_{timestamp}.json")

    with open(path, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)

    print(f"[HasData] JSON créé automatiquement → {path}")

    return JobData(raw_text=raw_text, structured=structured)

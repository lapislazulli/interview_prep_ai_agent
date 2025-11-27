import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")



# HasData – Indeed Job API
HASDATA_API_KEY = os.getenv("HASDATA_API_KEY")
HASDATA_INDEED_JOB_URL = "https://api.hasdata.com/scrape/indeed/job"

# OpenAI – TTS
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Notion
NOTION_API_KEY = os.getenv("NOTION_API_KEY")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

# Local backup export
NOTION_OUTPUT_PATH = "notion_page.md"

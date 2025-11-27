import requests
from config import NOTION_API_KEY, NOTION_DATABASE_ID, NOTION_OUTPUT_PATH


def save_markdown_locally(markdown: str) -> None:
    with open(NOTION_OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(markdown)
    print(f"[Notion] Markdown sauvegardé dans {NOTION_OUTPUT_PATH}")


def _chunk_text(text: str, max_len: int = 1800):
    chunks = []
    current = ""

    for line in text.split("\n"):
        if len(current) + len(line) + 1 <= max_len:
            current += line + "\n"
        else:
            if current:
                chunks.append(current.rstrip("\n"))
            while len(line) > max_len:
                chunks.append(line[:max_len])
                line = line[max_len:]
            current = line + "\n"

    if current.strip():
        chunks.append(current.rstrip("\n"))

    return chunks


def create_notion_page(title: str, markdown: str) -> None:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        print("[Notion] API key ou database ID manquant, export local uniquement.")
        save_markdown_locally(markdown)
        return

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    chunks = _chunk_text(markdown, max_len=1800)

    children = [{
        "object": "block",
        "type": "paragraph",
        "paragraph": {
            "rich_text": [{"type": "text", "text": {"content": chunk}}]
        },
    } for chunk in chunks]

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {"Name": {"title": [{"text": {"content": title}}]}},
        "children": children,
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    if resp.status_code >= 400:
        print(f"[Notion] Erreur {resp.status_code}: {resp.text}")
        save_markdown_locally(markdown)
    else:
        print("[Notion] Page créée avec succès.")

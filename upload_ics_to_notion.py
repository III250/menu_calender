import os
import subprocess
import requests
import glob
from datetime import date

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_latest_ics():
    files = glob.glob("menu-*.ics")
    if not files:
        raise FileNotFoundError("ICS file not found")
    return files[0]

def commit_ics(filename):
    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", filename], check=True)
    subprocess.run(["git", "commit", "-m", f"Update {filename}"], check=True)
    subprocess.run(["git", "push"], check=True)

def clear_notion_page():
    url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    blocks = res.json()["results"]

    for block in blocks:
        delete_url = f"https://api.notion.com/v1/blocks/{block['id']}"
        requests.delete(delete_url, headers=HEADERS)

def post_to_notion(filename):
    today = date.today()
    year = today.year + (today.month // 12)
    month = today.month % 12 + 1

    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{filename}"

    url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    payload = {
        "children": [
            {
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": f"{year}年{month}月分 献立カレンダー"
                            }
                        }
                    ]
                }
            },
            {
                "object": "block",
                "type": "file",
                "file": {
                    "type": "external",
                    "external": {
                        "url": raw_url
                    }
                }
            }
        ]
    }

    res = requests.patch(url, headers=HEADERS, json=payload)
    res.raise_for_status()

def main():
    filename = get_latest_ics()
    commit_ics(filename)
    clear_notion_page()
    post_to_notion(filename)
    print(f"{filename} uploaded and page refreshed")

if __name__ == "__main__":
    main()

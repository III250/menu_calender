import os
import subprocess
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]
GITHUB_REPO = os.environ["GITHUB_REPOSITORY"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def commit_ics():
    subprocess.run(["git", "config", "user.name", "github-actions"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True)
    subprocess.run(["git", "add", "menu.ics"], check=True)
    subprocess.run(["git", "commit", "-m", "Update menu.ics"], check=True)
    subprocess.run(["git", "push"], check=True)

def post_to_notion():
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/menu.ics"

    url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    payload = {
        "children": [
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
    commit_ics()
    post_to_notion()
    print("menu.ics linked to Notion")

if __name__ == "__main__":
    main()

import os
import requests

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
PAGE_ID = os.environ["NOTION_PAGE_ID"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def upload_ics():
    # Step 1: upload URL取得
    res = requests.post("https://api.notion.com/v1/files", headers=HEADERS)
    res.raise_for_status()
    data = res.json()

    upload_url = data["upload_url"]
    file_id = data["id"]

    # Step 2: ファイルアップロード
    with open("menu.ics", "rb") as f:
        up = requests.post(upload_url, files={"file": f})
        up.raise_for_status()

    # Step 3: ページにファイルブロック追加
    block_url = f"https://api.notion.com/v1/blocks/{PAGE_ID}/children"
    payload = {
        "children": [
            {
                "object": "block",
                "type": "file",
                "file": {
                    "type": "external",
                    "external": {
                        "url": f"https://api.notion.com/v1/files/{file_id}"
                    }
                }
            }
        ]
    }

    res = requests.patch(block_url, headers=HEADERS, json=payload)
    res.raise_for_status()

    print("menu.ics uploaded to Notion")

if __name__ == "__main__":
    upload_ics()

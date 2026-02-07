import os
import requests
from datetime import datetime, timedelta
from ics import Calendar, Event

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_menu_list():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=NOTION_HEADERS)
    res.raise_for_status()
    data = res.json()

    menus = []
    for r in data["results"]:
        title_prop = r["properties"]["名前"]["title"]
        if not title_prop:
            continue
        title = title_prop[0]["plain_text"]
        menus.append(title)

    return menus

def create_ics(menus):
    cal = Calendar()
    today = datetime.today()

    for i, menu in enumerate(menus):
        e = Event()
        e.name = menu
        e.begin = (today + timedelta(days=i)).date()
        e.make_all_day()
        cal.events.add(e)

    with open("menu.ics", "w", encoding="utf-8") as f:
        f.writelines(cal)

def main():
    menus = get_menu_list()
    create_ics(menus)
    print("menu.ics created")

if __name__ == "__main__":
    main()

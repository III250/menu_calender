import os
import random
import requests
from datetime import date, timedelta
from ics import Calendar, Event

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_menu_list():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=HEADERS)
    res.raise_for_status()
    data = res.json()

    menus = []
    for r in data["results"]:
        title_prop = r["properties"]["名前"]["title"]
        if title_prop:
            menus.append(title_prop[0]["plain_text"])

    if len(menus) < 2:
        raise ValueError("献立は2件以上必要です")

    return menus

def shuffle_no_repeat(menus, days):
    result = []
    prev = None
    for _ in range(days):
        choices = [m for m in menus if m != prev]
        pick = random.choice(choices)
        result.append(pick)
        prev = pick
    return result

def create_ics(menu_sequence):
    cal = Calendar()
    start = date.today().replace(day=1)

    for i, menu in enumerate(menu_sequence):
        e = Event()
        e.name = menu
        e.begin = start + timedelta(days=i)
        e.make_all_day()
        cal.events.add(e)

    with open("menu.ics", "w", encoding="utf-8") as f:
        f.writelines(cal)

def main():
    menus = get_menu_list()
    menu_sequence = shuffle_no_repeat(menus, 31)
    create_ics(menu_sequence)
    print("menu.ics generated")

if __name__ == "__main__":
    main()

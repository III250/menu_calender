import os
import random
import requests
from datetime import date, timedelta
from ics import Calendar, Event
import calendar

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_next_month():
    today = date.today()
    year = today.year + (today.month // 12)
    month = today.month % 12 + 1
    return year, month

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

def create_ics(menu_sequence, year, month):
    cal = Calendar()
    days_in_month = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)

    for i, menu in enumerate(menu_sequence):
        e = Event()
        e.name = menu
        e.begin = start + timedelta(days=i)
        e.make_all_day()
        cal.events.add(e)

    filename = f"menu-{year}-{month:02d}.ics"

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cal)

    return filename, year, month

def main():
    year, month = get_next_month()
    menus = get_menu_list()
    days_in_month = calendar.monthrange(year, month)[1]
    sequence = shuffle_no_repeat(menus, days_in_month)
    filename, year, month = create_ics(sequence, year, month)
    print(f"{filename} generated")

if __name__ == "__main__":
    main()

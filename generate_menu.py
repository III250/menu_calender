from datetime import date
from ics import Calendar, Event
import calendar
import random
import requests
import os

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
response = requests.post(url, headers=headers, json={
    "filter": {
        "property": "有効",
        "checkbox": { "equals": True }
    }
})

data = response.json()

menus = [
    r["properties"]["献立名"]["title"][0]["text"]["content"]
    for r in data["results"]
]

today = date.today()
year = today.year + (1 if today.month == 12 else 0)
month = 1 if today.month == 12 else today.month + 1
last_day = calendar.monthrange(year, month)[1]

cal = Calendar()
prev_menu = None

for day in range(1, last_day + 1):
    d = date(year, month, day)
    menu = random.choice([m for m in menus if m != prev_menu])

    e = Event()
    e.name = f"夕食：{menu}"
    e.begin = f"{d} 18:00"
    e.end = f"{d} 19:00"
    cal.events.add(e)

    prev_menu = menu

filename = f"menu_{year}_{month}.ics"
with open(filename, "w", encoding="utf-8") as f:
    f.writelines(cal)

print(filename)

import os
import random
import requests
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

# ===== 環境変数 =====
NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

# ===== Notion API =====
HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

def get_menu_list():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"
    res = requests.post(url, headers=HEADERS)
    res.raise_for_status()

    results = res.json()["results"]
    menus = []

    for r in results:
        title = r["properties"]["名前"]["title"]
        if title:
            menus.append(title[0]["plain_text"])

    if len(menus) < 2:
        raise ValueError("献立は2つ以上必要です")

    return menus

# ===== 翌月の日付リスト =====
def get_next_month_dates():
    today = date.today()
    first = today.replace(day=1) + relativedelta(months=1)
    dates = []
    d = first
    while d.month == first.month:
        dates.append(d)
        d += timedelta(days=1)
    return dates

# ===== 連続しないランダム =====
def generate_menu_schedule(dates, menus):
    result = []
    prev = None
    for d in dates:
        choices = [m for m in menus if m != prev]
        menu = random.choice(choices)
        result.append((d, menu))
        prev = menu
    return result

# ===== ICS生成 =====
def generate_ics(schedule):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Menu Calendar//JP",
    ]

    for d, menu in schedule:
        lines.extend([
            "BEGIN:VEVENT",
            f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{(d + timedelta(days=1)).strftime('%Y%m%d')}",
            f"SUMMARY:{menu}",
            "END:VEVENT",
        ])

    lines.append("END:VCALENDAR")
    return "\n".join(lines)

# ===== メイン処理 =====
def main():
    menus = get_menu_list()
    dates = get_next_month_dates()
    schedule = generate_menu_schedule(dates, menus)

    ics = generate_ics(schedule)
    filename = "menu_next_month.ics"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(ics)

    print(f"{filename} generated")

if __name__ == "__main__":
    main()


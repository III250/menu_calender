import os
import random
import calendar
import requests
from datetime import datetime, timedelta, date

# ===============================
# Notion設定（環境変数）
# ===============================

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["DATABASE_ID"]

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# ===============================
# 次の月を取得
# ===============================

def get_next_month():
    today = datetime.today()
    year = today.year
    month = today.month + 1
    if month == 13:
        month = 1
        year += 1
    return year, month

# ===============================
# Notionの献立マスターから取得
# （タイトルプロパティ名は "名前" 前提）
# ===============================

def get_menu_list_from_notion():
    url = f"https://api.notion.com/v1/databases/{DATABASE_ID}/query"

    menus = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        res = requests.post(url, headers=NOTION_HEADERS, json=payload)
        res.raise_for_status()
        data = res.json()

        for item in data["results"]:
            title_prop = item["properties"]["名前"]["title"]
            if title_prop:
                menus.append(title_prop[0]["plain_text"])

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    if len(menus) == 0:
        raise ValueError("献立マスターが空です")

    return menus

# ===============================
# 一巡方式（重複なし）
# ===============================

def generate_no_repeat_cycle(menus, year, month):
    days_in_month = calendar.monthrange(year, month)[1]

    result = []
    pool = menus.copy()
    random.shuffle(pool)

    for _ in range(days_in_month):

        if not pool:
            pool = menus.copy()
            random.shuffle(pool)

        pick = pool.pop(0)
        result.append(pick)

    return result

# ===============================
# ICS作成
# ===============================

def create_ics(sequence, year, month):
    filename = f"menu-{year}-{month:02d}.ics"
    start_date = date(year, month, 1)

    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Menu Calendar//JP\n")

        for i, menu in enumerate(sequence):
            event_date = start_date + timedelta(days=i)
            date_str = event_date.strftime("%Y%m%d")

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{year}{month:02d}{i}@menu\n")
            f.write(f"DTSTAMP:{date_str}T000000Z\n")
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
            f.write(f"SUMMARY:{menu}\n")
            f.write("END:VEVENT\n")

        f.write("END:VCALENDAR\n")

    return filename

# ===============================
# メイン
# ===============================

def main():
    year, month = get_next_month()

    menus = get_menu_list_from_notion()

    if len(menus) < 2:
        raise ValueError("献立は2個以上必要です")

    sequence = generate_no_repeat_cycle(menus, year, month)

    filename = create_ics(sequence, year, month)

    print(f"{filename} を生成しました")

if __name__ == "__main__":
    main()

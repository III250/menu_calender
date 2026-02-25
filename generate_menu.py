import os
import random
import calendar
import requests
from datetime import datetime, timedelta, date

# ===============================
# Notion設定
# ===============================

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

if not NOTION_TOKEN:
    raise ValueError("NOTION_TOKEN が設定されていません")

if not NOTION_DATABASE_ID:
    raise ValueError("NOTION_DATABASE_ID が設定されていません")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

# ===============================
# 次月取得
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
# Notionからメニュー取得
# ===============================

def get_menu_list():
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    menus = []
    has_more = True
    next_cursor = None

    while has_more:
        payload = {}
        if next_cursor:
            payload["start_cursor"] = next_cursor

        res = requests.post(url, headers=HEADERS, json=payload)
        res.raise_for_status()
        data = res.json()

        for item in data["results"]:
            props = item["properties"]

            if not props["名前"]["title"]:
                continue

            name = props["名前"]["title"][0]["plain_text"]

            categories = []
            if props["分類"]["multi_select"]:
                categories = [c["name"] for c in props["分類"]["multi_select"]]

            menus.append({
                "name": name,
                "categories": categories
            })

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    return menus

# ===============================
# 月間生成ロジック
# ===============================

def generate_menu(menus, year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)

    # 曜日→カテゴリ
    weekday_category = {
        0: "炊飯器",      # 月
        1: "フライパン",  # 火
        2: "魚",          # 水
        3: "フライパン",  # 木
        4: "炊飯器",      # 金
        5: "パパ",        # 土
        6: "フライパン"   # 日
    }

    # カテゴリごとのマスター
    category_master = {}
    for m in menus:
        for cat in m["categories"]:
            category_master.setdefault(cat, []).append(m)

    # pool作成
    category_pool = {}
    for cat, items in category_master.items():
        shuffled = items.copy()
        random.shuffle(shuffled)
        category_pool[cat] = shuffled

    result = []

    for i in range(days_in_month):
        current_date = start_date + timedelta(days=i)
        weekday = current_date.weekday()
        category = weekday_category[weekday]

        if category not in category_master:
            raise ValueError(f"{category} のメニューがありません")

        # 一巡したらリセット
        if not category_pool[category]:
            category_pool[category] = category_master[category].copy()
            random.shuffle(category_pool[category])

        # 翌週同曜日禁止
        last_week_name = None
        if i >= 7:
            last_week_name = result[i-7]["name"]

        # 候補選択
        pick = None
        for idx, candidate in enumerate(category_pool[category]):
            if candidate["name"] != last_week_name:
                pick = category_pool[category].pop(idx)
                break

        # 全部ダメなら再シャッフル
        if pick is None:
            category_pool[category] = category_master[category].copy()
            random.shuffle(category_pool[category])
            pick = category_pool[category].pop()

        result.append(pick)

    return result

# ===============================
# ICS生成
# ===============================

def create_ics(sequence, year, month):
    filename = f"menu-{year}-{month:02d}.ics"
    start_date = date(year, month, 1)

    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")

        for i, menu in enumerate(sequence):
            event_date = start_date + timedelta(days=i)
            date_str = event_date.strftime("%Y%m%d")

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{year}{month:02d}{i}@menu\n")
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
            f.write(f"SUMMARY:{menu['name']}\n")
            f.write("END:VEVENT\n")

        f.write("END:VCALENDAR\n")

    return filename

# ===============================
# main
# ===============================

def main():
    year, month = get_next_month()
    menus = get_menu_list()
    sequence = generate_menu(menus, year, month)
    create_ics(sequence, year, month)
    print("献立生成完了")

if __name__ == "__main__":
    main()

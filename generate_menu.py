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

NOTION_HEADERS = {
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
# Notionから取得
# 魚判定 = 名前に「魚」
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

        res = requests.post(url, headers=NOTION_HEADERS, json=payload)
        res.raise_for_status()
        data = res.json()

        for item in data["results"]:
            props = item["properties"]

            if not props["名前"]["title"]:
                continue

            name = props["名前"]["title"][0]["plain_text"]

            materials = ""
            if props["材料"]["rich_text"]:
                materials = props["材料"]["rich_text"][0]["plain_text"]

            recipe = ""
            if props["レシピ"]["rich_text"]:
                recipe = props["レシピ"]["rich_text"][0]["plain_text"]

            menus.append({
                "name": name,
                "materials": materials,
                "recipe": recipe,
                "is_fish": "魚" in name
            })

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    return menus

# ===============================
# 月間生成
# 水曜(2)・金曜(4)は魚固定
# 連続禁止
# 一巡方式
# ===============================
def generate_menu(menus, year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)

    fish_master = [m for m in menus if m["is_fish"]]
    other_master = [m for m in menus if not m["is_fish"]]

    if len(fish_master) < 1:
        raise ValueError("魚メニューが必要です")

    fish_pool = fish_master.copy()
    other_pool = other_master.copy()
    random.shuffle(fish_pool)
    random.shuffle(other_pool)

    result = []
    last_name = None

    for i in range(days_in_month):
        current_date = start_date + timedelta(days=i)
        weekday = current_date.weekday()  # 月0〜日6

        # 水曜(2)・金曜(4)は魚
        if weekday in [2, 4]:

            if not fish_pool:
                fish_pool = fish_master.copy()
                random.shuffle(fish_pool)

            # 連続禁止
            for idx, m in enumerate(fish_pool):
                if m["name"] != last_name:
                    pick = fish_pool.pop(idx)
                    break
            else:
                fish_pool = fish_master.copy()
                random.shuffle(fish_pool)
                pick = fish_pool.pop()

        else:
            if not other_pool:
                other_pool = other_master.copy()
                random.shuffle(other_pool)

            for idx, m in enumerate(other_pool):
                if m["name"] != last_name:
                    pick = other_pool.pop(idx)
                    break
            else:
                other_pool = other_master.copy()
                random.shuffle(other_pool)
                pick = other_pool.pop()

        result.append(pick)
        last_name = pick["name"]

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

            desc_parts = []
            if menu["materials"]:
                desc_parts.append("【材料】\\n" + menu["materials"])
            if menu["recipe"]:
                desc_parts.append("【レシピ】\\n" + menu["recipe"])

            description = "\\n\\n".join(desc_parts)

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{year}{month:02d}{i}@menu\n")
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
            f.write(f"SUMMARY:{menu['name']}\n")
            f.write(f"DESCRIPTION:{description}\n")
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

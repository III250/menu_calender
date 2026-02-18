import os
import random
import calendar
import requests
from datetime import datetime, timedelta, date

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

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
# Notion取得（魚=名前に「魚」）
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
# 月間生成（完全保証版）
# ===============================
def generate_menu(menus, year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)

    fish_master = [m for m in menus if m["is_fish"]]
    other_master = [m for m in menus if not m["is_fish"]]

    if len(fish_master) < 2:
        raise ValueError("魚メニューが2つ以上必要です")

    fish_pool = fish_master.copy()
    other_pool = other_master.copy()
    random.shuffle(fish_pool)
    random.shuffle(other_pool)

    result = []
    current_day = 0

    while current_day < days_in_month:
        current_date = start_date + timedelta(days=current_day)
        weekday = current_date.weekday()

        # 月曜なら1週間まとめて作る
        if weekday == 0 and current_day + 4 < days_in_month:

            # 平日5日分作る
            week_block = []

            # 魚2つ取得
            if len(fish_pool) < 2:
                fish_pool = fish_master.copy()
                random.shuffle(fish_pool)

            fish_two = [fish_pool.pop(), fish_pool.pop()]

            # 非魚3つ取得
            if len(other_pool) < 3:
                other_pool = other_master.copy()
                random.shuffle(other_pool)

            other_three = [other_pool.pop() for _ in range(3)]

            # 位置決め（連続禁止パターンのみ）
            valid_patterns = [
                [1,0,1,0,0],
                [1,0,0,1,0],
                [1,0,0,0,1],
                [0,1,0,1,0],
                [0,1,0,0,1],
                [0,0,1,0,1],
            ]

            pattern = random.choice(valid_patterns)

            fish_idx = 0
            other_idx = 0

            for flag in pattern:
                if flag == 1:
                    week_block.append(fish_two[fish_idx])
                    fish_idx += 1
                else:
                    week_block.append(other_three[other_idx])
                    other_idx += 1

            result.extend(week_block)
            current_day += 5

        else:
            # 土日や月末端数
            if not other_pool:
                other_pool = other_master.copy()
                random.shuffle(other_pool)

            result.append(other_pool.pop())
            current_day += 1

    return result[:days_in_month]

# ===============================
# ICS生成
# ===============================
def create_ics(sequence, year, month):
    filename = f"menu-{year}-{month:02d}.ics"
    start_date = date(year, month, 1)

    with open(filename, "w", encoding="utf-8") as f:
        f.write("BEGIN:VCALENDAR\nVERSION:2.0\n")

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

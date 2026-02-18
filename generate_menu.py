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
# Notionから献立取得
# 魚判定 = 名前に「魚」が含まれる
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
                "is_fish": "魚" in name  # ← ここが魚判定
            })

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    if not menus:
        raise ValueError("献立マスターが空です")

    return menus

# ===============================
# 月間献立生成
# ・平日(月〜金)に魚2回
# ・魚連続禁止
# ・一巡方式
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
    last_was_fish = False

    for i in range(days_in_month):
        current_date = start_date + timedelta(days=i)
        weekday = current_date.weekday()  # 月0〜日6

        # 月曜ならその週の魚配置を決定
        if weekday == 0:
            weekly_fish_days = random.sample([0,1,2,3,4], 2)

        use_fish = False
        if weekday < 5 and weekday in weekly_fish_days:
            use_fish = True

        if use_fish and not last_was_fish:
            if not fish_pool:
                fish_pool = fish_master.copy()
                random.shuffle(fish_pool)

            pick = fish_pool.pop()
            last_was_fish = True

        else:
            if not other_pool:
                other_pool = other_master.copy()
                random.shuffle(other_pool)

            pick = other_pool.pop()
            last_was_fish = False

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

            description_parts = []
            if menu["materials"]:
                description_parts.append("【材料】\\n" + menu["materials"])
            if menu["recipe"]:
                description_parts.append("【レシピ】\\n" + menu["recipe"])

            description = "\\n\\n".join(description_parts)

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{year}{month:02d}{i}@menu\n")
            f.write(f"DTSTAMP:{date_str}T000000Z\n")
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
    filename = create_ics(sequence, year, month)
    print(f"{filename} を生成しました")

if __name__ == "__main__":
    main()

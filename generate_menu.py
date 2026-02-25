import os
import json
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

STATE_FILE = "menu_state.json"

# ===============================
# 状態保存
# ===============================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "order": {},
        "last_week": []
    }

def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

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

            if "分類" in props and props["分類"]["multi_select"]:
                categories = [c["name"] for c in props["分類"]["multi_select"]]

            materials = ""
            if "材料" in props and props["材料"]["rich_text"]:
                materials = "".join(
                    t["plain_text"] for t in props["材料"]["rich_text"]
                )

            recipe = ""
            if "レシピ" in props and props["レシピ"]["rich_text"]:
                recipe = "".join(
                    t["plain_text"] for t in props["レシピ"]["rich_text"]
                )

            menus.append({
                "name": name,
                "categories": categories,
                "materials": materials,
                "recipe": recipe
            })

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    return menus


# ===============================
# ICSエスケープ
# ===============================

def escape_ics(text):

    if not text:
        return ""

    text = text.replace("\\", "\\\\")
    text = text.replace(",", "\\,")
    text = text.replace(";", "\\;")
    text = text.replace("\n", "\\n")

    return text


# ===============================
# メニュー生成（完全順番・キュー方式）
# ===============================

def generate_menu(menus, year, month):

    state = load_state()

    last_week = state.get("last_week", [])

    days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)

    weekday_category = {
        0: "炊飯器",
        1: "フライパン",
        2: "魚",
        3: "フライパン",
        4: "炊飯器",
        5: "パパ",
        6: "フライパン"
    }

    # カテゴリ別キュー
    category_queue = {}

    for m in menus:
        for cat in m["categories"]:
            category_queue.setdefault(cat, []).append(m)

    # 保存された順序復元
    saved_order = state.get("order", {})

    for cat in category_queue:

        if cat in saved_order:

            saved_names = saved_order[cat]

            lookup = {m["name"]: m for m in category_queue[cat]}

            new_queue = []

            for name in saved_names:
                if name in lookup:
                    new_queue.append(lookup[name])

            for m in category_queue[cat]:
                if m["name"] not in saved_names:
                    new_queue.append(m)

            category_queue[cat] = new_queue


    result = []

    for i in range(days):

        d = start_date + timedelta(days=i)
        cat = weekday_category[d.weekday()]

        if cat not in category_queue:
            raise ValueError(f"{cat} のメニューがありません")

        queue = category_queue[cat]

        attempts = 0

        # 重複回避
        while attempts < len(queue):

            menu = queue[0]
            name = menu["name"]

            duplicate = False

            if i >= 7 and result[i-7]["name"] == name:
                duplicate = True

            if name in last_week:
                duplicate = True

            if not duplicate:
                break

            queue.append(queue.pop(0))
            attempts += 1

        menu = queue.pop(0)
        queue.append(menu)

        result.append(menu)


    # 状態保存
    state["order"] = {
        cat: [m["name"] for m in queue]
        for cat, queue in category_queue.items()
    }

    state["last_week"] = [m["name"] for m in result[-7:]]

    save_state(state)

    return result


# ===============================
# ICS生成（終日予定）
# ===============================

def create_ics(sequence, year, month):

    filename = f"menu-{year}-{month:02d}.ics"

    start_date = date(year, month, 1)

    with open(filename, "w", encoding="utf-8") as f:

        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Menu Calendar//EN\n")

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

            # 終日予定
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")

            f.write(f"SUMMARY:{escape_ics(menu['name'])}\n")

            if description:
                f.write(f"DESCRIPTION:{escape_ics(description)}\n")

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

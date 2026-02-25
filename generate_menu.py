import os
import json
import calendar
import requests
from datetime import datetime, timedelta, date
from ics import Calendar, Event

STATE_FILE = "menu_state.json"

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

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
# state load/save
# ===============================
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"category_index": {}, "last_week": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===============================
# Notion取得
# ===============================
def get_menu_list():

    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"

    menus = []
    has_more = True
    cursor = None

    while has_more:

        payload = {}
        if cursor:
            payload["start_cursor"] = cursor

        res = requests.post(url, headers=HEADERS, json=payload)
        res.raise_for_status()
        data = res.json()

        for item in data["results"]:

            props = item["properties"]

            if not props["名前"]["title"]:
                continue

            name = props["名前"]["title"][0]["plain_text"]

            categories = [
                c["name"] for c in props["分類"]["multi_select"]
            ]

            materials = ""
            if props["材料"]["rich_text"]:
                materials = "".join(
                    t["plain_text"] for t in props["材料"]["rich_text"]
                )

            recipe = ""
            if props["レシピ"]["rich_text"]:
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
        cursor = data["next_cursor"]

    return menus


# ===============================
# エスケープ
# ===============================
def escape(text):

    if not text:
        return ""

    return text.replace("\\", "\\\\").replace("\n", "\\n")


# ===============================
# 献立生成（順番循環・重複禁止）
# ===============================
def generate_menu(menus, year, month):

    state = load_state()

    weekday_category = {
        0: "炊飯器",
        1: "フライパン",
        2: "魚",
        3: "フライパン",
        4: "炊飯器",
        5: "パパ",
        6: "フライパン"
    }

    category_master = {}

    for m in menus:
        for c in m["categories"]:
            category_master.setdefault(c, []).append(m)

    category_index = state.get("category_index", {})
    prev_last_week = state.get("last_week", [])

    result = []

    for i in range(calendar.monthrange(year, month)[1]):

        d = date(year, month, 1) + timedelta(days=i)
        category = weekday_category[d.weekday()]

        items = category_master[category]

        idx = category_index.get(category, 0)

        for _ in range(len(items)):

            candidate = items[idx]

            last_week_duplicate = (
                i >= 7 and candidate["name"] == result[i-7]["name"]
            )

            prev_month_duplicate = candidate["name"] in prev_last_week

            if not last_week_duplicate and not prev_month_duplicate:
                break

            idx = (idx + 1) % len(items)

        result.append(candidate)

        category_index[category] = (idx + 1) % len(items)

    state["category_index"] = category_index
    state["last_week"] = [m["name"] for m in result[-7:]]

    save_state(state)

    return result


# ===============================
# ICS生成
# ===============================
def create_ics(sequence, year, month):

    cal = Calendar()

    for i, menu in enumerate(sequence):

        d = date(year, month, 1) + timedelta(days=i)

        e = Event()
        e.name = menu["name"]
        e.begin = d

        desc = ""

        if menu["materials"]:
            desc += "【材料】\n" + menu["materials"] + "\n\n"

        if menu["recipe"]:
            desc += "【レシピ】\n" + menu["recipe"]

        e.description = desc

        cal.events.add(e)

    filename = f"menu-{year}-{month:02d}.ics"

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cal)

    return filename


# ===============================
# main
# ===============================
def main():

    year, month = get_next_month()

    menus = get_menu_list()

    sequence = generate_menu(menus, year, month)

    filename = create_ics(sequence, year, month)

    print("生成:", filename)


if __name__ == "__main__":
    main()

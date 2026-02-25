import os
import calendar
import requests
import json
from datetime import datetime, timedelta, date

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

INDEX_FILE = "menu_index.json"


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
# index読み込み
# ===============================
def load_index():

    if os.path.exists(INDEX_FILE):

        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {}


# ===============================
# index保存
# ===============================
def save_index(index):

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)


# ===============================
# Notionから取得
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

            materials = ""
            if "材料" in props and props["材料"]["rich_text"]:
                materials = "".join(t["plain_text"] for t in props["材料"]["rich_text"])

            recipe = ""
            if "レシピ" in props and props["レシピ"]["rich_text"]:
                recipe = "".join(t["plain_text"] for t in props["レシピ"]["rich_text"])

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
# 順番ローテーション生成
# ===============================
def generate_menu(menus, year, month):

    weekday_category = {
        0: "炊飯器",
        1: "フライパン",
        2: "魚",
        3: "フライパン",
        4: "炊飯器",
        5: "パパ",
        6: "フライパン"
    }

    days = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)

    category_master = {}

    for menu in menus:
        for cat in menu["categories"]:
            category_master.setdefault(cat, []).append(menu)

    index = load_index()

    result = []

    for i in range(days):

        d = start_date + timedelta(days=i)

        cat = weekday_category[d.weekday()]

        if cat not in category_master:
            raise Exception(f"{cat} メニュー無し")

        current_index = index.get(cat, 0)

        menu = category_master[cat][current_index]

        result.append(menu)

        index[cat] = (current_index + 1) % len(category_master[cat])

    save_index(index)

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

            d = start_date + timedelta(days=i)

            description = ""

            if menu["materials"]:
                description += "【材料】\\n" + menu["materials"] + "\\n\\n"

            if menu["recipe"]:
                description += "【レシピ】\\n" + menu["recipe"]

            f.write("BEGIN:VEVENT\n")

            f.write(f"UID:{year}{month:02d}{i}@menu\n")

            f.write(f"DTSTART;VALUE=DATE:{d.strftime('%Y%m%d')}\n")

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

    print(filename, "生成完了")


if __name__ == "__main__":
    main()

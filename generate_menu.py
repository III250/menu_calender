import os
import json
import calendar
from datetime import datetime, timedelta, date
from notion_client import Client

# ===============================
# 環境変数
# ===============================

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

# ===============================
# Notion client
# ===============================

notion = Client(auth=NOTION_TOKEN)

STATE_FILE = "menu_state.json"

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
# state 読み込み
# ===============================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ===============================
# Notionからメニュー取得（完全対応版）
# ===============================

def load_menu():

    menus = []
    start_cursor = None

    while True:

        if start_cursor:
            response = notion.databases.query(
                database_id=DATABASE_ID,
                start_cursor=start_cursor
            )
        else:
            response = notion.databases.query(
                database_id=DATABASE_ID
            )

        for page in response["results"]:

            props = page["properties"]

            # 名前
            title = props["名前"]["title"]
            if not title:
                continue

            name = title[0]["plain_text"]

            # 分類
            categories = []
            if props["分類"]["multi_select"]:
                categories = [
                    c["name"] for c in props["分類"]["multi_select"]
                ]

            # 材料
            materials = ""
            if "材料" in props and props["材料"]["rich_text"]:
                materials = "".join(
                    t["plain_text"] for t in props["材料"]["rich_text"]
                )

            # レシピ
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

        if not response["has_more"]:
            break

        start_cursor = response["next_cursor"]

    return menus


# ===============================
# ICS エスケープ
# ===============================

def escape(text):

    if not text:
        return ""

    return (
        text.replace("\\", "\\\\")
        .replace(",", "\\,")
        .replace(";", "\\;")
        .replace("\n", "\\n")
    )


# ===============================
# 献立生成（カテゴリ順＋index保存）
# ===============================

def generate_menu(menu_list, year, month):

    weekday_category = {
        0: "炊飯器",
        1: "フライパン",
        2: "魚",
        3: "フライパン",
        4: "炊飯器",
        5: "パパ",
        6: "フライパン"
    }

    # カテゴリごとに分割（Notion順維持）
    category_map = {}

    for menu in menu_list:
        for cat in menu["categories"]:
            category_map.setdefault(cat, []).append(menu)

    state = load_state()

    days = calendar.monthrange(year, month)[1]
    start = date(year, month, 1)

    sequence = []

    for i in range(days):

        d = start + timedelta(days=i)
        cat = weekday_category[d.weekday()]

        if cat not in category_map:
            raise Exception(f"{cat} が空です")

        idx = state.get(cat, 0)

        menu = category_map[cat][idx]

        sequence.append(menu)

        idx += 1
        if idx >= len(category_map[cat]):
            idx = 0

        state[cat] = idx

    save_state(state)

    return sequence


# ===============================
# ICS生成（終日予定）
# ===============================

def create_ics(sequence, year, month):

    filename = f"menu-{year}-{month:02d}.ics"

    start = date(year, month, 1)

    with open(filename, "w", encoding="utf-8") as f:

        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Menu//EN\n")

        for i, menu in enumerate(sequence):

            d = start + timedelta(days=i)

            start_str = d.strftime("%Y%m%d")
            end_str = (d + timedelta(days=1)).strftime("%Y%m%d")

            description = ""

            if menu["materials"]:
                description += "【材料】\\n" + escape(menu["materials"]) + "\\n\\n"

            if menu["recipe"]:
                description += "【レシピ】\\n" + escape(menu["recipe"])

            f.write("BEGIN:VEVENT\n")

            f.write(f"UID:{year}{month:02d}{i}@menu\n")

            # 終日イベント
            f.write(f"DTSTART;VALUE=DATE:{start_str}\n")
            f.write(f"DTEND;VALUE=DATE:{end_str}\n")

            f.write(f"SUMMARY:{escape(menu['name'])}\n")

            if description:
                f.write(f"DESCRIPTION:{description}\n")

            f.write("END:VEVENT\n")

        f.write("END:VCALENDAR\n")

    return filename


# ===============================
# main
# ===============================

def main():

    year, month = get_next_month()

    menus = load_menu()

    sequence = generate_menu(menus, year, month)

    create_ics(sequence, year, month)

    print("生成完了")


if __name__ == "__main__":
    main()

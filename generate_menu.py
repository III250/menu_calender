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

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json"
}

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
# 状態ファイル読み書き
# ===============================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"index": {}, "last_week": []}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


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

            # 名前
            if not props["名前"]["title"]:
                continue

            name = props["名前"]["title"][0]["plain_text"]

            # 分類
            categories = []
            if "分類" in props and props["分類"]["type"] == "multi_select":
                categories = [c["name"] for c in props["分類"]["multi_select"]]

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

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    return menus


# ===============================
# ICSエスケープ
# ===============================

def escape_ics(text):

    if not text:
        return ""

    return (
        text.replace("\\", "\\\\")
            .replace(",", "\\,")
            .replace(";", "\\;")
            .replace("\n", "\\n")
    )


# ===============================
# メニュー生成（順番＋重複禁止＋index保存）
# ===============================

def generate_menu(menus, year, month):

    state = load_state()

    index_state = state.get("index", {})
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

    # カテゴリ別リスト作成
    category_master = {}

    for m in menus:
        for cat in m["categories"]:
            category_master.setdefault(cat, []).append(m)

    result = []

    for i in range(days):

        d = start_date + timedelta(days=i)
        category = weekday_category[d.weekday()]

        if category not in category_master:
            raise ValueError(f"{category} が存在しません")

        items = category_master[category]

        index = index_state.get(category, 0)

        # 重複回避付きで選択
        attempts = 0

        while True:

            menu = items[index]

            name = menu["name"]

            duplicate = False

            # 先週禁止
            if i >= 7 and result[i-7]["name"] == name:
                duplicate = True

            # 前月最終週禁止
            if name in last_week:
                duplicate = True

            if not duplicate:
                break

            index = (index + 1) % len(items)
            attempts += 1

            if attempts > len(items):
                break

        result.append(menu)

        index = (index + 1) % len(items)
        index_state[category] = index

    # 次回用に最後の7日保存
    state["index"] = index_state
    state["last_week"] = [m["name"] for m in result[-7:]]

    save_state(state)

    return result


# ===============================
# ICS生成（終日）
# ===============================

def create_ics(sequence, year, month):

    filename = f"menu-{year}-{month:02d}.ics"

    start_date = date(year, month, 1)

    with open(filename, "w", encoding="utf-8") as f:

        f.write("BEGIN:VCALENDAR\n")
        f.write("VERSION:2.0\n")
        f.write("PRODID:-//Menu Calendar//EN\n")

        for i, menu in enumerate(sequence):

            d = start_date + timedelta(days=i)
            date_str = d.strftime("%Y%m%d")

            description = ""

            if menu["materials"]:
                description += "【材料】\\n" + menu["materials"] + "\\n\\n"

            if menu["recipe"]:
                description += "【レシピ】\\n" + menu["recipe"]

            f.write("BEGIN:VEVENT\n")

            f.write(f"UID:{year}{month:02d}{i}@menu\n")

            # 終日予定（重要）
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
            f.write(f"DTEND;VALUE=DATE:{date_str}\n")

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

    create_ics(sequence, year, month)

    print("献立生成完了")


if __name__ == "__main__":
    main()

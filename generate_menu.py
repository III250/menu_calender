import os
import json
import calendar
import datetime
from ics import Calendar, Event
from notion_client import Client

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["DATABASE_ID"]

STATE_FILE = "menu_state.json"

notion = Client(auth=NOTION_TOKEN)


# =========================
# state読み込み
# =========================

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "category_index": {},
        "last_week_menus": [],
        "last_month_last_week": []
    }


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# =========================
# Notionから献立取得
# =========================

def get_menu_list():

    results = notion.databases.query(
        database_id=DATABASE_ID,
        page_size=100
    )

    menus = {}

    for page in results["results"]:

        props = page["properties"]

        title = props["名前"]["title"][0]["plain_text"]

        category = None
        if "分類" in props and props["分類"]["type"] == "multi_select":
            if props["分類"]["multi_select"]:
                category = props["分類"]["multi_select"][0]["name"]

        ingredients = ""
        if "材料" in props and props["材料"]["type"] == "rich_text":
            if props["材料"]["rich_text"]:
                ingredients = props["材料"]["rich_text"][0]["plain_text"]

        recipe = ""
        if "レシピ" in props and props["レシピ"]["type"] == "rich_text":
            if props["レシピ"]["rich_text"]:
                recipe = props["レシピ"]["rich_text"][0]["plain_text"]

        if category not in menus:
            menus[category] = []

        menus[category].append({
            "title": title,
            "ingredients": ingredients,
            "recipe": recipe
        })

    return menus


# =========================
# カテゴリ順で取得（重複回避付き）
# =========================

def get_next_menu(category, menus, state, forbidden):

    if category not in state["category_index"]:
        state["category_index"][category] = 0

    menu_list = menus[category]

    start = state["category_index"][category]

    for i in range(len(menu_list)):

        idx = (start + i) % len(menu_list)

        menu = menu_list[idx]["title"]

        if menu not in forbidden:

            state["category_index"][category] = (idx + 1) % len(menu_list)

            return menu_list[idx]

    raise Exception(f"{category}で重複しない献立が不足しています")


# =========================
# カレンダー生成
# =========================

def generate_calendar(year, month, menus):

    state = load_state()

    cal = Calendar()

    categories = list(menus.keys())

    last_week = []
    this_month_all = []

    cal_data = calendar.Calendar()

    weeks = cal_data.monthdatescalendar(year, month)

    for week_index, week in enumerate(weeks):

        for day in week:

            if day.month != month:
                continue

            category = categories[day.weekday() % len(categories)]

            forbidden = set(state["last_week_menus"])
            forbidden.update(state["last_month_last_week"])

            menu = get_next_menu(
                category,
                menus,
                state,
                forbidden
            )

            title = menu["title"]

            description = f"""材料:
{menu['ingredients']}

レシピ:
{menu['recipe']}
"""

            event = Event()

            event.name = title
            event.begin = day.isoformat()
            event.make_all_day()

            event.description = description

            cal.events.add(event)

            last_week.append(title)
            this_month_all.append(title)

    # 最終週保存
    state["last_week_menus"] = last_week[-7:]
    state["last_month_last_week"] = last_week[-7:]

    save_state(state)

    return cal


# =========================
# main
# =========================

def main():

    today = datetime.date.today()

    year = today.year
    month = today.month

    menus = get_menu_list()

    cal = generate_calendar(year, month, menus)

    filename = f"menu-{year}-{month:02d}.ics"

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(cal)

    print("generated:", filename)


if __name__ == "__main__":
    main()

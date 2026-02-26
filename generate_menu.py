import os
import json
from datetime import date, timedelta
from collections import defaultdict
from notion_client import Client
from ics import Calendar, Event

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

STATE_FILE = "menu_state.json"
OUTPUT_FILE = "menu_calendar.ics"

START_DATE = date(2026, 1, 1)
END_DATE = date(2026, 12, 31)

weekday_category = {
    0: "炊飯器",
    1: "フライパン",
    2: "魚",
    3: "フライパン",
    4: "炊飯器",
    5: "パパ",
    6: "フライパン"
}


# =====================
# state load/save
# =====================

def load_state():

    if not os.path.exists(STATE_FILE):
        return {}

    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(state):

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# =====================
# Notion load
# =====================

def get_text(prop):

    if "rich_text" in prop and prop["rich_text"]:
        return prop["rich_text"][0]["plain_text"]

    return ""


def get_title(prop):

    if prop["title"]:
        return prop["title"][0]["plain_text"]

    return ""


def load_menu():

    notion = Client(auth=NOTION_TOKEN)

    results = []
    cursor = None

    while True:

        res = notion.databases.query(
            database_id=DATABASE_ID,
            start_cursor=cursor
        )

        results.extend(res["results"])

        if not res["has_more"]:
            break

        cursor = res["next_cursor"]

    menus = defaultdict(list)

    for page in results:

        props = page["properties"]

        name = get_title(props["名前"])

        if not name:
            continue

        category = props["カテゴリ"]["select"]["name"]

        materials = get_text(props.get("材料", {}))
        recipe = get_text(props.get("レシピ", {}))

        menus[category].append({
            "name": name,
            "materials": materials,
            "recipe": recipe
        })

    return menus


# =====================
# selector（state対応）
# =====================

class Selector:

    def __init__(self, menus, state):

        self.menus = menus
        self.state = state

        for category in menus:

            if category not in self.state:
                self.state[category] = 0


    def next(self, category):

        index = self.state[category]

        menu = self.menus[category][index]

        self.state[category] = (index + 1) % len(self.menus[category])

        return menu


# =====================
# calendar
# =====================

def create_calendar(menus, state):

    selector = Selector(menus, state)

    cal = Calendar()

    current = START_DATE

    while current <= END_DATE:

        category = weekday_category[current.weekday()]

        menu = selector.next(category)

        event = Event()

        event.name = menu["name"]

        event.begin = current
        event.make_all_day()

        description = ""

        if menu["materials"]:
            description += "【材料】\n" + menu["materials"] + "\n\n"

        if menu["recipe"]:
            description += "【レシピ】\n" + menu["recipe"]

        event.description = description

        cal.events.add(event)

        current += timedelta(days=1)

    return cal


# =====================
# save
# =====================

def save_calendar(cal):

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.writelines(cal)


# =====================
# main
# =====================

def main():

    menus = load_menu()

    state = load_state()

    cal = create_calendar(menus, state)

    save_calendar(cal)

    save_state(state)

    print("完了")


if __name__ == "__main__":
    main()

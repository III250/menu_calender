import json
import os
import calendar as cal_module
from datetime import date, timedelta
from ics import Calendar, Event


MENU_FILE = "menu_data.json"
STATE_FILE = "menu_state.json"


# ----------------------
# データ読み込み
# ----------------------

def load_menu():
    with open(MENU_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_state():

    if not os.path.exists(STATE_FILE):
        return {
            "index": {},
            "last_week": [],
            "last_week_previous_month": []
        }

    with open(STATE_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_state(state):

    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ----------------------
# 次の献立取得（順番＋重複禁止）
# ----------------------

def get_next(menu_data, state, category):

    if category not in state["index"]:
        state["index"][category] = 0

    start = state["index"][category]

    size = len(menu_data[category])

    banned = set(state["last_week"]) | set(state["last_week_previous_month"])

    for i in range(size):

        idx = (start + i) % size

        item = menu_data[category][idx]

        if item["name"] not in banned:

            state["index"][category] = (idx + 1) % size

            return item

    return menu_data[category][start]


# ----------------------
# 献立生成
# ----------------------

def generate_sequence(menu_data, state, year, month):

    days = cal_module.monthrange(year, month)[1]

    sequence = []

    categories = list(menu_data.keys())

    for i in range(days):

        category = categories[i % len(categories)]

        item = get_next(menu_data, state, category)

        sequence.append(item)

    return sequence


# ----------------------
# ICS作成（終日イベント）
# ----------------------

def create_ics(sequence, year, month):

    calendar = Calendar()

    for i, menu in enumerate(sequence):

        d = date(year, month, 1) + timedelta(days=i)

        event = Event()

        event.name = menu["name"]

        # ⭐ 終日イベント設定
        event.begin = d
        event.make_all_day()

        desc = ""

        if menu.get("materials"):
            desc += "【材料】\n" + menu["materials"] + "\n\n"

        if menu.get("recipe"):
            desc += "【レシピ】\n" + menu["recipe"]

        event.description = desc

        calendar.events.add(event)

    filename = f"menu-{year}-{month:02d}.ics"

    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(calendar)

    return filename


# ----------------------
# state更新
# ----------------------

def update_state(state, sequence):

    names = [m["name"] for m in sequence]

    state["last_week_previous_month"] = state["last_week"]

    state["last_week"] = names[-7:]


# ----------------------
# メイン処理
# ----------------------

def main():

    today = date.today()

    year = today.year
    month = today.month

    menu_data = load_menu()

    state = load_state()

    sequence = generate_sequence(menu_data, state, year, month)

    filename = create_ics(sequence, year, month)

    update_state(state, sequence)

    save_state(state)

    print("created:", filename)


if __name__ == "__main__":
    main()

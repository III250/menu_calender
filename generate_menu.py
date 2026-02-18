import os
import random
import calendar
import requests
from datetime import datetime, timedelta, date

# ===============================
# Notion設定（GitHub Secrets）
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
# 次の月を取得
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
# Notionの献立マスターから取得
# （タイトルプロパティ名は "名前" 前提）
# ===============================

def get_menu_list_from_notion():
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
            title_prop = item["properties"]["名前"]["title"]
            if title_prop:
                menus.append(title_prop[0]["plain_text"])

        has_more = data["has_more"]
        next_cursor = data.get("next_cursor")

    if not menus:
        raise ValueError("献立マスターが空です")

    return menus

# ===============================
# 一巡方式 + 平日週2魚 + 魚連続禁止
# （魚判定 = メニュー名に「魚」を含む）
# ===============================

def generate_menu(menus, year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    start_date = date(year, month, 1)

    result = []
    pool = menus.copy()
    random.shuffle(pool)

    fish_count = 0

    for day_offset in range(days_in_month):
        current_date = start_date + timedelta(days=day_offset)
        weekday = current_date.weekday()  # 0=月, 4=金

        # 月曜なら魚カウントリセット
        if weekday == 0:
            fish_count = 0

        prev_is_fish = False
        if result:
            prev_is_fish = "魚" in result[-1]

        # 平日（月〜金）
        if weekday < 5:
            remaining_weekdays = 4 - weekday
            remaining_fish_needed = 2 - fish_count

            if remaining_fish_needed > remaining_weekdays:
                candidate_pool = [m for m in pool if "魚" in m]
            else:
                candidate_pool = pool
        else:
            candidate_pool = pool

        # 魚連続禁止
        if prev_is_fish:
            candidate_pool = [m for m in candidate_pool if "魚" not in m]

        # 候補が空なら一巡リセット
        if not candidate_pool:
            pool = menus.copy()
            random.shuffle(pool)
            candidate_pool = pool

            if prev_is_fish:
                candidate_pool = [m for m in candidate_pool if "魚" not in m]

        pick = random.choice(candidate_pool)
        pool.remove(pick)

        if "魚" in pick and weekday < 5:
            fish_count += 1

        result.append(pick)

        # 一巡したら再シャッフル
        if not pool:
            pool = menus.copy()
            random.shuffle(pool)

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

            f.write("BEGIN:VEVENT\n")
            f.write(f"UID:{year}{month:02d}{i}@menu\n")
            f.write(f"DTSTAMP:{date_str}T000000Z\n")
            f.write(f"DTSTART;VALUE=DATE:{date_str}\n")
            f.write(f"SUMMARY:{menu}\n")
            f.write("END:VEVENT\n")

        f.write("END:VCALENDAR\n")

    return filename

# ===============================
# メイン
# ===============================

def main():
    year, month = get_next_month()

    menus = get_menu_list_from_notion()

    if len(menus) < 2:
        raise ValueError("献立は2個以上必要です")

    sequence = generate_menu(menus, year, month)

    filename = create_ics(sequence, year, month)

    print(f"{filename} を生成しました")

if __name__ == "__main__":
    main()

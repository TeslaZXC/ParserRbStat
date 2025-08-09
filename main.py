import os
import json
import time

from missions_parser import parse_ocap_table, sanitize_filename
from stats_parser import fetch_and_update_stats

from stat_squad import process_file_with_team_stats, load_json_file
from aggregate_stats import aggregate_stats

PROCESSED_FILE = 'processed_missions.json'
MISSION_DETAILS_DIR = 'temp/mission-details'

def load_processed_missions():
    if os.path.exists(PROCESSED_FILE):
        with open(PROCESSED_FILE, encoding='utf-8') as f:
            return set(json.load(f))
    return set()

def save_processed_missions(processed_ids):
    with open(PROCESSED_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(processed_ids), f, ensure_ascii=False, indent=4)

def main_loop():
    os.makedirs(MISSION_DETAILS_DIR, exist_ok=True)
    team_tags = load_json_file('team.json')

    processed_ids = load_processed_missions()

    while True:
        print("Парсим список миссий...")
        missions = parse_ocap_table("http://stats.red-bear.ru/", limit=100)
        print(f"Найдено миссий: {len(missions)}")

        new_missions = [m for m in missions if m['id'] not in processed_ids]

        if not new_missions:
            print("Новых миссий нет. Ждём 1 минуту...")
        else:
            print(f"Новых миссий для парсинга: {len(new_missions)}")

            for mission in new_missions:
                try:
                    updated_mission = fetch_and_update_stats(mission)
                    filename = os.path.join(MISSION_DETAILS_DIR, f"{sanitize_filename(mission['mission_name'])}.json")
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(updated_mission, f, ensure_ascii=False, indent=4)
                    print(f"Сохранена миссия с деталями: {mission['mission_name']}")

                    process_file_with_team_stats(filename, team_tags)

                    processed_ids.add(mission['id'])
                except Exception as e:
                    print(f"Ошибка при обработке миссии {mission['mission_name']}: {e}")
            aggregate_stats()
            save_processed_missions(processed_ids)
            print("Общая статистика обновлена.")

        time.sleep(60)  

if __name__ == "__main__":
    main_loop()

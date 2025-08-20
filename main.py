import os
import json
import time
import traceback
from datetime import datetime

from missions_parser import parse_ocap_table, sanitize_filename
from stats_parser import fetch_and_update_stats
from stat_squad import process_file_with_team_stats, load_json_file
from aggregate_stats import aggregate_stats
from aggregate_all_stats import aggregate_all_missions
from config import *
from aggregate_top_season import aggregate_top

def log(msg):
    """Печать сообщения с текущим временем."""
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}")

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
    team_tags = load_json_file(TEAMP_DIR)

    processed_ids = load_processed_missions()

    while True:
        log("Парсим список миссий...")
        missions = parse_ocap_table("http://stats.red-bear.ru/")
        log(f"Найдено миссий: {len(missions)}")

        new_missions = [m for m in missions if m['id'] not in processed_ids]

        if not new_missions:
            log("Новых миссий нет.")
        else:
            log(f"Новых миссий для парсинга: {len(new_missions)}")

            for mission in new_missions:
                try:
                    updated_mission = fetch_and_update_stats(mission)
                    filename = os.path.join(MISSION_DETAILS_DIR, f"{sanitize_filename(mission['mission_name'])}.json")
                    with open(filename, 'w', encoding='utf-8') as f:
                        json.dump(updated_mission, f, ensure_ascii=False, indent=4)
                    log(f"Сохранена миссия с деталями: {mission['mission_name']}")

                    process_file_with_team_stats(filename, team_tags)

                    processed_ids.add(mission['id'])
                except Exception as e:
                    log(f"Ошибка при обработке миссии {mission['mission_name']}: {e}")
                    traceback.print_exc()

            save_processed_missions(processed_ids)

        try:
            log("Обновляем общую статистику...")
            aggregate_stats()
            aggregate_all_missions()
            # aggregate_top()
            log("Общая статистика обновлена.")
        except Exception as e:
            log(f"Ошибка при обновлении статистики: {e}")
            traceback.print_exc()

        time.sleep(60)

if __name__ == "__main__":
    while True:
        try:
            main_loop()
        except Exception as e:
            log(f"Критическая ошибка в скрипте: {e}")
            traceback.print_exc()
            log("Перезапуск через 10 секунд...")
            time.sleep(10)

import os
import json
import requests
from pathlib import Path
from time import sleep
from datetime import datetime

from logic.mission_pars import process_ocap 
from config import *

OCAPS_PATH.mkdir(exist_ok=True)
TEMP_PATH.mkdir(exist_ok=True)


def download_new_ocaps():
    response = requests.get(OCAPS_URL)
    response.raise_for_status()
    ocaps_list = response.json()

    min_date_dt = datetime.strptime(DOWNLOAD_DATE, "%Y-%m-%d")
    filtered_ocaps = [o for o in ocaps_list if datetime.strptime(o["date"], "%Y-%m-%d") >= min_date_dt]

    if not filtered_ocaps:
        print("Новых миссий не найдено.")
        return []

    filtered_ocaps.sort(key=lambda x: (x["date"], x["filename"]), reverse=True)

    local_files = set(os.listdir(OCAPS_PATH))
    downloaded_files = []

    for ocap in filtered_ocaps:
        filename = ocap["filename"]
        filepath = OCAPS_PATH / filename
        if filename not in local_files:
            print(f"Скачиваем: {filename}")
            r = requests.get(OCAP_URL % filename)
            r.raise_for_status()
            filepath.write_text(r.text, encoding="utf-8")
            sleep(1)
        else:
            print(f"Уже скачано: {filename}")
        downloaded_files.append(filepath)

    return downloaded_files

def main():
    new_ocaps = download_new_ocaps()
    if not new_ocaps:
        return
    for ocap_file in new_ocaps:
        print(f"Обрабатываем: {ocap_file.name}")
        process_ocap(ocap_file)

if __name__ == "__main__":
    main()

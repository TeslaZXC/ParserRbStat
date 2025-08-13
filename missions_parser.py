import os
import re
import urllib.parse
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from config import *

HEADERS = {'User-Agent': UserAgent().random}

def sanitize_filename(filename):
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def parse_ocap_table(url):
    response = requests.get(url, headers=HEADERS)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', id='ocap-list-table')
    if not table:
        print("Таблица не найдена")
        return []

    rows = table.tbody.find_all('tr')

    def extract_id(row):
        cols = row.find_all('td')
        try:
            return int(cols[0].text.strip())
        except:
            return -1  

    rows = sorted(rows, key=extract_id, reverse=True)

    days_ago = MONTHS * 30
    date_threshold = datetime.now() - timedelta(days=days_ago)

    missions = []

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 10:
            continue

        tags_text = ' '.join(col.text.strip().lower() for col in cols)
        if 'tvt' not in tags_text:
            continue

        mission_date = None
        date_str = None
        for col in cols:
            text = col.text.strip()
            for fmt in ("%d.%m.%Y", "%Y-%m-%d", "%d/%m/%Y"):
                try:
                    mission_date = datetime.strptime(text, fmt)
                    date_str = text
                    break
                except ValueError:
                    continue
            if mission_date:
                break

        if not mission_date or mission_date < date_threshold:
            continue

        id_ = cols[0].text.strip()
        mission_name = cols[1].a.text.strip() if cols[1].a else cols[1].text.strip()
        ocap_link = cols[2].a['href'].strip() if cols[2].a else ""
        players = cols[3].text.strip()
        frags = cols[4].div.text.strip() if cols[4].div else cols[4].text.strip()
        tk = cols[6].div.text.strip() if cols[6].div else cols[6].text.strip()
        map_ = cols[7].text.strip()
        duration = cols[8].text.strip()

        if ocap_link.startswith('/'):
            ocap_link = 'https://ocap.red-bear.ru' + ocap_link

        parsed = urllib.parse.urlparse(ocap_link)
        query = urllib.parse.parse_qs(parsed.query)
        filename = query.get('file', [None])[0]
        stats_url = None
        if filename:
            stats_url = f"http://stats.red-bear.ru/?filename={filename}"

        missions.append({
            "id": id_,
            "mission_name": mission_name,
            "ocap_link": ocap_link,
            "stats_url": stats_url,
            "players": players,
            "frags": frags,
            "tk": tk,
            "map": map_,
            "duration": duration,
            "date": date_str,
            "tag_check": "tvt"
        })

    return missions

def main():
    os.makedirs('temp/missions', exist_ok=True)
    
    missions = parse_ocap_table(URL)  
    total = len(missions)
    print(f"Найдено {total} миссий для парсинга.\n")

    import json
    for idx, m in enumerate(missions, start=1):
        filename = f"temp/missions/{sanitize_filename(m['mission_name'])}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(m, f, ensure_ascii=False, indent=4)

        remaining = total - idx
        print(f"Сохранена миссия {m['mission_name']} ({idx}/{total}, осталось {remaining})")

if __name__ == "__main__":
    main()
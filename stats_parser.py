import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/115.0 Safari/537.36'
}

def parse_victims_table(victims_table, mission_id=None, mission_date=None):
    """Парсинг таблицы жертв/смертей."""
    victims = []
    death_info = None
    rows = victims_table.find_all('tr')

    in_death_section = False

    for row in rows:
        cols = row.find_all('td')

        # Разделы "Kills" и "Death"
        if len(cols) == 1 and cols[0].has_attr('colspan'):
            section_name = cols[0].text.strip().lower()
            if section_name == 'kills':
                in_death_section = False
            elif section_name == 'death':
                in_death_section = True
            continue

        # Запись события
        if len(cols) == 5:
            kill_type = cols[0].text.strip()
            time_ = cols[1].text.strip()
            victim_link = cols[2].find('a')
            victim_name = victim_link.text.strip() if victim_link else cols[2].text.strip()
            distance = cols[3].text.strip()
            weapon = cols[4].text.strip()

            entry = {
                "kill_type": kill_type,
                "time": time_,
                "victim_name": victim_name,
                "distance": distance,
                "weapon": weapon,
                "mission_id": mission_id,
                "mission_date": mission_date  # добавили дату миссии
            }

            if in_death_section:
                death_info = entry
            else:
                victims.append(entry)

    return victims, death_info


def parse_stats_table(soup, mission_id=None, mission_date=None):
    """Парсинг общей таблицы статистики игроков."""
    table = soup.find('table', id='stats-table')
    if not table:
        print("Таблица с id='stats-table' не найдена")
        return []

    players_data = []
    tbody = table.find('tbody')
    rows = tbody.find_all('tr')

    for row in rows:
        cols = row.find_all('td')
        if len(cols) < 8:
            continue

        player_link = cols[0].find('a')
        player_name = player_link.text.strip() if player_link else cols[0].text.strip()
        frags = int(cols[1].text.strip())
        side = cols[2].text.strip()
        group = cols[3].text.strip()
        teamkills = int(cols[4].text.strip())
        vehicle_kills = int(cols[5].text.strip())
        ai_kills = int(cols[6].text.strip())

        victims = []
        death = None
        victim_div = cols[7].find('div', class_='collapse')
        if victim_div:
            victims_table = victim_div.find('table')
            if victims_table:
                victims, death = parse_victims_table(
                    victims_table, 
                    mission_id=mission_id, 
                    mission_date=mission_date
                )

        player_data = {
            "player_name": player_name,
            "frags": frags,
            "side": side,
            "group": group,
            "teamkills": teamkills,
            "vehicle_kills": vehicle_kills,
            "ai_kills": ai_kills,
            "victims": victims,
            "death": death
        }
        players_data.append(player_data)

    return players_data


def fetch_and_update_stats(mission):
    """Получение и обновление статистики миссии."""
    stats_url = mission.get('stats_url')
    if not stats_url:
        print(f"Нет ссылки на статистику для миссии {mission['mission_name']}")
        return mission

    response = requests.get(stats_url, headers=HEADERS)
    if response.status_code != 200:
        print(f"Ошибка загрузки статистики: {response.status_code} "
              f"для миссии {mission['mission_name']}")
        return mission

    soup = BeautifulSoup(response.text, 'html.parser')
    players_stats = parse_stats_table(
        soup,
        mission_id=mission['id'],
        mission_date=mission.get('date')  # передаём дату миссии
    )
    mission['players_stats'] = players_stats
    return mission


def filter_missions_last_2_months(missions):
    """Фильтрация миссий за последние 2 месяца."""
    two_months_ago = datetime.now() - timedelta(days=60)
    filtered = []

    for mission in missions:
        date_str = mission.get('date')
        if not date_str:
            continue
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            continue

        if date >= two_months_ago:
            filtered.append(mission)

    return filtered

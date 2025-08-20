import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/115.0 Safari/537.36'
}

def parse_victims_table(victims_table, mission_id=None, mission_date=None):
    """Парсинг таблицы 'Kills/Death' с учетом техники и шлемов, пропуская убийства ИИ (серые строки)."""
    victims = []
    death_info = None
    frag_inf_count = 0
    frag_veh_count = 0
    destroyed_vehicles_count = 0

    rows = victims_table.find_all('tr')
    in_death_section = False

    for row in rows:
        if 'style' in row.attrs and 'color:grey' in row['style']:
            continue

        cols = row.find_all('td')

        if len(cols) == 1 and cols[0].has_attr('colspan'):
            section_name = cols[0].text.strip().lower()
            if section_name == 'kills':
                in_death_section = False
            elif section_name == 'death':
                in_death_section = True
            continue

        if len(cols) != 5:
            continue

        kill_type = cols[0].text.strip()
        time_ = cols[1].text.strip()

        victim_td = cols[2]
        victim_link = victim_td.find('a')
        victim_name = victim_link.text.strip() if victim_link else victim_td.text.strip()

        victim_img = victim_td.find('img')
        has_vehicle_target = False
        if victim_img and 'helmet_grey.png' not in victim_img['src']:
            has_vehicle_target = True

        distance = cols[3].text.strip()

        weapon_td = cols[4]
        weapon = weapon_td.text.strip()
        weapon_img = weapon_td.find('img')
        has_vehicle_weapon = False
        if weapon_img and 'helmet_grey.png' not in weapon_img['src']:
            has_vehicle_weapon = True

        if in_death_section:
            death_info = {
                "kill_type": kill_type,
                "time": time_,
                "victim_name": victim_name,
                "distance": distance,
                "weapon": weapon,
                "frag_type": "death",
                "mission_id": mission_id,
                "mission_date": mission_date
            }
            continue

        if kill_type.upper() == 'TK':
            entry = {
                "kill_type": kill_type,
                "time": time_,
                "victim_name": victim_name,
                "distance": distance,
                "weapon": weapon,
                "frag_type": "teamkill",
                "mission_id": mission_id,
                "mission_date": mission_date
            }
            victims.append(entry)
            continue

        if has_vehicle_target:
            destroyed_vehicles_count += 1
            frag_type = 'vehicle_destroyed'
            entry = {
                "kill_type": kill_type,
                "time": time_,
                "victim_name": victim_name,
                "distance": distance,
                "weapon": weapon,
                "frag_type": frag_type,
                "mission_id": mission_id,
                "mission_date": mission_date
            }
            victims.append(entry)
            continue

        if has_vehicle_weapon:
            frag_veh_count += 1
            frag_type = 'vehicle_kill'
        else:
            frag_inf_count += 1
            frag_type = 'infantry'

        entry = {
            "kill_type": kill_type,
            "time": time_,
            "victim_name": victim_name,
            "distance": distance,
            "weapon": weapon,
            "frag_type": frag_type,
            "mission_id": mission_id,
            "mission_date": mission_date
        }
        victims.append(entry)

    return victims, death_info, frag_inf_count, frag_veh_count, destroyed_vehicles_count


def parse_stats_table(soup, mission_id=None, mission_date=None):
    """Парсинг общей таблицы статистики игроков с разделением фрагов."""
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
        side = cols[2].text.strip()
        group = cols[3].text.strip()
        teamkills = int(cols[4].text.strip())
        vehicle_kills = int(cols[5].text.strip())
        ai_kills = int(cols[6].text.strip())

        victims = []
        death = None
        frag_inf_count = 0
        frag_veh_count = 0
        destroyed_vehicles_count = 0

        victim_div = cols[7].find('div', class_='collapse')
        if victim_div:
            victims_table = victim_div.find('table')
            if victims_table:
                victims, death, frag_inf_count, frag_veh_count, destroyed_vehicles_count = parse_victims_table(
                    victims_table,
                    mission_id=mission_id,
                    mission_date=mission_date
                )

        player_data = {
            "player_name": player_name,
            "frags": frag_inf_count + frag_veh_count - teamkills,
            "frag_inf": frag_inf_count,
            "frag_veh": frag_veh_count,
            "destroyed_vehicles": destroyed_vehicles_count,
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
        mission_date=mission.get('date')
    )
    mission['players_stats'] = players_stats
    return mission


def filter_missions_by_days(missions, days_back=60):
    """Фильтрация миссий за последние N дней."""
    date_threshold = datetime.now() - timedelta(days=days_back)
    filtered = []

    for mission in missions:
        date_str = mission.get('date')
        if not date_str:
            continue
        try:
            date = datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            continue

        if date >= date_threshold:
            filtered.append(mission)

    return filtered

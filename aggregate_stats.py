import os
import json
import re
from datetime import datetime, timedelta

MISSION_DETAILS_DIR = "temp/mission-details"

SEASON_START_DATE = datetime(2025, 5, 1)  # 1 августа 2025 года

def add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, [31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31,30,31,30,31,31,30,31,30,31][month-1])
    return datetime(year, month, day)

def get_season_ranges(start_date, end_date):
    seasons = []
    current_start = start_date
    while current_start < end_date:
        current_end = add_months(current_start, 1)
        if current_end > end_date:
            current_end = end_date
        seasons.append((current_start, current_end))
        current_start = current_end
    return seasons

def format_nick(name: str) -> str:
    name = re.sub(r'\[([^\]]+)\]', lambda m: f"[{m.group(1).upper()}]", name)
    if name.startswith("Dw."):
        name = "DW." + name[3:]
    return name

def format_team(name: str) -> str:
    return name.upper()

def aggregate_stats_for_period(start_date: datetime, end_date: datetime):
    print(f"Агрегация статистики за период: {start_date.date()} - {end_date.date()}")

    player_stats = {}
    team_stats = {}

    def add_counts(dest, source):
        for key in ['frags', 'teamkills', 'deaths']:
            dest[key] = dest.get(key, 0) + source.get(key, 0)
        if 'side' in source:
            dest['side'] = source['side']

    for filename in os.listdir(MISSION_DETAILS_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(MISSION_DETAILS_DIR, filename)
        with open(filepath, encoding='utf-8') as f:
            data = json.load(f)

        mission_date_str = data.get('date')
        if not mission_date_str:
            continue

        try:
            mission_date = datetime.strptime(mission_date_str, "%Y-%m-%d")
        except ValueError:
            try:
                mission_date = datetime.strptime(mission_date_str, "%d.%m.%Y")
            except ValueError:
                continue

        if not (start_date <= mission_date < end_date):
            continue

        for player in data.get('players_stats', []):
            pname = format_nick(player['player_name'])
            group_name = format_team(player.get('group', 'unknown'))

            if pname not in player_stats:
                player_stats[pname] = {
                    'frags': 0,
                    'teamkills': 0,
                    'deaths_count': 0,
                    'side': player.get('side', 'unknown'),
                    'group': group_name,
                    'victims': [],
                    'deaths': []
                }

            player_stats[pname]['frags'] += player.get('frags', 0)
            player_stats[pname]['teamkills'] += player.get('teamkills', 0)

            if player.get('death'):
                death = player['death']
                death['victim_name'] = format_nick(death['victim_name'])
                player_stats[pname]['deaths_count'] += 1
                player_stats[pname]['deaths'].append(death)

            if 'victims' in player:
                for v in player['victims']:
                    v['victim_name'] = format_nick(v['victim_name'])
                player_stats[pname]['victims'].extend(player['victims'])

        teams_data = data.get('team_stats', {})
        for team_name, team_info in teams_data.items():
            formatted_team_name = format_team(team_name)
            if formatted_team_name not in team_stats:
                team_stats[formatted_team_name] = {
                    'frags': 0,
                    'teamkills': 0,
                    'deaths': 0,
                    'side': team_info.get('side', 'unknown')
                }
            add_counts(team_stats[formatted_team_name], team_info)

    summary = {
        'players': player_stats,
        'teams': team_stats,
        'season_start': start_date.strftime("%Y-%m-%d"),
        'season_end': end_date.strftime("%Y-%m-%d")
    }

    summary['players'] = {format_nick(name): stats for name, stats in summary['players'].items()}

    os.makedirs('temp', exist_ok=True)
    output_filename = f"temp/stats_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.json"

    with open(output_filename, 'w', encoding='utf-8') as f_out:
        json.dump(summary, f_out, indent=4, ensure_ascii=False)

    print(f"Сезонная статистика сохранена в {output_filename}")

def aggregate_stats():
    today = datetime.now()
    seasons = get_season_ranges(SEASON_START_DATE, today)
    for start, end in seasons:
        aggregate_stats_for_period(start, end)

if __name__ == '__main__':
    aggregate_stats()

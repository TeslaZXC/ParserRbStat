import os
import json
import re
from datetime import datetime
from config import *

def format_nick(name: str) -> str:
    name = re.sub(r'\[([^\]]+)\]', lambda m: f"[{m.group(1).upper()}]", name)
    if name.startswith("Dw."):
        name = "DW." + name[3:]
    return name

def format_team(name: str) -> str:
    return name.upper()

def aggregate_all_missions():
    print("Собираем общую статистику по всем миссиям...")

    player_stats = {}
    team_stats = {}
    total_missions = 0

    def add_counts(dest, source):
        for key in ['frags', 'teamkills', 'deaths', 'total_players']:
            dest[key] = dest.get(key, 0) + source.get(key, 0)

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

        total_missions += 1
        players_in_this_mission = set()

        for player in data.get('players_stats', []):
            pname = format_nick(player['player_name'])
            team_name = format_team(player.get('group', 'UNKNOWN'))

            if pname not in player_stats:
                player_stats[pname] = {
                    'frags': 0,
                    'frag_inf': 0,
                    'frag_veh': 0,
                    'destroyed_vehicles': 0,
                    'teamkills': 0,
                    'deaths_count': 0,
                    'victims': [],
                    'deaths': [],
                    'missions_played': 0
                }

            if pname not in players_in_this_mission:
                player_stats[pname]['missions_played'] += 1
                players_in_this_mission.add(pname)

            player_stats[pname]['frag_inf'] += player.get('frag_inf', 0)
            player_stats[pname]['frag_veh'] += player.get('frag_veh', 0)
            player_stats[pname]['destroyed_vehicles'] += player.get('destroyed_vehicles', 0)
            player_stats[pname]['frags'] = (
                player_stats[pname]['frag_inf'] +
                player_stats[pname]['frag_veh'] +
                player_stats[pname]['destroyed_vehicles']
            )
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

        teams_in_this_mission = set()
        for team_name, team_info in data.get('team_stats', {}).items():
            formatted_team_name = format_team(team_name)
            if formatted_team_name not in team_stats:
                team_stats[formatted_team_name] = {
                    'frags': 0,
                    'teamkills': 0,
                    'deaths': 0,
                    'missions_played': 0,
                    'total_players': 0,
                    'score': 0.0,
                    'missions': []  
                }

            if formatted_team_name not in teams_in_this_mission:
                team_stats[formatted_team_name]['missions_played'] += 1
                teams_in_this_mission.add(formatted_team_name)

                mission_info = {
                    'id': data.get('id'),
                    'mission_name': data.get('mission_name'),
                    'map': data.get('map'),
                    'date': data.get('date'),
                    'frags': team_info.get('frags', 0),
                    'deaths': team_info.get('deaths', 0),
                    'teamkills': team_info.get('teamkills', 0)
                }
                team_stats[formatted_team_name]['missions'].append(mission_info)

            team_info['total_players'] = team_info.get('total_players', 0)
            add_counts(team_stats[formatted_team_name], team_info)

    for tname, tstats in team_stats.items():
        if tstats['total_players'] > 0:
            tstats['score'] = tstats['frags'] / tstats['total_players']
        else:
            tstats['score'] = 0.0

    summary = {
        'players': {format_nick(name): stats for name, stats in player_stats.items()},
        'teams': team_stats,
        'total_missions': total_missions,
        'date_generated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    os.makedirs('temp', exist_ok=True)
    output_filename = "temp/all_stats.json"
    with open(output_filename, 'w', encoding='utf-8') as f_out:
        json.dump(summary, f_out, indent=4, ensure_ascii=False)

    print(f"Общая статистика сохранена: {output_filename} — всего игроков: {len(player_stats)}, отрядов: {len(team_stats)}, миссий: {total_missions}")

if __name__ == '__main__':
    aggregate_all_missions()
import os
import json
from collections import defaultdict

MISSION_DETAILS_DIR = "temp/mission-details"
OUTPUT_FILE = "temp/stats.json"

def aggregate_stats():
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

        for player in data.get('players_stats', []):
            pname = player['player_name']

            if pname not in player_stats:
                player_stats[pname] = {
                    'frags': 0,
                    'teamkills': 0,
                    'deaths_count': 0,
                    'side': player.get('side', 'unknown'),
                    'group': player.get('group', 'unknown'),
                    'victims': [],
                    'deaths': []
                }
            player_stats[pname]['frags'] += player.get('frags', 0)
            player_stats[pname]['teamkills'] += player.get('teamkills', 0)

            if player.get('death'):
                player_stats[pname]['deaths_count'] += 1
                player_stats[pname]['deaths'].append(player['death'])

            if 'victims' in player:
                player_stats[pname]['victims'].extend(player['victims'])

        if 'team_stats' in data:
            teams_data = data['team_stats']
        elif 'team_stats' in data:
            teams_data = data['team_stats']
        else:
            teams_data = {}

        for team_name, team_info in teams_data.items():
            if team_name not in team_stats:
                team_stats[team_name] = {
                    'frags': 0,
                    'teamkills': 0,
                    'deaths': 0,
                    'side': team_info.get('side', 'unknown')
                }
            add_counts(team_stats[team_name], team_info)

    summary = {
        'players': player_stats,
        'teams': team_stats
    }
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f_out:
        json.dump(summary, f_out, indent=4, ensure_ascii=False)

    print(f"Собранная статистика сохранена в {OUTPUT_FILE}")

if __name__ == '__main__':
    aggregate_stats()

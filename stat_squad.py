import json
import os
import re

def load_json_file(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)

def save_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_team_tag(player_name, team_tags):
    match = re.search(r'\[([^\]]+)\]', player_name)
    if match:
        tag = match.group(1)
        if tag in team_tags:
            return tag
    match = re.match(r'(\w+)\.', player_name, re.IGNORECASE)
    if match:
        prefix = match.group(1)
        for team_tag in team_tags:
            if team_tag.lower() == prefix.lower():
                return team_tag
    return None

def aggregate_stats_from_players(players_stats, team_tags):
    team_stats = {}
    for p in players_stats:
        tag = extract_team_tag(p.get('player_name', ''), team_tags)
        if not tag:
            continue

        if tag not in team_stats:
            team_stats[tag] = {
                "frags": 0,
                "teamkills": 0,
                "deaths": 0,
                "side": None
            }
        team_stats[tag]["frags"] += p.get("frags", 0)
        team_stats[tag]["teamkills"] += p.get("teamkills", 0)
        if team_stats[tag]["side"] is None and p.get("side"):
            team_stats[tag]["side"] = p.get("side")
        if p.get("death") is not None:
            team_stats[tag]["deaths"] += 1
    return team_stats

def process_file_with_team_stats(filepath, team_tags):
    data = load_json_file(filepath)
    players_stats = data.get('players_stats', [])
    team_stats = aggregate_stats_from_players(players_stats, team_tags)
    data['team_stats'] = team_stats
    save_json_file(filepath, data)
    print(f"Добавлена статистика отрядов в файл {os.path.basename(filepath)}")


if __name__ == "__main__":
    team_tags = load_json_file('team.json')
    folder = 'temp/mission-details'
    for filename in os.listdir(folder):
        if filename.endswith('.json'):
            process_file_with_team_stats(os.path.join(folder, filename), team_tags)

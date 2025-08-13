import json
import os
import re
from config import *

def load_json_file(filename):
    with open(filename, encoding='utf-8') as f:
        return json.load(f)

def save_json_file(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def extract_team_tag(player_name, team_tags):
    """
    Извлекает тег игрока по формату [TAG] или TAG.PlayerName.
    Сравнивает с team_tags без учёта регистра и лишних пробелов.
    """
    player_name = player_name.strip()

    match = re.search(r'\[\s*([^\]]+?)\s*\]', player_name)
    if match:
        tag = match.group(1).strip()
        for t in team_tags:
            if tag.lower() == t.lower():
                return t

    match = re.match(r'(\w+)\.', player_name)
    if match:
        prefix = match.group(1).strip()
        for t in team_tags:
            if prefix.lower() == t.lower():
                return t

    for t in team_tags:
        if player_name.lower().startswith(t.lower()):
            return t

    return None

def aggregate_stats_from_players(players_stats, allowed_tags_lower):
    team_stats = {}
    team_players = {} 
    skipped_players = []

    for p in players_stats:
        player_name = p.get('player_name', '')
        tag = extract_team_tag(player_name, allowed_tags_lower)
        
        if not tag:
            skipped_players.append(player_name)
            continue

        if tag not in team_stats:
            team_stats[tag] = {
                "frags": 0,
                "teamkills": 0,
                "deaths": 0,
                "side": None,
                "total_players": 0
            }
            team_players[tag] = set()

        team_players[tag].add(player_name)

        team_stats[tag]["frags"] += p.get("frags", 0)
        team_stats[tag]["teamkills"] += p.get("teamkills", 0)

        if team_stats[tag]["side"] is None and p.get("side"):
            team_stats[tag]["side"] = p.get("side")

        if bool(p.get("death")):
            team_stats[tag]["deaths"] += 1

    for tag in team_stats:
        team_stats[tag]["total_players"] = len(team_players[tag])

    return team_stats, skipped_players

def process_file_with_team_stats(filepath, allowed_tags_lower):
    data = load_json_file(filepath)
    players_stats = data.get('players_stats', [])
    team_stats, skipped_players = aggregate_stats_from_players(players_stats, allowed_tags_lower)

    if not team_stats:
        print(f"[WARNING] В файле {os.path.basename(filepath)} team_stats пустой!")
        if skipped_players:
            print("Причина: Ни один игрок не принадлежит к отрядам из TEAM_DIR.")
            print("Игроки, которые были пропущены:")
            for name in skipped_players:
                print(f"  - {name}")
        else:
            print("Причина: В players_stats вообще нет игроков.")

    data['team_stats'] = team_stats
    save_json_file(filepath, data)
    print(f"Обработан файл: {os.path.basename(filepath)}")

if __name__ == "__main__":
    team_tags = load_json_file(TEAMP_DIR)
    allowed_tags_lower = {t.strip().lower() for t in team_tags}

    for filename in os.listdir(MISSION_DETAILS_DIR):
        if filename.endswith('.json'):
            process_file_with_team_stats(os.path.join(MISSION_DETAILS_DIR, filename), allowed_tags_lower)

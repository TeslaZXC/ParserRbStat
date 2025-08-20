import os
import json
import re
from datetime import datetime
from config import *

def add_months(dt, months):
    month = dt.month - 1 + months
    year = dt.year + month // 12
    month = month % 12 + 1
    day = min(dt.day, [
        31,
        29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
        31, 30, 31, 30, 31, 31, 30, 31, 30, 31
    ][month - 1])
    return datetime(year, month, day)

def get_season_ranges(start_date, end_date, months_per_season):
    seasons = []
    current_start = start_date
    while current_start < end_date:
        current_end = add_months(current_start, months_per_season)
        if current_end > end_date:
            current_end = end_date
        seasons.append((current_start, current_end))
        current_start = current_end
    return seasons

def format_nick(name: str) -> str:
    if not name:
        return name
    name = re.sub(r'\[([^\]]+)\]', lambda m: f"[{m.group(1).upper()}]", name)
    if name.startswith("Dw."):
        name = "DW." + name[3:]
    return name

def format_team(name: str) -> str:
    return name.upper() if name else "UNKNOWN"

def has_tag(nick: str) -> bool:
    """Проверка, что ник содержит клан-тег ([TAG] или Dw.)"""
    if not nick:
        return False
    return bool(re.match(r"^\[[A-Za-z0-9]+\]", nick)) or nick.startswith("DW.")

def clean_player_stats(stats: dict) -> dict:
    """Удаляем лишние поля (victims, deaths)"""
    return {k: v for k, v in stats.items() if k not in ("victims", "deaths")}

def aggregate_stats_for_period(start_date: datetime, end_date: datetime):
    print(f"Сезон: {start_date.date()} - {end_date.date()}")

    player_stats = {}
    team_stats = {}

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

        if not (start_date <= mission_date < end_date):
            continue

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
                    'score': 0.0
                }

            if formatted_team_name not in teams_in_this_mission:
                team_stats[formatted_team_name]['missions_played'] += 1
                teams_in_this_mission.add(formatted_team_name)

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
        'season_start': start_date.strftime("%Y-%m-%d"),
        'season_end': end_date.strftime("%Y-%m-%d")
    }

    os.makedirs('temp', exist_ok=True)
    output_filename = f"temp/stats_{start_date.strftime('%Y-%m-%d')}_{end_date.strftime('%Y-%m-%d')}.json"
    with open(output_filename, 'w', encoding='utf-8') as f_out:
        json.dump(summary, f_out, indent=4, ensure_ascii=False)

    print(f"Сезон сохранён: {output_filename} — всего игроков: {len(player_stats)}")
    return summary

def get_season_tops(season_data: dict):
    players = season_data['players']
    teams = season_data['teams']

    def safe_div(x, y):
        return x / y if y > 0 else 0

    def valid_players():
        """Отфильтрованные игроки по условиям"""
        return {
            pname: pdata for pname, pdata in players.items()
            if pdata['missions_played'] > 5 and has_tag(pname)
        }

    tops = {}

    def player_entry(name, value, details):
        return {"name": name, "value": value, "details": clean_player_stats(details)}

    vp = valid_players()
    if not vp:
        return tops  

    best_overall = max(vp.items(), key=lambda kv: safe_div(kv[1]['frags'], kv[1]['missions_played']))
    pname, pdata = best_overall
    tops['best_overall'] = player_entry(pname, round(safe_div(pdata['frags'], pdata['missions_played']), 2), pdata)

    best_vehicle = max(vp.items(), key=lambda kv: safe_div(kv[1]['frag_veh'], kv[1]['missions_played']))
    pname, pdata = best_vehicle
    tops['best_vehicle'] = player_entry(pname, round(safe_div(pdata['frag_veh'], pdata['missions_played']), 2), pdata)

    best_infantry = max(vp.items(), key=lambda kv: safe_div(kv[1]['frag_inf'], kv[1]['missions_played']))
    pname, pdata = best_infantry
    tops['best_infantry'] = player_entry(pname, round(safe_div(pdata['frag_inf'], pdata['missions_played']), 2), pdata)

    best_destroyer = max(vp.items(), key=lambda kv: kv[1]['destroyed_vehicles'])
    pname, pdata = best_destroyer
    tops['best_destroyer'] = player_entry(pname, pdata['destroyed_vehicles'], pdata)

    teamkiller = max(vp.items(), key=lambda kv: kv[1]['teamkills'])
    pname, pdata = teamkiller
    tops['teamkiller'] = player_entry(pname, pdata['teamkills'], pdata)

    sniper = None
    sniper_dist = 0
    sniper_details = None
    for pname, stats in vp.items():
        for v in stats['victims']:
            if v.get('frag_type') == "infantry":
                try:
                    dist = int(v['distance'].replace("m", ""))
                except:
                    continue
                if dist > sniper_dist:
                    sniper_dist = dist
                    sniper = pname
                    sniper_details = v
    if sniper:
        tops['best_sniper'] = {"name": sniper, "value": sniper_dist, "details": sniper_details}

    veh_sniper = None
    veh_dist = 0
    veh_details = None
    for pname, stats in vp.items():
        for v in stats['victims']:
            if v.get('frag_type') == "vehicle_kill":
                try:
                    dist = int(v['distance'].replace("m", ""))
                except:
                    continue
                if dist > veh_dist:
                    veh_dist = dist
                    veh_sniper = pname
                    veh_details = v
    if veh_sniper:
        tops['best_vehicle_distance'] = {"name": veh_sniper, "value": veh_dist, "details": veh_details}

    if teams:
        best_team = max(teams.items(), key=lambda kv: kv[1]['score'])
        tname, tdata = best_team
        tops['best_team'] = {"name": tname, "value": round(tdata['score'], 2), "details": tdata}

        teamkill_team = max(teams.items(), key=lambda kv: kv[1]['teamkills'])
        tname, tdata = teamkill_team
        tops['teamkill_team'] = {"name": tname, "value": tdata['teamkills'], "details": tdata}

    return tops

def aggregate_top():
    today = datetime.now()

    if os.path.exists("temp"):
        for fname in os.listdir("temp"):
            if fname.startswith("stats_") or fname == "tops.json":
                os.remove(os.path.join("temp", fname))

    seasons = get_season_ranges(SEASON_START_DATE, today, SEASON_LENGTH_MONTHS)
    last_season_summary = None
    for start, end in seasons:
        last_season_summary = aggregate_stats_for_period(start, end)

    if last_season_summary:
        tops = get_season_tops(last_season_summary)
        with open("temp/tops.json", "w", encoding="utf-8") as f:
            json.dump(tops, f, indent=4, ensure_ascii=False)
        print("Топы сезона сохранены: temp/tops.json")

if __name__ == '__main__':
    aggregate_top()
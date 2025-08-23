import os
import json
import shutil
from pathlib import Path
from pymongo import MongoClient

from module.ocap_models import OCAP
from logic.name_logic import extract_name_and_squad
from config import *

OCAPS_PATH.mkdir(exist_ok=True)
TEMP_PATH.mkdir(exist_ok=True)

def load_squads() -> dict:
    if SQUAD_FILE.exists():
        with SQUAD_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def process_ocap(ocap_file: Path):
    if collection.find_one({"file": ocap_file.name}):
        print(f"Файл {ocap_file.name} уже обработан, пропускаю.")
        return

    with ocap_file.open("r", encoding="utf-8") as f:
        raw_data = json.load(f)

    squads_data = load_squads()
    ocap = OCAP.from_file(ocap_file)

    players_stats: dict[int, dict] = {}
    for p in ocap.players.values():
        clean_name, squad = extract_name_and_squad(p.name)
        players_stats[p.id] = {
            "id": p.id,
            "name": clean_name,
            "side": p.side,
            "squad": squad or None,
            "frags": 0,
            "frags_veh": 0,
            "frags_inf": 0,
            "tk": 0,
            "death": 0,
            "victims_players": [],
            "destroyed_vehicles": [],
            "destroyed_veh": 0
        }

    for e in ocap.events:
        killed = getattr(e, "killed", None)
        killer = getattr(e, "killer", None)
        killer_vehicle = getattr(e, "killer_vehicle", None)
        if not killer or killer.id not in players_stats or not killed:
            continue

        killer_stats = players_stats[killer.id]
        weapon_name = killer_vehicle.name if killer_vehicle else getattr(e, "weapon", "unknown")
        distance = getattr(e, "distance", 0)
        is_killed_vehicle = hasattr(killed, "vehicle_type") and getattr(killed, "vehicle_type") is not None

        if is_killed_vehicle:
            kill_type = "veh"
            killer_stats["destroyed_veh"] += 1
            killer_stats["destroyed_vehicles"].append({
                "name": getattr(killed, "name", "unknown"),
                "veh_type": str(getattr(killed, "vehicle_type", "unknown")),
                "weapon": weapon_name,
                "distance": distance,
                "kill_type": kill_type
            })
        else:
            same_side = hasattr(killed, "side") and killer.side == getattr(killed, "side", None)
            if same_side:
                kill_type = "tk"
                killer_stats["tk"] += 1
            else:
                if killer_vehicle:
                    kill_type = "veh"  
                    killer_stats["frags_veh"] += 1
                else:
                    kill_type = "kill"
                    killer_stats["frags_inf"] += 1

            killer_stats["victims_players"].append({
                "name": getattr(killed, "name", "unknown"),
                "weapon": weapon_name,
                "distance": distance,
                "killer_name": killer_stats["name"],
                "kill_type": kill_type
            })

        if not is_killed_vehicle and hasattr(killed, "id") and killed.id in players_stats:
            players_stats[killed.id]["death"] += 1

    for stats in players_stats.values():
        stats["frags"] = stats["frags_inf"] + stats["frags_veh"] - stats["tk"]

    win_side = None
    for event in raw_data.get("events", []):
        if isinstance(event, list) and len(event) >= 2 and event[1] == "endMission":
            win_side = event[2][0] if len(event) > 2 and isinstance(event[2], list) else None
            break

    mission_name = raw_data.get("missionName", "Unknown Mission")
    world_name = raw_data.get("worldName", "Unknown World")

    file_date = None
    if "__" in ocap_file.stem:
        file_date = ocap_file.stem.split("__")[0]
    else:
        file_date = "_".join(ocap_file.stem.split("_")[0:3])

    squads_stats: dict[str, dict] = {}
    for player in players_stats.values():
        squad_tag = player["squad"]
        if not squad_tag or squad_tag not in squads_data:
            continue

        if squad_tag not in squads_stats:
            squads_stats[squad_tag] = {
                "squad_tag": squad_tag,
                "side": player["side"],
                "frags": 0,
                "death": 0,
                "tk": 0,
                "victims_players": [],
                "squad_players": []
            }

        s = squads_stats[squad_tag]
        s["frags"] += player["frags"]
        s["death"] += player["death"]
        s["tk"] += player["tk"]

        for v in player["victims_players"]:
            s["victims_players"].append({
                "name": v["name"],
                "weapon": v["weapon"],
                "distance": v["distance"],
                "killer_name": v["killer_name"],
                "kill_type": v["kill_type"]
            })
        s["squad_players"].append({
            "name": player["name"],
            "frags": player["frags"],
            "tk": player["tk"]
        })

    data = {
        "file": ocap_file.name,
        "file_date": file_date,
        "game_type": ocap.game_type,
        "duration_frames": ocap.max_frame,
        "missionName": mission_name,
        "worldName": world_name,
        "win_side": win_side,
        "players": list(players_stats.values()),
        "squads": list(squads_stats.values())
    }

    collection.insert_one(data)

    for item in TEMP_PATH.iterdir():
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            shutil.rmtree(item)

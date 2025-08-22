import re

def extract_name_and_squad(nickname: str) -> tuple[str, str]:
    match = re.search(r"\[(.*?)\]", nickname)
    if match:
        squad = match.group(1).upper()
    else:
        squad = ""

        if "." in nickname:
            squad = nickname.split(".")[0].strip().upper()
        else:
            parts = nickname.split()
            if len(parts) > 1:
                squad = parts[0].upper()

    nickname_clean = re.sub(r"\[.*?\]", " ", nickname)
    nickname_clean = nickname_clean.replace(".", " ")
    parts = nickname_clean.split()

    name = parts[-1].lower() if parts else ""

    return name, squad
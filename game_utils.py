# game_utils.py
from __future__ import annotations
import json, os, random
from typing import Any, Dict, List, Optional, Tuple

PLAYERS: List[str] = ["Chri", "Gabbo", "Pavi", "Fruca", "Effe", "Gargiu", "Gio"]

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_BASE_DIR, "data.json")
SCHEDULE_PATH = os.path.join(_BASE_DIR, "giornate.json")

def load_data() -> Dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data: Dict[str, Any]) -> None:
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_schedule() -> Dict[str, List[str]]:
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def next_giornata(data: Dict[str, Any]) -> int:
    # compat: supporta sia lista che dict "giornate"
    g = data.get("giornate", [])
    if isinstance(g, list):
        return len(g) + 1
    if isinstance(g, dict):
        # prendi max key + 1
        return (max(map(int, g.keys())) + 1) if g else 1
    return 1

def estrai_partite() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    data = load_data()
    schedule = load_schedule()

    bets = data.get("bets", {})
    if bets:
        last_key = max(int(k) for k in bets.keys())
        last_entry = bets[str(last_key)]
        if last_entry.get("status", "finished") != "finished":
            return None, (f"Non puoi estrarre finché la G{last_key} non è conclusa con /fine_giornata.")

    g_num = next_giornata(data)
    g_key = str(g_num)
    if g_key not in schedule:
        return None, "Non ci sono più giornate da estrarre."

    if g_key in bets:
        return None, f"La giornata {g_num} è già stata estratta."

    matches = schedule[g_key]
    if len(matches) < len(PLAYERS):
        return None, f"Nella G{g_num} non ci sono abbastanza partite per tutti."

    selected = random.sample(matches, len(PLAYERS))
    shuffled = PLAYERS.copy()
    random.shuffle(shuffled)
    assignments = {p: m for p, m in zip(shuffled, selected)}
    leftover = [m for m in matches if m not in selected]

    bets[g_key] = {
        "assignments": assignments,
        "leftover": leftover,
        "bets": {},               # qui si accumulano le /gioca
        "status": "assigned",
        "settled": False
    }
    data["bets"] = bets

    # Supporta sia lista che dict
    if isinstance(data.get("giornate"), list):
        data["giornate"].append(g_num)
    else:
        data.setdefault("giornate", {})[g_key] = {}

    save_data(data)
    return {"giornata": g_num, "assignments": assignments, "leftover": leftover}, None

def inizio_giornata() -> Tuple[Optional[int], Optional[str]]:
    data = load_data()
    bets = data.get("bets", {})
    if not bets: return None, "Nessuna giornata estratta. Usa /estrai prima."
    last_key = max(int(k) for k in bets.keys())
    entry = bets[str(last_key)]
    s = entry.get("status", "finished")
    if s == "assigned":
        entry["status"] = "started"
        save_data(data)
        return last_key, None
    if s == "started": return None, f"La giornata {last_key} è già in corso."
    return None, f"La giornata {last_key} è già stata conclusa."

def fine_giornata() -> Tuple[Optional[int], Optional[str]]:
    data = load_data()
    bets = data.get("bets", {})
    if not bets: return None, "Nessuna giornata estratta. Usa /estrai prima."
    last_key = max(int(k) for k in bets.keys())
    entry = bets[str(last_key)]
    s = entry.get("status", "finished")
    if s == "started":
        entry["status"] = "finished"
        entry["settled"] = True
        save_data(data)
        return last_key, None
    if s == "assigned":
        return None, f"La G{last_key} non è ancora iniziata. Usa /inizio_giornata prima."
    return None, f"La giornata {last_key} è già stata conclusa."

def applica_esiti_manuali(g_key: str, losers_usernames: List[str], username_to_name: Dict[str, str]) -> None:
    """
    Aggiorna punti, debiti, malloppo e marca 'vinta/persa' per l'ultima giornata finita.
    Parametri:
      - g_key: stringa numero giornata (es. "2")
      - losers_usernames: elenco '@username' che hanno perso
      - username_to_name: mappa '@user' -> 'Nome'
    """
    data = load_data()
    if "bets" not in data or g_key not in data["bets"]:
        raise ValueError("Giornata inesistente.")

    giornata = data["bets"][g_key]
    giornata.setdefault("bets", {})
    # per tutti i 7, scrivi esito coerente
    for u, name in username_to_name.items():
        # se non aveva inviato la giocata, lascia comunque un record basico
        giornata["bets"].setdefault(u, {"giocata": "(nessuna)", "quota": 0.0, "jolly": False})

        if u in losers_usernames:
            giornata["bets"][u]["esito"] = "persa"
            # punti/debiti/malloppo
            player_name = username_to_name[u]
            data["players"][player_name]["points"] += 1
            data["players"][player_name]["debt"] = data["players"][player_name].get("debt", 0) + 5
            data["malloppo"]["giocate_sbagliate"] += 5
        else:
            giornata["bets"][u]["esito"] = "vinta"

    save_data(data)

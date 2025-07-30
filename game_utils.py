"""Utility functions for the Telegram betting bot.

This module encapsulates all game logic and persistent state
management. It is separate from ``utils.py`` to avoid conflicts with
previous placeholder code. Functions here handle loading and saving
data, extracting matches for the upcoming giornata, and marking the
start and end of a giornata via explicit commands.
"""

from __future__ import annotations

import json
import os
import random
from typing import Any, Dict, List, Optional, Tuple

# Participants in the game. Order is arbitrary since assignments are
# randomised each time.
PLAYERS: List[str] = ["Chri", "Gabbo", "Pavi", "Fruca", "Effe", "Gargiu", "Gio"]

# Paths to data and schedule files relative to this module's location.
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(_BASE_DIR, "data.json")
SCHEDULE_PATH = os.path.join(_BASE_DIR, "giornate.json")


def load_data() -> Dict[str, Any]:
    """Load the game state from ``data.json``.

    Returns
    -------
    dict
        The game state as a dictionary.
    """
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: Dict[str, Any]) -> None:
    """Persist the game state back to ``data.json``.

    Parameters
    ----------
    data : dict
        The game state to write.
    """
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def load_schedule() -> Dict[str, List[str]]:
    """Load the Serie A schedule from ``giornate.json``.

    Returns
    -------
    dict
        Mapping of giornata numbers (strings) to lists of matches.
    """
    with open(SCHEDULE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def next_giornata(data: Dict[str, Any]) -> int:
    """Compute the next giornata number based on completed giornate.

    Parameters
    ----------
    data : dict
        The current game state.

    Returns
    -------
    int
        The next giornata number (1-indexed).
    """
    return len(data.get("giornate", [])) + 1


def estrai_partite() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Assign matches for the next giornata to each player.

    This function ensures that no new extraction can occur until the
    previous giornata has been marked as finished via ``fine_giornata``.

    Returns
    -------
    tuple
        A tuple where the first element is a dictionary with keys
        ``giornata``, ``assignments`` and ``leftover`` when the
        extraction is successful, and the second element is an error
        message if the extraction cannot be performed. Only one of
        these elements will be non-``None``.
    """
    data = load_data()
    schedule = load_schedule()

    # Check the status of the most recent giornata. We only allow a new
    # extraction if the last giornata is finished or if none exist.
    bets = data.get("bets", {})
    if bets:
        last_key = max(int(k) for k in bets.keys())
        last_entry = bets[str(last_key)]
        status = last_entry.get("status", "finished")
        if status != "finished":
            return None, (
                f"Non è possibile estrarre una nuova giornata finché la giornata {last_key} "
                f"non è stata conclusa con /fine_giornata."
            )

    # Determine the next giornata number.
    g_num = next_giornata(data)
    g_key = str(g_num)

    # Ensure the giornata exists in the schedule.
    if g_key not in schedule:
        return None, "Non ci sono più giornate da estrarre."

    # Prevent re-extraction for the same giornata.
    if g_key in bets:
        return None, f"La giornata {g_num} è già stata estratta."

    matches = schedule[g_key]
    if len(matches) < len(PLAYERS):
        return None, (
            f"Non ci sono abbastanza partite per tutti i giocatori nella giornata {g_num}."
        )

    # Randomly pick matches for players and shuffle the player list.
    selected_matches = random.sample(matches, len(PLAYERS))
    players_shuffled = PLAYERS.copy()
    random.shuffle(players_shuffled)
    assignments = {player: match for player, match in zip(players_shuffled, selected_matches)}
    leftover = [m for m in matches if m not in selected_matches]

    # Save the new bets entry with status 'assigned'.
    bets_entry = {
        "assignments": assignments,
        "leftover": leftover,
        "bets": {},
        "status": "assigned",
        "settled": False,
    }
    bets[g_key] = bets_entry
    data["bets"] = bets
    data.setdefault("giornate", []).append(g_num)
    save_data(data)

    return {
        "giornata": g_num,
        "assignments": assignments,
        "leftover": leftover,
    }, None

def verifica_giocata(giocata: dict, data_match: dict) -> str:
    tipo = giocata.get("tipo_verifica")
    d = giocata.get("dati_verifica", {})

    if tipo == "combo_esito":
        esiti = d.get("esiti", [])
        gol_totali = data_match["gol_totali"]
        esito_finale = data_match["esito"]  # "1", "X", "2"
        gol_range = d.get("gol_range")

        if esito_finale in esiti or any(e in esiti for e in ["1X", "X2", "12"] if esito_finale in e):
            if gol_range:
                if gol_range[0] <= gol_totali <= gol_range[1]:
                    return "vinta"
                else:
                    return "persa"
            return "vinta"
        return "persa"

    elif tipo == "combo_esito_gol":
        esiti = d.get("esiti", [])
        gol_both = data_match["gol_casa"] > 0 and data_match["gol_trasferta"] > 0
        nogol_both = data_match["gol_casa"] == 0 or data_match["gol_trasferta"] == 0
        esito_finale = data_match["esito"]

        if esito_finale in esiti or any(e in esiti for e in ["1X", "X2", "12"] if esito_finale in e):
            if d.get("gol") == "gol" and gol_both:
                return "vinta"
            elif d.get("gol") == "nogol" and nogol_both:
                return "vinta"
        return "persa"

    elif tipo == "combo_esito_over":
        esiti = d.get("esiti", [])
        over_under = d.get("over_under", {})
        gol_totali = data_match["gol_totali"]
        esito_finale = data_match["esito"]

        if esito_finale in esiti or any(e in esiti for e in ["1X", "X2", "12"] if esito_finale in e):
            val = over_under["valore"]
            if over_under["tipo"] == "over" and gol_totali > val:
                return "vinta"
            elif over_under["tipo"] == "under" and gol_totali < val:
                return "vinta"
        return "persa"

    elif tipo == "multigol_squadre":
        g_home = data_match["gol_casa"]
        g_away = data_match["gol_trasferta"]
        r_home = d["casa"]
        r_away = d["trasferta"]
        if r_home[0] <= g_home <= r_home[1] and r_away[0] <= g_away <= r_away[1]:
            return "vinta"
        return "persa"

    elif tipo == "statistica_partita":
        val = d["valore"]
        cond = d["condizione"]
        stat = d["statistica"]
        valore_match = data_match["statistiche_partita"].get(stat, 0)
        if cond == "over" and valore_match > val:
            return "vinta"
        if cond == "under" and valore_match < val:
            return "vinta"
        return "persa"

    elif tipo == "statistica_giocatore":
        player = d["giocatore"]
        stat = d["statistica"]
        valore = d["valore"]
        player_stats = data_match["giocatori"].get(player, {})
        if player_stats.get(stat, 0) >= valore:
            return "vinta"
        return "persa"

    elif tipo == "cartellino":
        player = d["giocatore"]
        cards = data_match["giocatori"].get(player, {}).get("cards", 0)
        return "vinta" if cards >= 1 else "persa"

    elif tipo == "giocatore_gol_o_assist":
        player = d["giocatore"]
        stats = data_match["giocatori"].get(player, {})
        if stats.get("goals", 0) >= 1 or stats.get("assists", 0) >= 1:
            return "vinta"
        return "persa"

    elif tipo == "chance_mix":
        cond1 = d.get("cond1")
        cond2 = d.get("cond2")
        # Qui dovrai decidere la logica OR per i due elementi
        # es: cond1 = {"tipo": "esito", "valore": "1X"}, cond2 = {"tipo": "gol", "valore": "gol"}
        # È un tipo flessibile, va strutturato caso per caso

        # per ora ritorno sempre "non implementato"
        return "non_verificabile"

    elif tipo == "combo_tripla":
        esiti = d.get("esiti", [])
        esito_ok = data_match["esito"] in esiti or any(e in esiti for e in ["1X", "X2", "12"] if data_match["esito"] in e)
        over_under = d.get("over_under")
        gol_check = d.get("gol") == "gol" and (data_match["gol_casa"] > 0 and data_match["gol_trasferta"] > 0)
        nogol_check = d.get("gol") == "nogol" and (data_match["gol_casa"] == 0 or data_match["gol_trasferta"] == 0)

        if over_under:
            val = over_under["valore"]
            if over_under["tipo"] == "over":
                ou_check = data_match["gol_totali"] > val
            else:
                ou_check = data_match["gol_totali"] < val
        else:
            ou_check = True

        if esito_ok and ou_check and (gol_check or nogol_check):
            return "vinta"
        return "persa"

    return "non_verificabile"

import requests
from bs4 import BeautifulSoup
import time

import requests
from datetime import datetime, timedelta

import os
API_KEY = os.getenv("FOOTBALL_API_KEY")
API_HOST = "https://v3.football.api-sports.io"

headers = {
    "x-apisports-key": API_KEY
}

def get_match_data(partita_nome: str) -> dict:
    # Esempio: "Roma-Napoli"
    try:
        home_team, away_team = partita_nome.split("-")
    except ValueError:
        return {"errore": "Formato partita non valido."}

    # Cerca le partite giocate ieri, oggi o domani per sicurezza
    date_range = [
        (datetime.today() - timedelta(days=1)).strftime("%Y-%m-%d"),
        datetime.today().strftime("%Y-%m-%d"),
        (datetime.today() + timedelta(days=1)).strftime("%Y-%m-%d")
    ]

    for date in date_range:
        url = f"{API_HOST}/fixtures?league=135&season=2024&date={date}"
        resp = requests.get(url, headers=headers)
        data = resp.json()

        for match in data.get("response", []):
            teams = match["teams"]
            if home_team.lower() in teams["home"]["name"].lower() and away_team.lower() in teams["away"]["name"].lower():
                fixture_id = match["fixture"]["id"]
                return parse_fixture_data(fixture_id)

    return {"errore": "Partita non trovata nelle date recenti."}

def parse_fixture_data(fixture_id: int) -> dict:
    url = f"{API_HOST}/fixtures?id={fixture_id}"
    resp = requests.get(url, headers=headers)
    data = resp.json()

    if not data["response"]:
        return {"errore": "Dettagli partita non trovati."}

    match = data["response"][0]
    goals = match["goals"]
    events = match.get("events", [])

    gol_casa = goals["home"]
    gol_trasferta = goals["away"]
    esito = (
        "1" if gol_casa > gol_trasferta
        else "2" if gol_trasferta > gol_casa
        else "X"
    )

    # Statistiche base
    stats_url = f"{API_HOST}/players?fixture={fixture_id}"
    stats_resp = requests.get(stats_url, headers=headers)
    stats_data = stats_resp.json()

    giocatori = {}
    for player_data in stats_data.get("response", []):
        name = player_data["player"]["name"]
        stats = player_data["statistics"][0]

        giocatori[name] = {
            "shots_on_target": stats["shots"]["on"] if stats["shots"] else 0,
            "shots_total": stats["shots"]["total"] if stats["shots"] else 0,
            "goals": stats["goals"]["total"] if stats["goals"] else 0,
            "assists": stats["goals"]["assists"] if stats["goals"] else 0,
            "cards": stats["cards"]["yellow"] + stats["cards"]["red"] if stats["cards"] else 0,
            "passes": stats["passes"]["total"] if stats["passes"] else 0,
            "saves": stats["goalkeeper"]["saves"] if "goalkeeper" in stats else 0
        }

    return {
        "esito": esito,
        "gol_casa": gol_casa,
        "gol_trasferta": gol_trasferta,
        "gol_totali": gol_casa + gol_trasferta,
        "statistiche_partita": {},
        "giocatori": giocatori
    }


def inizio_giornata() -> Tuple[Optional[int], Optional[str]]:
    """Mark the most recently extracted giornata as started.

    Returns
    -------
    tuple
        The giornata number that has been started, or ``None`` and an
        error message if the operation is not allowed.
    """
    data = load_data()
    bets = data.get("bets", {})
    if not bets:
        return None, "Nessuna giornata è stata estratta da iniziare. Usa /estrai prima."
    last_key = max(int(k) for k in bets.keys())
    entry = bets[str(last_key)]
    status = entry.get("status", "finished")
    if status == "assigned":
        entry["status"] = "started"
        save_data(data)
        return last_key, None
    elif status == "started":
        return None, f"La giornata {last_key} è già in corso."
    else:  # finished
        return None, f"La giornata {last_key} è già stata conclusa."


def fine_giornata() -> Tuple[Optional[int], Optional[str]]:
    """Mark the most recently started giornata as finished.

    Returns
    -------
    tuple
        The giornata number that has been finished, or ``None`` and an
        error message if the operation is not allowed.
    """
    data = load_data()
    bets = data.get("bets", {})
    if not bets:
        return None, "Nessuna giornata è stata estratta. Usa /estrai prima."
    last_key = max(int(k) for k in bets.keys())
    entry = bets[str(last_key)]
    status = entry.get("status", "finished")
    if status == "started":
        entry["status"] = "finished"
        entry["settled"] = True
        save_data(data)
        return last_key, None
    elif status == "assigned":
        return None, (
            f"La giornata {last_key} non è ancora iniziata. Usa /inizio_giornata prima di "
            "terminarla."
        )
    else:  # finished
        return None, f"La giornata {last_key} è già stata conclusa."
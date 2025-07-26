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
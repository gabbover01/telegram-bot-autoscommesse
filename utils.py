"""
Utility functions for the Telegram betting game bot.

This module provides helper functions to load and save the persistent game
state stored in a JSON file.  The state includes the list of players,
their current points and jolly counts, outstanding bets and the malloppo
(the communal pot).  All functions here are synchronous and can be
imported by the Telegram bot to manage its state.

The JSON structure is expected to follow this format:

```
{
    "players": {
        "PlayerName": {
            "points": <int>,
            "jolly": <int>,
            "debt": <int>
        },
        ...
    },
    "bets": {
        "giornata": {
            "PlayerName": {
                "match": "HomeTeam-AwayTeam",
                "odds": <float>,
                "selection": "player's bet description"
            },
            ...
        },
        ...
    },
    "malloppo": {
        "giocate_sbagliate": <float>,
        "jolly": <float>,
        "giocate_malloppo": <float>
    },
    "giornate": [ <int>, ... ]
}
```

You can adjust the path to the JSON file by setting the DATA_FILE constant.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

# Path to the JSON data file.  Relative paths are resolved relative to this
# module's location.  If you move the data file elsewhere, update this
# constant accordingly.
DATA_FILE = Path(__file__).with_name("data.json")


def load_data() -> Dict[str, Any]:
    """Load the persistent state from the JSON file.

    Returns
    -------
    dict
        A dictionary representing the entire game state.  If the file does
        not exist, a KeyError will be raised.

    Raises
    ------
    FileNotFoundError
        If the data file does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    """
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Data file {DATA_FILE} does not exist")
    with DATA_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data: Dict[str, Any]) -> None:
    """Persist the given game state to disk.

    Parameters
    ----------
    data : dict
        The game state to write.  It should follow the structure described
        in the module docstring.
    """
    with DATA_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
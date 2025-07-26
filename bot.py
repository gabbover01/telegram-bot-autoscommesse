"""
Telegram bot for managing the Serie A betting game.

This script defines a Telegram bot that automates the weekly betting game
for a group of friends. It handles match extraction, tracks points and
jolly usage, and allows an admin to mark the start and end of each
giornata (matchday). The bot reads and writes persistent state via
``game_utils.py``.

Commands implemented:
  /start            – conferma che il bot è attivo
  /classifica       – mostra la classifica attuale dei giocatori
  /estrai           – estrae le partite per la prossima giornata
  /inizio_giornata  – segna l’inizio della giornata estratta
  /fine_giornata    – segna la fine della giornata in corso

To run this bot locally, ensure you have set the ``TELEGRAM_BOT_TOKEN``
environment variable to your bot token, then execute:
    python bot.py
The bot uses python-telegram-bot v20+, which requires Python 3.8–3.12.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

import game_utils  # custom module containing game state logic


# Set up basic logging. Adjust level to logging.WARNING to reduce verbosity.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the user sends /start."""
    await update.message.reply_text(
        "✅ Bot attivo! Benvenuto al gioco delle scommesse. Usa /estrai per iniziare."
    )


async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the current standings to the chat."""
    data = game_utils.load_data()
    players: Dict[str, Dict[str, int]] = data.get("players", {})
    if not players:
        await update.message.reply_text(
            "Nessun dato disponibile. Inizializza il gioco prima di visualizzare la classifica."
        )
        return
    # Sort players by points (ascending) and display remaining jolly
    sorted_players = sorted(players.items(), key=lambda x: x[1].get("points", 0))
    lines: List[str] = ["📊 Classifica attuale:"]
    for name, info in sorted_players:
        points = info.get("points", 0)
        jolly_left = info.get("jolly", 0)
        lines.append(f"• {name}: {points} punti (jolly rimasti: {jolly_left})")
    await update.message.reply_text("\n".join(lines))


async def estrai(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extract matches for the upcoming giornata and assign them to players."""
    result, error = game_utils.estrai_partite()
    if error:
        await update.message.reply_text(error)
        return
    assert result is not None  # for type checking
    giornata: int = result["giornata"]
    assignments: Dict[str, str] = result["assignments"]
    leftover: List[str] = result["leftover"]
    lines: List[str] = [f"🎲 Estrazione giornata {giornata}:"]
    for player, match in assignments.items():
        lines.append(f"• {player} → {match}")
    if leftover:
        lines.append("\nPartite rimaste fuori:")
        for match in leftover:
            lines.append(f"- {match}")
    await update.message.reply_text("\n".join(lines))


async def inizio_giornata_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark the most recently extracted giornata as started."""
    giornata, error = game_utils.inizio_giornata()
    if error:
        await update.message.reply_text(error)
    else:
        await update.message.reply_text(
            f"🚦 La giornata {giornata} è stata avviata! Buona fortuna a tutti."
        )


async def fine_giornata_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Mark the current giornata as finished, allowing a new extraction."""
    giornata, error = game_utils.fine_giornata()
    if error:
        await update.message.reply_text(error)
    else:
        await update.message.reply_text(
            f"🏁 La giornata {giornata} è stata conclusa. È possibile procedere con una nuova estrazione."
        )


def main() -> None:
    """Initialize the bot and start polling for updates."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "Il TOKEN del bot non è stato impostato. Definisci la variabile d'ambiente TELEGRAM_BOT_TOKEN."
        )
    application = ApplicationBuilder().token(token).build()
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("classifica", classifica))
    application.add_handler(CommandHandler("estrai", estrai))
    application.add_handler(CommandHandler("inizio_giornata", inizio_giornata_handler))
    application.add_handler(CommandHandler("fine_giornata", fine_giornata_handler))
    logger.info("Bot avviato. In attesa di comandi…")
    application.run_polling()


if __name__ == "__main__":
    main()
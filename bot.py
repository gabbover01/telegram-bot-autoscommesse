"""
Telegram bot implementation for the Serie A betting game.

This script defines the command handlers for the Telegram bot that automates
the game described by the user.  It currently implements the `/start`
command, which simply confirms that the bot is running, and the
`/classifica` command, which displays the current leaderboard based on the
data stored in ``data.json``.  Additional commands such as `/estrai` and
`/gioca` can be added later following the same pattern.

To run this bot locally, install the requirements listed in
``requirements.txt`` and set the ``TELEGRAM_BOT_TOKEN`` environment
variable (or edit ``config.py`` to supply your token and import it here).

Example::

    $ export TELEGRAM_BOT_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
    $ python bot.py

The bot will start polling for updates and respond to supported commands.
"""

from __future__ import annotations

import logging
import os
from typing import Dict

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from utils import load_data

# Configure basic logging.  This will print information to stdout which
# can be helpful during development or debugging.  In production you
# might want to customise the log format or destination.
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# Try to get the token from an environment variable first, then fall
# back to config.py if available.  This allows flexibility when
# deploying to platforms like Railway or Heroku.
try:
    from config import TOKEN as CONFIG_TOKEN  # type: ignore
except Exception:
    CONFIG_TOKEN = None

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", CONFIG_TOKEN)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command.

    This simply acknowledges that the bot is up and running.  It can be
    extended later to provide help or other introductory information.
    """
    await update.message.reply_text("✅ Bot autoscommesse attivo!")


async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /classifica command.

    Loads the current standings from the JSON file, sorts the players by
    their points in ascending order (lower is better), and sends a
    formatted message back to the chat.  If the data file cannot be
    loaded, an error message is sent instead.
    """
    try:
        data: Dict[str, Dict] = load_data()
        players: Dict[str, Dict[str, int]] = data.get("players", {})
    except Exception as exc:
        logger.exception("Failed to load data: %s", exc)
        await update.message.reply_text("⚠️ Errore nel caricamento dei dati.")
        return

    if not players:
        await update.message.reply_text("ℹ️ Nessun giocatore registrato.")
        return

    # Sort players by points (ascending) and then by name (alphabetically)
    sorted_players = sorted(
        players.items(), key=lambda item: (item[1].get("points", 0), item[0].lower())
    )

    # Build the leaderboard message.
    lines = ["📊 Classifica attuale:"]
    for position, (nome, info) in enumerate(sorted_players, start=1):
        punti = info.get("points", 0)
        jolly = info.get("jolly", 0)
        lines.append(f"{position}. {nome} – {punti} punti (jolly rimasti: {jolly})")

    message = "\n".join(lines)
    await update.message.reply_text(message)


def main() -> None:
    """Start the Telegram bot and register command handlers.

    This version of ``main`` is synchronous and uses the built-in
    ``run_polling()`` method.  It avoids issues with nested event loops
    that can occur when ``asyncio.run`` is used on certain platforms.
    """
    if not TOKEN:
        raise RuntimeError(
            "Il TOKEN del bot non è stato impostato. "
            "Definisci la variabile d'ambiente TELEGRAM_BOT_TOKEN "
            "oppure inseriscilo in config.py come TOKEN."
        )

    # Build the application.  The token argument is required to
    # authenticate with Telegram.
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers.  Additional commands can be added
    # following this pattern.
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("classifica", classifica))

    logger.info("Bot avviato. In attesa di comandi…")
    # Start polling for updates.  This call does not return until the
    # bot is stopped (e.g., by pressing Ctrl+C).
    application.run_polling()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot interrotto manualmente.")
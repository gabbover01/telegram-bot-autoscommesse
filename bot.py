from telegram.ext import CommandHandler
from game_utils import load_data
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    players = data["players"]

    classifica_text = "📊 Classifica attuale:\n"
    sorted_players = sorted(players.items(), key=lambda x: x[1]["points"])

    for nome, info in sorted_players:
        classifica_text += f"• {nome}: {info['points']} punti\n"

    await update.message.reply_text(classifica_text)

# Leggi il token dalla variabile d'ambiente
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo!")

import asyncio  # Assicurati di averlo importato in alto

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    await app.bot.delete_webhook(drop_pending_updates=True)  # ✅ fix qui

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("classifica", classifica))
    app.add_handler(CommandHandler("estrai", estrai))
    app.add_handler(CommandHandler("gioca", gioca))
    app.add_handler(CommandHandler("inizio_giornata", inizio_giornata))
    app.add_handler(CommandHandler("fine_giornata", fine_giornata))
    app.add_handler(CommandHandler("jolly", mostra_jolly))

    print("🚀 Bot avviato...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())


# Modifica forzata per commit


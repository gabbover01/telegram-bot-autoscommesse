
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json

TOKEN = "7719502887:AAHU2Cl9jrwxSJIUFZ8Esp2D-bQfcaQzk94"  # Da sostituire con il vero token su Railway
DATA_FILE = "data.json"

# ✅ Definisci l'elenco dei giocatori
GIOCATORI = ["Chri", "Gabbo", "Pavi", "Fruca", "Effe", "Gargiu", "Gio"]

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Benvenuto nel bot delle autoscommesse! ⚽")

async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    classifica = data.get("classifica", {})
    response = "📊 Classifica:\n"
    for nome in GIOCATORI:
        punti = classifica.get(nome, 0)
        response += f"{nome:<10} →  {punti} punti\n"
    await update.message.reply_text(response)

async def jolly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    jolly_dict = data.get("jolly", {})
    response = "🃏 Jolly usati:\n"
    for nome in GIOCATORI:
        jolly_usati = jolly_dict.get(nome, 0)
        response += f"{nome:<10} →  {jolly_usati} jolly\n"
    await update.message.reply_text(response)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("classifica", classifica))
    app.add_handler(CommandHandler("jolly", jolly))

    print("🚀 Bot avviato...")

    asyncio.run(delete_webhook_and_run(app))

async def delete_webhook_and_run(app):
    await app.bot.delete_webhook(drop_pending_updates=True)
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await app.updater.idle()
    app.run_polling()

if __name__ == "__main__":
    main()

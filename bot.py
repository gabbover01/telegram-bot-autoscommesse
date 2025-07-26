
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import json

TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # Da sostituire con il vero token su Railway

DATA_FILE = "data.json"

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Benvenuto nel bot delle autoscommesse! ⚽")

async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    response = "📊 Classifica:\n"
"
    for user, info in data["players"].items():
        response += f"{user}: {info['points']} punti | Jolly usati: {info.get('jolly', 0)}
"
    await update.message.reply_text(response)

async def jolly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    response = "🃏 Jolly usati:
"
    for user, info in data["players"].items():
        jolly_usati = info.get("jolly", 0)
        response += f"{user}: {jolly_usati} jolly
"
    await update.message.reply_text(response)

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("classifica", classifica))
    app.add_handler(CommandHandler("jolly", jolly))
    print("🚀 Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()

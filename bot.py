from telegram.ext import CommandHandler
from utils import load_data
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

def main():
    app.add_handler(CommandHandler("classifica", classifica))

    print("🔍 TOKEN:", TOKEN)

    if not TOKEN:
        raise ValueError("❌ TOKEN non trovato. Imposta la variabile TELEGRAM_BOT_TOKEN su Railway.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()
# Modifica forzata per commit


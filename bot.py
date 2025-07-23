from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

# Leggi il token dalla variabile d'ambiente
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot attivo!")

def main():
    print("🔍 TOKEN:", TOKEN)

    if not TOKEN:
        raise ValueError("❌ TOKEN non trovato. Imposta la variabile TELEGRAM_BOT_TOKEN su Railway.")

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("🚀 Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()

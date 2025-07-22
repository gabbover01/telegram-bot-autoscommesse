from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import config

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot attivo!")

def main():
    app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("Bot avviato...")
    app.run_polling()

if __name__ == "__main__":
    main()
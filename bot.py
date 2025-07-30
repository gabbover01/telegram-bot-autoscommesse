import asyncio
import os
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from game_utils import load_data, save_data, inizio_giornata, fine_giornata 

TOKEN = "7719502887:AAHU2Cl9jrwxSJIUFZ8Esp2D-bQfcaQzk94"
DATA_FILE = "data.json"
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

USERNAME_TO_NAME = {
    "@Federico_Lolli": "Effe",
    "@Federico9499": "Fruca",
    "@agggg21": "Gargiu",
    "@BTC_TonyStark": "Gabbo",
    "@TheBu7cher": "Pavi",
    "@Chris4rda": "Chri",
    "@JoLaFlame": "Gio"
}

MIN_QUOTA = 1.50

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Ciao! Benvenuto nel bot delle autoscommesse! ⚽")

async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    response = "📊 Classifica:\n"
    for username in USERNAME_TO_NAME:
        name = USERNAME_TO_NAME[username]
        punti = data["players"][name]["points"]
        response += f"{username:<15} →  {punti} punti\n"
    await update.message.reply_text(response)

async def jolly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    response = "🃏 Jolly usati:\n"
    for username in USERNAME_TO_NAME:
        name = USERNAME_TO_NAME[username]
        jolly_usati = data["players"][name]["jolly_used"]
        response += f"{username:<15} →  {jolly_usati} jolly\n"
    await update.message.reply_text(response)

async def gioca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"

    if username not in USERNAME_TO_NAME:
        await update.message.reply_text("❌ Non sei autorizzato a giocare.")
        return

    text = update.message.text.replace("/gioca", "").strip()
    match = re.match(r"(.+)\s+([0-9]+\.[0-9]+)", text)
    if not match:
        await update.message.reply_text("⚠️ Usa il formato: /gioca <giocata> <quota>. Es: /gioca Over 2.5 1.65")
        return

    giocata = match.group(1).strip()
    quota = float(match.group(2))

    data = load_data()
    bets = data.get("bets", {})
    if not bets:
        await update.message.reply_text("❌ Nessuna giornata attiva. Usa /estrai prima.")
        return

    g_key = str(max(int(k) for k in bets.keys()))
    giornata = bets[g_key]

    if giornata["status"] != "assigned":
        await update.message.reply_text("❌ Le giocate non sono più accettate per questa giornata.")
        return

    giornata.setdefault("bets", {})
    giornata["bets"][username] = {
        "giocata": giocata,
        "quota": quota,
        "jolly": False
    }

    if quota < MIN_QUOTA:
        context.user_data["pending_jolly"] = {
            "username": username,
            "giocata": giocata,
            "quota": quota,
            "giornata_key": g_key
        }
        keyboard = [[
            InlineKeyboardButton("🃏 Sì", callback_data="jolly_yes"),
            InlineKeyboardButton("❌ No", callback_data="jolly_no")
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ La quota è sotto 1.50. Vuoi usare un jolly?", reply_markup=reply_markup)
        return

    save_data(data)
    await aggiorna_riepilogo_giocate(update, context, g_key)
    await update.message.reply_text(f"✅ Giocata salvata: {giocata} @ {quota:.2f}")

async def handle_jolly_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    choice = query.data
    pending = context.user_data.get("pending_jolly")

    if not pending:
        await query.edit_message_text("❌ Nessuna giocata in sospeso.")
        return

    data = load_data()
    g_key = pending["giornata_key"]
    giornata = data["bets"][g_key]
    username = pending["username"]
    player_name = USERNAME_TO_NAME[username]

    giornata.setdefault("bets", {})

    if choice == "jolly_yes":
        giornata["bets"][username] = {
            "giocata": pending["giocata"],
            "quota": pending["quota"],
            "jolly": True
        }

        data["players"][player_name]["jolly_used"] += 1

        if data["players"][player_name]["jolly_used"] > 3:
            data["malloppo"]["penali_jolly"] += 20
            data["players"][player_name]["debt"] += 20

        save_data(data)
        await aggiorna_riepilogo_giocate(update, context, g_key)
        await query.edit_message_text("🃏 Jolly usato. Giocata salvata.")
        await jolly(update, context)
    else:
        await query.edit_message_text("❌ Giocata annullata. Riprova con una quota ≥ 1.50.")

async def aggiorna_riepilogo_giocate(update: Update, context: ContextTypes.DEFAULT_TYPE, g_key: str):
    data = load_data()
    giornata = data["bets"][g_key]
    bets = giornata.get("bets", {})

    lines = ["📋 *GIOCATE GIORNATA {}*".format(g_key)]
    for username in USERNAME_TO_NAME:
        if username in bets:
            giocata = bets[username]["giocata"]
            quota = bets[username]["quota"]
            jolly = " 🃏" if bets[username]["jolly"] else ""
            lines.append(f"{username}: {giocata} @ {quota:.2f}{jolly}")
        else:
            lines.append(f"{username}: ❌ Non ancora giocato")

    text = "\n".join(lines)
    message_id = giornata.get("summary_message_id")
    chat_id = update.effective_chat.id

    if message_id:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            print("Errore aggiornamento messaggio:", e)
    else:
        msg = await context.bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
        giornata["summary_message_id"] = msg.message_id
        save_data(data)

async def inizio_giornata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giornata_num, error = inizio_giornata()
    if error:
        await update.message.reply_text(f"❌ {error}")
        return

    data = load_data()
    g_key = str(giornata_num)
    bets = data["bets"][g_key]
    non_giocati = []

    for username in USERNAME_TO_NAME:
        if username not in bets.get("bets", {}):
            non_giocati.append(username)
            name = USERNAME_TO_NAME[username]
            data["players"][name]["points"] += 1
            data["malloppo"]["giocate_sbagliate"] += 5
            data["players"][name]["debt"] += 5

    save_data(data)

    if non_giocati:
        msg = "\n".join([f"{u}, sei un coglione non hai giocato" for u in non_giocati])
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("✅ Tutti hanno giocato! Giornata iniziata.")

async def fine_giornata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    giornata_num, error = fine_giornata()
    if error:
        await update.message.reply_text(f"❌ {error}")
    else:
        await update.message.reply_text(f"✅ Giornata {giornata_num} conclusa correttamente. Ora puoi usare /estrai per la prossima.")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("classifica", classifica))
    app.add_handler(CommandHandler("jolly", jolly))
    app.add_handler(CommandHandler("gioca", gioca))
    app.add_handler(CommandHandler("inizio_giornata", inizio_giornata_cmd))
    app.add_handler(CommandHandler("fine_giornata", fine_giornata_cmd))
    app.add_handler(CallbackQueryHandler(handle_jolly_response))

    print(f"🚀 Imposto webhook su: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()

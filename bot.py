import asyncio
import os
import json
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters 
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

    # Salva giocata base in user_data
    context.user_data["giocata_temp"] = {
        "username": username,
        "quota": quota,
        "giocata": giocata,
        "giornata_key": g_key,
        "step": "tipo_verifica"
    }

    keyboard = [[
        InlineKeyboardButton("📊 Statistica Giocatore", callback_data="verifica_statistica"),
        InlineKeyboardButton("🎯 Esito/Combo", callback_data="verifica_esito"),
        InlineKeyboardButton("🟨 Cartellino", callback_data="verifica_cartellino")
    ]]
    await update.message.reply_text(
        "👉 Che tipo di giocata è?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

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

async def handle_verifica_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.user_data.get("giocata_temp")
    if not data:
        await query.edit_message_text("❌ Nessuna giocata in sospeso.")
        return

    data["step"] = "inserimento_dati"
    callback = query.data

    if callback == "verifica_statistica":
        data["tipo_verifica"] = "statistica_giocatore"
        await query.edit_message_text("✍️ Scrivi il nome del giocatore, la statistica e il valore.\nEsempio: *Pellegrini shots_on_target 2*", parse_mode="Markdown")

    elif callback == "verifica_esito":
        data["tipo_verifica"] = "combo_esito"
        await query.edit_message_text("✍️ Scrivi gli esiti previsti (es: 1X MG 2-4)", parse_mode="Markdown")

    elif callback == "verifica_cartellino":
        data["tipo_verifica"] = "cartellino"
        await query.edit_message_text("✍️ Scrivi il nome del giocatore che deve prendere il cartellino.\nEs: *Di Lorenzo*", parse_mode="Markdown")

    context.user_data["giocata_temp"] = data

async def ricevi_testo_verifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.strip()
    data = context.user_data.get("giocata_temp")
    if not data:
        return

    step = data.get("step")
    g_key = data["giornata_key"]
    data_finale = load_data()
    username = data["username"]
    player_name = USERNAME_TO_NAME[username]

    if step == "inserimento_dati":
        tipo = data["tipo_verifica"]
        quota = data["quota"]
        giocata = {
            "giocata": data["giocata"],
            "quota": quota,
            "jolly": False,
            "tipo_verifica": tipo,
            "esito": "pending"
        }

        if quota < MIN_QUOTA:
            giocata["jolly"] = True
            data_finale["players"][player_name]["jolly_used"] += 1
            if data_finale["players"][player_name]["jolly_used"] > 3:
                data_finale["malloppo"]["penali_jolly"] += 20
                data_finale["players"][player_name]["debt"] += 20

        if tipo == "statistica_giocatore":
            try:
                nome, stat, val = user_input.split()
                giocata["dati_verifica"] = {
                    "giocatore": nome,
                    "statistica": stat,
                    "valore": int(val)
                }
                context.user_data["giocata_temp"]["completata"] = giocata
                context.user_data["giocata_temp"]["step"] = "alternativa"
                await update.message.reply_text("⚠️ La giocata è su un giocatore. Scrivi ora una *giocata alternativa* in caso non giochi.")
                return
            except:
                await update.message.reply_text("⚠️ Formato errato. Es: Pellegrini shots_on_target 2")
                return

        elif tipo == "combo_esito":
            esiti = user_input.upper().split()
            gol_range = None
            for e in esiti:
                if "-" in e:
                    parts = e.split("-")
                    if len(parts) == 2 and all(p.isdigit() for p in parts):
                        gol_range = [int(parts[0]), int(parts[1])]
            giocata["dati_verifica"] = {"esiti": esiti, "gol_range": gol_range}

        elif tipo == "cartellino":
            giocata["dati_verifica"] = {"giocatore": user_input}

        data_finale["bets"][g_key].setdefault("bets", {})[username] = giocata
        save_data(data_finale)
        await update.message.reply_text("✅ Giocata salvata.")
        await aggiorna_riepilogo_giocate(update, context, g_key)
        context.user_data["giocata_temp"] = None
        return

    if step == "alternativa":
        giocata_base = context.user_data["giocata_temp"]["completata"]
        giocata_base["alternativa"] = {
            "giocata": user_input,
            "tipo_verifica": "combo_esito",
            "dati_verifica": {"esiti": user_input.upper().split()}
        }

        data_finale["bets"][g_key].setdefault("bets", {})[username] = giocata_base
        save_data(data_finale)

        await update.message.reply_text("✅ Giocata e alternativa salvate.")
        await aggiorna_riepilogo_giocate(update, context, g_key)
        context.user_data["giocata_temp"] = None

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
from game_utils import estrai_partite  # assicurati che sia importato

from game_utils import get_match_data, verifica_giocata, save_data, load_data

async def aggiorna_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    bets = data.get("bets", {})
    if not bets:
        await update.message.reply_text("❌ Nessuna giornata da aggiornare.")
        return

    g_key = str(max(int(k) for k in bets.keys()))
    giornata = bets[g_key]

    if giornata["status"] != "finished":
        await update.message.reply_text("⚠️ La giornata non è ancora conclusa. Usa /fine_giornata prima.")
        return

    summary = [f"📊 *Aggiornamento Giornata {g_key}*"]
    for username, giocata in giornata.get("bets", {}).items():
        player_name = USERNAME_TO_NAME[username]
        partita = giornata["assignments"].get(player_name)

        if not partita:
            summary.append(f"{username}: ❌ Nessuna partita assegnata.")
            continue

        match_data = get_match_data(partita)

        # Se giocata su giocatore, verifica presenza
        tipo = giocata.get("tipo_verifica")
        if tipo == "statistica_giocatore" or tipo == "cartellino" or tipo == "giocatore_gol_o_assist":
            giocatore = giocata["dati_verifica"].get("giocatore")
            stats = match_data.get("giocatori", {}).get(giocatore, {})
            ha_giocato = any(stats.values())

            if not ha_giocato and "alternativa" in giocata:
                giocata = giocata["alternativa"]
                summary.append(f"{username}: 🔁 Usata giocata alternativa perché {giocatore} non ha giocato")

        esito = verifica_giocata(giocata, match_data)
        giocata["esito"] = esito

        if esito == "vinta":
            summary.append(f"{username}: ✅ Vinta")
        elif esito == "persa":
            data["players"][player_name]["points"] += 1
            data["players"][player_name]["debt"] += 5
            data["malloppo"]["giocate_sbagliate"] += 5
            summary.append(f"{username}: ❌ Persa (+1 punto, +5€)")
        else:
            summary.append(f"{username}: ⚠️ Non verificabile automaticamente")

    save_data(data)
    await update.message.reply_text("\n".join(summary), parse_mode="Markdown")

async def estrai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result, error = estrai_partite()
    if error:
        await update.message.reply_text(f"❌ {error}")
        return

    giornata = result["giornata"]
    assignments = result["assignments"]
    leftover = result["leftover"]

    text = f"🎲 *Partite estratte per la giornata {giornata}*\n\n"
    for player, match in assignments.items():
        username = next((u for u, n in USERNAME_TO_NAME.items() if n == player), player)
        text += f"{username}: {match}\n"

    if leftover:
        text += "\n❗ Partite non assegnate:\n"
        for match in leftover:
            text += f"- {match}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def soldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    response = "💰 *Situazione versamenti:*\n\n"

    for username, name in USERNAME_TO_NAME.items():
        player = data["players"][name]
        debt = player.get("debt", 0)
        paid = player.get("paid", 0)
        status = "✅" if paid >= debt else "❌"
        response += f"{username:<15} → Deve {debt}€, Ha versato {paid}€ {status}\n"

    await update.message.reply_text(response, parse_mode="Markdown")


async def versa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.username != "Federico9499":
        await update.message.reply_text("❌ Solo Fruca può gestire i versamenti.")
        return

    try:
        args = context.args
        if len(args) != 2:
            raise ValueError("Formato errato")

        username = args[0]
        euro = int(args[1])

        if username not in USERNAME_TO_NAME:
            await update.message.reply_text("❌ Username non valido.")
            return

        name = USERNAME_TO_NAME[username]
        data = load_data()

        data["players"][name].setdefault("paid", 0)
        data["players"][name]["paid"] += euro

        save_data(data)
        await update.message.reply_text(f"✅ Aggiunti {euro}€ a {username}.")
    except Exception as e:
        await update.message.reply_text("⚠️ Usa il formato: /versa @username <euro>\nEsempio: /versa @Chris4rda 5")

    giornata = result["giornata"]
    assignments = result["assignments"]
    leftover = result["leftover"]

    text = f"🎲 *Partite estratte per la giornata {giornata}*\n\n"
    for player, match in assignments.items():
        username = next((u for u, n in USERNAME_TO_NAME.items() if n == player), player)
        text += f"{username}: {match}\n"

    if leftover:
        text += "\n❗ Partite non assegnate:\n"
        for match in leftover:
            text += f"- {match}\n"

    await update.message.reply_text(text, parse_mode="Markdown")

async def malloppo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_data()
    args = context.args

    solo_giocate = False
    if args and args[0] == "solo_giocate":
        solo_giocate = True

    m = data["malloppo"]
    totale = m["giocate_sbagliate"] + m["penali_jolly"] + m["giocate_gruppo"]
    
    if solo_giocate:
        text = f"💰 *Malloppo solo giocate sbagliate:* {m['giocate_sbagliate']}€"
    else:
        text = (
            f"💰 *Malloppo Totale: {totale}€*\n\n"
            f"- Giocate sbagliate: {m['giocate_sbagliate']}€\n"
            f"- Penali jolly: {m['penali_jolly']}€\n"
            f"- Giocate di gruppo: {m['giocate_gruppo']}€"
        )

    await update.message.reply_text(text, parse_mode="Markdown")

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("classifica", classifica))
    app.add_handler(CommandHandler("jolly", jolly))
    app.add_handler(CommandHandler("gioca", gioca))
    app.add_handler(CommandHandler("inizio_giornata", inizio_giornata_cmd))
    app.add_handler(CommandHandler("fine_giornata", fine_giornata_cmd))
    app.add_handler(CallbackQueryHandler(handle_jolly_response))
    app.add_handler(CommandHandler("estrai", estrai_cmd))
    app.add_handler(CallbackQueryHandler(handle_verifica_callback, pattern="^verifica_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ricevi_testo_verifica))
    app.add_handler(CommandHandler("aggiorna", aggiorna_cmd))
    app.add_handler(CommandHandler("soldi", soldi))
    app.add_handler(CommandHandler("versa", versa))
    app.add_handler(CommandHandler("malloppo", malloppo))


    print(f"🚀 Imposto webhook su: {WEBHOOK_URL}")
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8080)),
        webhook_url=WEBHOOK_URL,
    )

if __name__ == "__main__":
    main()

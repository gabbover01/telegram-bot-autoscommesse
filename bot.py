import os, re, json
from typing import List, Dict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

from game_utils import (
    load_data, save_data,
    estrai_partite, inizio_giornata, fine_giornata,
    applica_esiti_manuali
)

# ====== CONFIG ======
TOKEN = os.getenv("BOT_TOKEN", "REPLACE_ME_TOKEN")  # set in Railway as BOT_TOKEN
WEBHOOK_URL = os.getenv("WEBHOOK_URL")              # es: https://<app>.up.railway.app
MIN_QUOTA = 1.50
TOT_JOLLY = 3
JOLLY_PENALTY_EUR = 20

# Admin che può usare /estrai /inizio_giornata /fine_giornata /esiti /versa
ADMINS = {"@BTC_TonyStark"}

# Mappa username -> Nome giocatore
USERNAME_TO_NAME: Dict[str, str] = {
    "@Federico_Lolli": "Effe",
    "@Federico9499": "Fruca",
    "@agggg21": "Gargiu",
    "@BTC_TonyStark": "Gabbo",
    "@TheBu7cher": "Pavi",
    "@Chris4rda": "Chri",
    "@JoLaFlame": "Gio"
}
NAME_TO_USERNAME = {v: k for k, v in USERNAME_TO_NAME.items()}


# ====== HELPERS ======
def is_admin(username: str) -> bool:
    return username in ADMINS


async def pin_or_edit_summary(update: Update, context: ContextTypes.DEFAULT_TYPE, g_key: str) -> None:
    """Crea/aggiorna e mette in pin il messaggio riassuntivo delle giocate della giornata."""
    data = load_data()
    giornata = data["bets"][g_key]
    bets = giornata.get("bets", {})

    lines = [f"📋 GIOCATE GIORNATA {g_key}"]
    for u, name in USERNAME_TO_NAME.items():
        if u in bets:
            giocata = bets[u].get("giocata", "(nessuna)")
            quota = bets[u].get("quota", 0.0)
            jolly = " 🃏" if bets[u].get("jolly") else ""
            lines.append(f"{u}: {giocata} @ {quota:.2f}{jolly}")
        else:
            lines.append(f"{u}: ❌ Non ancora giocato")
    text = "\n".join(lines)

    chat_id = update.effective_chat.id
    try:
        if "pinned_summary_id" in giornata:
            await context.bot.unpin_chat_message(chat_id=chat_id, message_id=giornata["pinned_summary_id"])
    except Exception:
        pass

    msg_id = giornata.get("summary_message_id")
    if msg_id:
        try:
            await context.bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text)
            new_id = msg_id
        except Exception:
            m = await context.bot.send_message(chat_id=chat_id, text=text)
            new_id = m.message_id
            giornata["summary_message_id"] = new_id
    else:
        m = await context.bot.send_message(chat_id=chat_id, text=text)
        new_id = m.message_id
        giornata["summary_message_id"] = new_id

    try:
        await context.bot.pin_chat_message(chat_id=chat_id, message_id=new_id)
        giornata["pinned_summary_id"] = new_id
    except Exception:
        pass

    save_data(data)


# ====== COMMANDS ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Ciao! Bot autoscommesse ⚽\n"
        "Comandi:\n"
        "/estrai  /inizio_giornata  /fine_giornata  /esiti (admin)\n"
        "/gioca  /modifica\n"
        "/classifica  /jolly  /Jolly  /malloppo [totale|solo giocate]\n"
        "/soldi  /versa @user <euro> (admin)  /giornate  /aggiorna"
    )


async def classifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    txt = "📊 Classifica:\n"
    for u, name in USERNAME_TO_NAME.items():
        txt += f"{u:<15} → {d['players'][name]['points']} punti\n"
    await update.message.reply_text(txt)


async def jolly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    txt = "🃏 Jolly usati:\n"
    for u, name in USERNAME_TO_NAME.items():
        txt += f"{u:<15} → {d['players'][name]['jolly_used']} jolly\n"
    await update.message.reply_text(txt)


async def gioca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"
    if username not in USERNAME_TO_NAME:
        await update.message.reply_text("❌ Non sei autorizzato.")
        return

    text = update.message.text.replace("/gioca", "", 1).strip()
    m = re.match(r"(.+)\s+([0-9]+(?:\.[0-9]+)?)$", text)
    if not m:
        await update.message.reply_text("Formato: /gioca <testo giocata> <quota>\nEs: /gioca Over 2.5 1.65")
        return

    giocata = m.group(1).strip()
    quota = float(m.group(2))
    d = load_data()
    bets = d.get("bets", {})
    if not bets:
        await update.message.reply_text("❌ Nessuna giornata attiva. Usa /estrai prima.")
        return

    g_key = str(max(int(k) for k in bets.keys()))
    giornata = bets[g_key]
    if giornata["status"] not in ("assigned", "started"):
        await update.message.reply_text("❌ Le giocate non sono più accettate (giornata conclusa).")
        return

    giornata.setdefault("bets", {})
    giornata["bets"][username] = {
        "giocata": giocata,
        "quota": quota,
        "jolly": quota < MIN_QUOTA
    }

    # Gestione jolly "a cicli" con penale dopo TOT_JOLLY
    if quota < MIN_QUOTA:
        name = USERNAME_TO_NAME[username]
        used = d["players"][name].get("jolly_used", 0) + 1
        if used > TOT_JOLLY:
            # scatta penale e riparte il conteggio
            d["players"][name]["jolly_used"] = 1
            d["players"][name]["debt"] = d["players"][name].get("debt", 0) + JOLLY_PENALTY_EUR
            d["malloppo"]["penali_jolly"] += JOLLY_PENALTY_EUR
            extra = f" 💸 Penale {JOLLY_PENALTY_EUR}€ applicata, jolly azzerati (ora 1/{TOT_JOLLY})."
        else:
            d["players"][name]["jolly_used"] = used
            extra = f" 🃏 Jolly usato ({used}/{TOT_JOLLY})."
    else:
        extra = ""

    save_data(d)
    await update.message.reply_text(f"✅ Giocata salvata.{extra}")
    await pin_or_edit_summary(update, context, g_key)


async def modifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"
    if username not in USERNAME_TO_NAME:
        await update.message.reply_text("❌ Non sei autorizzato.")
        return
    d = load_data()
    bets = d.get("bets", {})
    if not bets:
        await update.message.reply_text("❌ Nessuna giornata attiva.")
        return
    g_key = str(max(int(k) for k in bets.keys()))
    giornata = bets[g_key]
    if giornata["status"] != "assigned":
        await update.message.reply_text("⚠️ Giornata già iniziata: non puoi modificare.")
        return
    if username not in giornata.get("bets", {}):
        await update.message.reply_text("❌ Non hai ancora giocato.")
        return
    del giornata["bets"][username]
    save_data(d)
    await update.message.reply_text("✏️ Giocata cancellata. Re-invia con /gioca …")


async def estrai_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"
    if not is_admin(username):
        await update.message.reply_text("❌ Solo l'admin può estrarre.")
        return
    result, error = estrai_partite()
    if error:
        await update.message.reply_text(f"❌ {error}")
        return
    giornata = result["giornata"]
    assignments = result["assignments"]
    leftover = result["leftover"]
    txt = f"🎲 *Partite estratte per la giornata {giornata}*\n\n"
    for player, match in assignments.items():
        u = NAME_TO_USERNAME.get(player, player)
        txt += f"{u}: {match}\n"
    if leftover:
        txt += "\n❗ Partite non assegnate:\n" + "\n".join(f"- {m}" for m in leftover)
    await update.message.reply_text(txt, parse_mode="Markdown")


async def inizio_giornata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if f"@{user.username}" not in ADMINS:
        await update.message.reply_text("❌ Solo l'admin può iniziare la giornata.")
        return
    gnum, err = inizio_giornata()
    if err:
        await update.message.reply_text(f"❌ {err}")
        return
    await update.message.reply_text(f"🏁 Giornata {gnum} iniziata. Buone giocate!")


async def fine_giornata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if f"@{user.username}" not in ADMINS:
        await update.message.reply_text("❌ Solo l'admin può chiudere la giornata.")
        return
    gnum, err = fine_giornata()
    if err:
        await update.message.reply_text(f"❌ {err}")
        return
    await update.message.reply_text(f"🧾 Giornata {gnum} chiusa. Ora usa /esiti (o /aggiorna) per segnare chi ha perso.")


# ====== ESITI MANUALI ======
def _keyboard_esiti(losers: List[str]) -> InlineKeyboardMarkup:
    rows = []
    for u in USERNAME_TO_NAME:
        flag = "❌" if u in losers else "✅"
        rows.append([InlineKeyboardButton(text=f"{flag} {u}", callback_data=f"esiti_toggle|{u}")])
    rows.append([
        InlineKeyboardButton("✅ Conferma", callback_data="esiti_confirm"),
        InlineKeyboardButton("Annulla", callback_data="esiti_cancel")
    ])
    return InlineKeyboardMarkup(rows)


async def esiti_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    username = f"@{user.username}"
    if not is_admin(username):
        await update.message.reply_text("❌ Solo l'admin può impostare gli esiti.")
        return

    d = load_data()
    bets = d.get("bets", {})
    if not bets:
        await update.message.reply_text("❌ Nessuna giornata.")
        return
    g_key = str(max(int(k) for k in bets.keys()))
    if bets[g_key].get("status") != "finished":
        await update.message.reply_text("ℹ️ La giornata non è ancora *finished*. Usa /fine_giornata prima.")
        return

    context.chat_data["esiti"] = {"g_key": g_key, "losers": set()}
    await update.message.reply_text(
        f"Seleziona i PERDENTI della Giornata {g_key} (toggle sui nomi).",
        reply_markup=_keyboard_esiti([])
    )


async def esiti_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = context.chat_data.get("esiti")
    if not data:
        await query.edit_message_text("Sessione esiti non trovata. Rilancia /esiti.")
        return
    losers = data["losers"]

    if query.data.startswith("esiti_toggle|"):
        u = query.data.split("|", 1)[1]
        if u in losers: losers.remove(u)
        else: losers.add(u)
        await query.edit_message_reply_markup(reply_markup=_keyboard_esiti(list(losers)))
        return

    if query.data == "esiti_cancel":
        context.chat_data.pop("esiti", None)
        await query.edit_message_text("Operazione annullata.")
        return

    if query.data == "esiti_confirm":
        g_key = data["g_key"]
        losers_usernames = list(losers)
        applica_esiti_manuali(g_key, losers_usernames, USERNAME_TO_NAME)
        context.chat_data.pop("esiti", None)

        if losers_usernames:
            righe = [f"📌 Esiti G{g_key} salvati. Hanno perso:"]
            for u in losers_usernames: righe.append(f"- {u} (+1 punto, +5€)")
            await query.edit_message_text("\n".join(righe))
        else:
            await query.edit_message_text(f"📌 Esiti G{g_key} salvati. Nessun perdente 🎉")


async def soldi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    txt = "💰 *Situazione versamenti:*\n\n"
    for u, name in USERNAME_TO_NAME.items():
        debt = d["players"][name].get("debt", 0)
        paid = d["players"][name].get("paid", 0)
        status = "✅" if paid >= debt else "❌"
        txt += f"{u:<15} → Deve {debt}€, Ha versato {paid}€ {status}\n"
    await update.message.reply_text(txt, parse_mode="Markdown")


async def versa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if f"@{user.username}" not in ADMINS:
        await update.message.reply_text("❌ Solo l'admin può registrare versamenti.")
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
        d = load_data()
        d["players"][name].setdefault("paid", 0)
        d["players"][name]["paid"] += euro
        save_data(d)
        await update.message.reply_text(f"✅ Aggiunti {euro}€ a {username}.")
    except Exception:
        await update.message.reply_text("Formato: /versa @username <euro>  (es: /versa @Chris4rda 5)")


async def malloppo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    args = [a.lower() for a in context.args]
    solo = (args == ["solo", "giocate"]) or (args and args[0] in {"solo_giocate", "solo"})
    m = d["malloppo"]
    totale = m["giocate_sbagliate"] + m["penali_jolly"] + m["giocate_gruppo"]
    if solo:
        text = f"💰 *Malloppo solo giocate sbagliate:* {m['giocate_sbagliate']}€"
    else:
        text = (
            f"💰 *Malloppo Totale: {totale}€*\n\n"
            f"- Giocate sbagliate: {m['giocate_sbagliate']}€\n"
            f"- Penali jolly: {m['penali_jolly']}€\n"
            f"- Giocate di gruppo: {m['giocate_gruppo']}€"
        )
    await update.message.reply_text(text, parse_mode="Markdown")


async def giornate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    d = load_data()
    bets = d.get("bets", {})
    if not bets:
        await update.message.reply_text("❌ Nessuna giornata ancora registrata.")
        return
    resp = "📅 *Storico Giornate*\n\n"
    for g_key in sorted(bets.keys(), key=lambda x: int(x)):
        g = bets[g_key]
        if g.get("status") != "finished": continue
        losers = [u for u, b in g.get("bets", {}).items() if b.get("esito") == "persa"]
        if losers:
            resp += f"G{g_key}: {', '.join(losers)}\n"
        else:
            resp += f"G{g_key}: 🏆 Nessun errore!\n"
    await update.message.reply_text(resp, parse_mode="Markdown")


def main():
    print("ENV BOT_TOKEN presente:", bool(os.getenv("BOT_TOKEN")), flush=True)
    print("TOKEN length:", len(TOKEN), flush=True)
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("classifica", classifica))
    app.add_handler(CommandHandler("jolly", jolly))
    app.add_handler(CommandHandler("Jolly", jolly))  # alias
    app.add_handler(CommandHandler("gioca", gioca))
    app.add_handler(CommandHandler("modifica", modifica))
    app.add_handler(CommandHandler("estrai", estrai_cmd))
    app.add_handler(CommandHandler("inizio_giornata", inizio_giornata_cmd))
    app.add_handler(CommandHandler("fine_giornata", fine_giornata_cmd))
    app.add_handler(CommandHandler("esiti", esiti_cmd))
    app.add_handler(CommandHandler("aggiorna", esiti_cmd))  # alias di /esiti
    app.add_handler(CallbackQueryHandler(esiti_cb, pattern="^esiti_"))
    app.add_handler(CommandHandler("soldi", soldi))
    app.add_handler(CommandHandler("versa", versa))
    app.add_handler(CommandHandler("malloppo", malloppo))
    app.add_handler(CommandHandler("giornate", giornate))

    if WEBHOOK_URL:
        print(f"🚀 Imposto webhook su: {WEBHOOK_URL}")
        app.run_webhook(
            listen="0.0.0.0",
            port=int(os.environ.get("PORT", 8080)),
            webhook_url=WEBHOOK_URL,
            drop_pending_updates=True,
        )
    else:
        # 👉 assicura che NON ci sia un webhook attivo quando usi il polling
        import asyncio
        asyncio.get_event_loop().run_until_complete(
            app.bot.delete_webhook(drop_pending_updates=True)
        )

        print("▶️ Avvio in polling (WEBHOOK_URL non impostato)")
        app.run_polling(
            drop_pending_updates=True
        )

if __name__ == "__main__":
    main()

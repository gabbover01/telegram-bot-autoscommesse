# hotfix_g1.py
import json

DATA_FILE = "data.json"

LOSERS = ["Fruca", "Pavi", "Chri", "Gio", "Gargiu"]
NAME_TO_USERNAME = {
    "Effe": "@Federico_Lolli",
    "Fruca": "@Federico9499",
    "Gargiu": "@agggg21",
    "Gabbo": "@BTC_TonyStark",
    "Pavi": "@TheBu7cher",
    "Chri": "@Chris4rda",
    "Gio": "@JoLaFlame",
}

with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# 1) Crea la struttura 'bets' se manca
data.setdefault("bets", {})

# 2) Inserisci la G1 “finita” con chi ha sbagliato
gkey = "1"
data["bets"][gkey] = {
    "assignments": {},     # non servono per lo storico /giornate
    "leftover": [],
    "bets": {},
    "status": "finished",  # fondamentale per far vedere la giornata
    "settled": True
}

for name in LOSERS:
    username = NAME_TO_USERNAME[name]
    data["bets"][gkey]["bets"][username] = {
        "giocata": "import-manuale",
        "quota": 1.50,
        "jolly": False,
        "tipo_verifica": "combo_esito",
        "dati_verifica": {},
        "esito": "persa"     # fondamentale per apparire in /giornate
    }

# 3) Sistema i punti in classifica (1 ai cinque che hanno sbagliato)
for name in LOSERS:
    if name in data.get("players", {}):
        data["players"][name]["points"] = max(1, data["players"][name].get("points", 0))

# 4) (Opzionale) assicura che la lista “giornate” contenga la 1
#    Non è obbligatoria per /giornate, ma aiuta /estrai a scalare bene.
if isinstance(data.get("giornate"), list):
    if 1 not in data["giornate"]:
        data["giornate"].append(1)
else:
    # se era un dict tipo {"1": {...}}, lascialo com'è: /estrai calcola comunque la prossima
    pass

# 5) Non tocchiamo malloppo: nel tuo file è già a 25€ per G1

with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)

print("Hotfix completato: G1 marcata come finished, punti aggiornati, /giornate e /classifica OK.")

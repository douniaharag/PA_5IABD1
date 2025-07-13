import sys
import time
from datetime import datetime
import requests
import csv
from collections import defaultdict
from scripts.gather_keys_oauth2 import get_fitbit_client  # Assure-toi que ce chemin est correct

# === 1. Paramètres OAuth ===
CLIENT_ID = '23Q9LC'
CLIENT_SECRET = '038b7a1687ef74de477a063744e459ae'
REDIRECT_URI = 'http://127.0.0.1:5000/callback'

# === 2. Authentification Fitbit ===
print("🔒 Lancement du flow OAuth2...")
fb_client = get_fitbit_client(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
access_token = fb_client.client.session.token['access_token']
headers = {'Authorization': f'Bearer {access_token}'}
print("✅ Token obtenu !\n")

# === 3. Date cible ===
if len(sys.argv) > 1:
    try:
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d")
    except ValueError:
        print("❌ Format attendu : AAAA-MM-JJ")
        sys.exit(1)
else:
    target_date = datetime.now()

date_str = target_date.strftime('%Y-%m-%d')
print(f"📅 Récupération des données pour : {date_str}")

# === 4. Ressources intraday ===
resources = {
    'Steps': 'activities/steps',
    'Calories': 'activities/calories',
    'Distance': 'activities/distance',
    'Floors': 'activities/floors',
    'Elevation': 'activities/elevation',
    'HeartRate': 'activities/heart',
    'MinutesSedentary': 'activities/minutesSedentary',
    'MinutesLightlyActive': 'activities/minutesLightlyActive',
    'MinutesFairlyActive': 'activities/minutesFairlyActive',
    'MinutesVeryActive': 'activities/minutesVeryActive',
}

# === 5. Récupération des données Intraday ===
data_intraday = {}
for label, path in resources.items():
    print(f"→ {label} intraday...")
    url_day = f'https://api.fitbit.com/1/user/-/{path}/date/{date_str}/1d/1min.json'
    wait = 1
    for attempt in range(1, 6):
        resp = requests.get(url_day, headers=headers)
        if resp.status_code == 429:
            print(f"   ⚠️ Trop de requêtes, attente {wait}s...")
            time.sleep(wait)
            wait *= 2
            continue
        elif resp.status_code == 403:
            print("   🚫 Accès interdit pour cette ressource")
            break
        elif resp.status_code == 400:
            print("   ⚠️ Ressource non disponible pour aujourd'hui")
            break
        elif resp.status_code != 200:
            print(f"   ❌ Erreur {resp.status_code}")
            break

        js = resp.json()
        intraday_k = next((k for k in js if k.endswith('-intraday')), None)
        if intraday_k:
            data_intraday[label] = js[intraday_k]['dataset']
        else:
            data_intraday[label] = []
        break
    else:
        print(f"   ❌ 5 échecs pour {label}")
        data_intraday[label] = []

# === 6. Sauvegarde des données minute par minute ===
table = defaultdict(dict)
for label, entries in data_intraday.items():
    for entry in entries:
        time_key = entry['time']
        table[time_key][label] = entry['value']

csv_filename = f'intraday_{date_str}.csv'
with open(csv_filename, 'w', newline='', encoding='utf-8') as f_csv:
    writer = csv.writer(f_csv)
    header = ['time'] + list(resources.keys())
    writer.writerow(header)
    for t in sorted(table.keys()):
        row = [t] + [table[t].get(label, '') for label in resources.keys()]
        writer.writerow(row)

print(f"✅ Données intraday sauvegardées dans {csv_filename}")

# === 7. Récupération des données de sommeil ===
print(f"\n😴 Récupération du sommeil...")
url_sleep = f'https://api.fitbit.com/1.2/user/-/sleep/date/{date_str}.json'
sleep_resp = requests.get(url_sleep, headers=headers)

sleep_summary = {}
if sleep_resp.status_code == 200:
    sleep_data = sleep_resp.json()
    if sleep_data.get("sleep"):
        sleep_main = sleep_data["sleep"][0]
        levels = sleep_main.get("levels", {}).get("summary", {})
        sleep_summary = {
            "date": date_str,
            "totalMinutesAsleep": sleep_main.get("minutesAsleep", 0),
            "totalTimeInBed": sleep_main.get("timeInBed", 0),
            "sleepEfficiency": sleep_main.get("efficiency", 0),
            "startTime": sleep_main.get("startTime", ""),
            "endTime": sleep_main.get("endTime", ""),
            "deepSleep": levels.get("deep", {}).get("minutes", 0),
            "lightSleep": levels.get("light", {}).get("minutes", 0),
            "remSleep": levels.get("rem", {}).get("minutes", 0),
            "wake": levels.get("wake", {}).get("minutes", 0)
        }
        print("✅ Sommeil récupéré")
    else:
        print("⚠️ Aucune donnée de sommeil disponible")
else:
    print(f"❌ Erreur {sleep_resp.status_code} lors de la récupération du sommeil")

# === 8. Sauvegarde sommeil ===
if sleep_summary:
    sleep_filename = f'sleep_{date_str}.csv'
    with open(sleep_filename, 'w', newline='', encoding='utf-8') as f_csv:
        writer = csv.DictWriter(f_csv, fieldnames=sleep_summary.keys())
        writer.writeheader()
        writer.writerow(sleep_summary)
    print(f"✅ Données de sommeil sauvegardées dans {sleep_filename}")

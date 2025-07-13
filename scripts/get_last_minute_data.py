import time
from datetime import datetime
import requests
from collections import defaultdict
from scripts.gather_keys_oauth2 import get_fitbit_client  # Vérifie ce chemin

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

# === 3. Date du jour ===
target_date = datetime.now()
date_str = target_date.strftime('%Y-%m-%d')
print(f"📅 Données du : {date_str}")

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

# === 5. Récupération des dernières valeurs ===
print("\n📊 Données biométriques de la dernière minute :")
data_last_minute = {}
latest_time = None

for label, path in resources.items():
    print(f"→ {label}...")
    url = f'https://api.fitbit.com/1/user/-/{path}/date/{date_str}/1d/1min.json'

    for attempt in range(5):
        resp = requests.get(url, headers=headers)
        if resp.status_code == 429:
            print(f"   ⚠️ Trop de requêtes. Attente {2 ** attempt}s...")
            time.sleep(2 ** attempt)
            continue
        elif resp.status_code in (403, 400):
            print(f"   ❌ {resp.status_code} : accès refusé ou non disponible")
            break
        elif resp.status_code != 200:
            print(f"   ❌ Erreur {resp.status_code}")
            break

        js = resp.json()
        intraday_key = next((k for k in js if k.endswith("-intraday")), None)
        if intraday_key:
            dataset = js[intraday_key]["dataset"]
            if dataset:
                last_entry = dataset[-1]
                data_last_minute[label] = last_entry["value"]
                if not latest_time:
                    data_last_minute["time"] = last_entry["time"]
                    latest_time = last_entry["time"]
            else:
                data_last_minute[label] = None
        break
    else:
        data_last_minute[label] = None

# === 6. Affichage normal ===
for k, v in data_last_minute.items():
    if k != "time":
        print(f"   {k} : {v}")
print(f"\n🕒 Heure de la dernière mesure : {date_str} {data_last_minute.get('time', '--:--')}")

# === 7. Récupération des données de sommeil ===
print("\n😴 Données de sommeil :")
url_sleep = f'https://api.fitbit.com/1.2/user/-/sleep/date/{date_str}.json'
sleep_resp = requests.get(url_sleep, headers=headers)

main_sleep = {}
levels = {}
if sleep_resp.status_code == 200:
    sleep_data = sleep_resp.json()
    if sleep_data.get("sleep"):
        main_sleep = sleep_data["sleep"][0]
        levels = main_sleep.get("levels", {}).get("summary", {})
        print(f"   Total sommeil : {main_sleep.get('minutesAsleep', 0)} min")
        print(f"   Efficacité : {main_sleep.get('efficiency', 0)}%")
        print(f"   Profond : {levels.get('deep', {}).get('minutes', 0)} min")
        print(f"   REM : {levels.get('rem', {}).get('minutes', 0)} min")
        print(f"   Léger : {levels.get('light', {}).get('minutes', 0)} min")
        print(f"   Réveillé : {levels.get('wake', {}).get('minutes', 0)} min")
    else:
        print("⚠️ Aucune donnée de sommeil disponible")
else:
    print(f"❌ Erreur {sleep_resp.status_code} pour les données de sommeil")

# === 8. Format compact pour IA ===
formatted_output = (
    f"date:{date_str} "
    f"time:{data_last_minute.get('time', '--:--:--')} "
    f"bpm:{data_last_minute.get('HeartRate', 0)} "
    f"steps:{data_last_minute.get('Steps', 0)} "
    f"cal:{data_last_minute.get('Calories', 0)} "
    f"sedentary:{data_last_minute.get('MinutesSedentary', 0)} "
    f"asleep:{main_sleep.get('minutesAsleep', 0)} "
    f"eff:{main_sleep.get('efficiency', 0)} "
    f"rem:{levels.get('rem', {}).get('minutes', 0)} "
    f"deep:{levels.get('deep', {}).get('minutes', 0)} "
    f"wake:{levels.get('wake', {}).get('minutes', 0)}"
)

print("\n🧾 Format compact pour IA :")
print(formatted_output)

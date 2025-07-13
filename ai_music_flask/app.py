import os
import sys
import csv
import datetime
import requests
import subprocess
from flask import Flask, render_template, jsonify, request
from shutil import copyfile
from scripts.gather_keys_oauth2 import get_fitbit_client

app = Flask(__name__)

CLIENT_ID = '23Q9LC'
CLIENT_SECRET = '038b7a1687ef74de477a063744e459ae'
REDIRECT_URI = 'http://127.0.0.1:5000/callback'

print("🔒 Initialisation du client Fitbit...")
fb_client = get_fitbit_client(CLIENT_ID, CLIENT_SECRET, REDIRECT_URI)
print("✅ Client Fitbit prêt.")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/callback")
def callback():
    # Traiter le retour OAuth2 ici si besoin
    return "<h3>✅ Connexion réussie ! Vous pouvez revenir à l'accueil.</h3>"


@app.route("/biometrics")
def biometrics():
    token = fb_client.client.session.token
    headers = {'Authorization': f"Bearer {token['access_token']}"}
    today = datetime.datetime.now().strftime("%Y-%m-%d")

    resources = {
        'Steps': 'activities/steps',
        'Calories': 'activities/calories',
        'HeartRate': 'activities/heart',
        'MinutesSedentary': 'activities/minutesSedentary',
    }

    data = {}
    latest_time = None

    for label, path in resources.items():
        url = f"https://api.fitbit.com/1/user/-/{path}/date/{today}/1d/1min.json"
        resp = requests.get(url, headers=headers)
        if resp.status_code == 200:
            intraday = next((v for k, v in resp.json().items() if 'intraday' in k), {}).get('dataset', [])
            if intraday:
                last = intraday[-1]
                data[label] = last['value']
                latest_time = last['time']

    sleep_url = f"https://api.fitbit.com/1.2/user/-/sleep/date/{today}.json"
    sleep_resp = requests.get(sleep_url, headers=headers)
    sleep_summary = {}
    if sleep_resp.status_code == 200 and sleep_resp.json().get('sleep'):
        main_sleep = sleep_resp.json()['sleep'][0]
        summary = main_sleep['levels']['summary']
        sleep_summary = {
            'asleep': main_sleep.get('minutesAsleep', 0),
            'eff': main_sleep.get('efficiency', 0),
            'rem': summary.get('rem', {}).get('minutes', 0),
            'deep': summary.get('deep', {}).get('minutes', 0),
            'wake': summary.get('wake', {}).get('minutes', 0),
        }

    final_data = {
        'date': today,
        'time': latest_time,
        'bpm': data.get('HeartRate', '-'),
        'cal': data.get('Calories', '-'),
        'sedentary': data.get('MinutesSedentary', '-'),
        'steps': data.get('Steps', '-'),
        **sleep_summary
    }

    print("📥 Données Fitbit envoyées :", final_data)
    return jsonify(final_data)

@app.route("/generate_music", methods=["POST"])
def generate_music():
    d = request.json
    biometric_input = " ".join(f"{k}:{v}" for k, v in d.items())

    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "..", "scripts", "generate_music_prompt.py")

    proc = subprocess.run(
        [sys.executable, script_path, biometric_input],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8"
    )

    print("=" * 60)
    print("🎧 Résultat du script :")
    print(proc.stdout)
    print("=" * 60)

    if proc.returncode != 0:
        return jsonify({"status": "error", "message": "Erreur dans le script Python"})

    # Extraire le prompt et le fichier généré
    prompt, filename = "", ""
    for line in proc.stdout.splitlines():
        if line.startswith("[PROMPT]"):
            prompt = line.replace("[PROMPT]", "").strip()
        if line.startswith("[FILENAME]"):
            filename = line.replace("[FILENAME]", "").strip()

    if not filename:
        return jsonify({"status": "error", "message": "Fichier musique non généré"})

    # Déplacer le .wav
    source_path = os.path.join(base_dir, "..", "scripts", "outputs_son", filename)
    target_audio_dir = os.path.join(base_dir, "static", "audio")
    os.makedirs(target_audio_dir, exist_ok=True)
    destination = os.path.join(target_audio_dir, filename)
    if not os.path.exists(destination):
        copyfile(source_path, destination)

    url = f"/static/audio/{filename}"
    print("✅ Prompt extrait :", prompt)
    return jsonify({
        "status": "success",
        "filename": filename,
        "url": url,
        "prompt": prompt,
        "input_text": biometric_input
    })

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    print("📩 /submit_feedback déclenché")  # AJOUT
    data = request.json
    input_text = data.get("input_text", "").strip()
    music_prompt = data.get("music_prompt", "").strip()
    score = data.get("score", None)

    print("📩 Feedback reçu :", data)
    print("📥 Input :", input_text)
    print("🎼 Prompt :", music_prompt)
    print("⭐ Note :", score)

    if not input_text or not music_prompt or score is None:
        print("❌ Champs manquants.")
        return jsonify({"status": "error", "message": "Champs manquants"})

    # Chemin du dossier feedback/
    feedback_dir = os.path.join(os.path.dirname(__file__), "feedback")
    os.makedirs(feedback_dir, exist_ok=True)
    filepath = os.path.join(feedback_dir, "user_feedback.csv")

    file_exists = os.path.isfile(filepath)
    try:
        with open(filepath, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["input_text", "music_prompt", "score"])
            writer.writerow([input_text, music_prompt, score])
        print("✅ Feedback sauvegardé dans :", filepath)
        return jsonify({"status": "success", "message": "Feedback enregistré ✅"})
    except Exception as e:
        print("❌ Erreur lors de l’écriture du fichier :", e)
        return jsonify({"status": "error", "message": "Erreur en sauvegardant le feedback"})


@app.route("/heart_history")
def heart_history():
    return last_60min_values("activities/heart")

@app.route("/steps_history")
def steps_history():
    return last_60min_values("activities/steps")

@app.route("/calories_history")
def calories_history():
    return last_60min_values("activities/calories")

@app.route("/sedentary_history")
def sedentary_history():
    return last_60min_values("activities/minutesSedentary")

def last_60min_values(path):
    token = fb_client.client.session.token
    headers = {'Authorization': f"Bearer {token['access_token']}"}
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    url = f"https://api.fitbit.com/1/user/-/{path}/date/{today}/1d/1min.json"
    resp = requests.get(url, headers=headers)
    if resp.status_code != 200:
        return jsonify([])
    dataset = next((v for k, v in resp.json().items() if 'intraday' in k), {}).get('dataset', [])
    return jsonify(dataset[-60:] if len(dataset) >= 60 else dataset)

if __name__ == "__main__":
    print("=== Lancement du serveur Flask sur port 5000 ===")
    app.run(host="127.0.0.1", port=5000, debug=False)

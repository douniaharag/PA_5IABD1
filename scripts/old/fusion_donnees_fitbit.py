import pandas as pd
from glob import glob
from datetime import datetime
import os

# === 1. Fusion des fichiers INTRADAY ===
intraday_files = sorted(glob("Dataset_FitBit/Intraday/intraday_2025-05-*.csv"))
intraday_dfs = []

all_intraday_cols = [
    'time', 'Steps', 'Calories', 'Distance', 'Floors', 'Elevation',
    'HeartRate', 'MinutesSedentary', 'MinutesLightlyActive',
    'MinutesFairlyActive', 'MinutesVeryActive'
]

for path in intraday_files:
    df = pd.read_csv(path)
    date_str = path.split('_')[-1].replace('.csv', '')
    df['date'] = datetime.strptime(date_str, "%Y-%m-%d").date()

    for col in all_intraday_cols:
        if col not in df.columns:
            df[col] = pd.NA

    df = df[['date', 'time'] + all_intraday_cols[1:]]
    intraday_dfs.append(df)

intraday_all = pd.concat(intraday_dfs, ignore_index=True)

# Créer dossier si besoin
os.makedirs("Dataset_outputs", exist_ok=True)
intraday_all.to_csv("Dataset_outputs/intraday_merged.csv", index=False)
print("✅ Fichier Dataset_outputs/intraday_merged.csv généré")

# === 2. Fusion des fichiers SLEEP ===
sleep_files = sorted(glob("Dataset_FitBit/Sleep/sleep_2025-05-*.csv"))
sleep_dfs = []

for path in sleep_files:
    df = pd.read_csv(path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date
        sleep_dfs.append(df)

sleep_all = pd.concat(sleep_dfs, ignore_index=True)
sleep_all.to_csv("Dataset_outputs/sleep_merged.csv", index=False)
print("✅ Fichier Dataset_outputs/sleep_merged.csv généré")

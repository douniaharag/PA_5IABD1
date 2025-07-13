import pandas as pd
import openai
from tqdm import tqdm
import os

openai.api_key = "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"  # Ta clé API

# Mets le bon chemin si tu exécutes ce script ailleurs
df = pd.read_csv("../../Dataset_outputs/old/manual_music_prompt_dataset.csv")
df["music_prompt"] = ""

def is_musical(text):
    text = text.lower()
    if "bpm" in text or "steps" in text or "cal" in text or "date:" in text:
        return False
    if len(text.split()) < 4 or len(text.split()) > 9:
        return False
    return True

def gpt4_music_prompt(biometric_data):
    system_msg = (
        "You are an assistant that translates physiological data into concise musical ambiances. "
        "Given biometric inputs (heart rate, steps, calories, sleep phases), imagine the mood or energy "
        "and suggest a 5-7 word music style/atmosphere (e.g. 'slow ambient tones with warm textures'). "
        "Don't use emotion labels, don't explain. Just output the musical suggestion."
    )
    user_msg = f"Biometric input: {biometric_data}"
    for _ in range(3):
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",  # <- C’EST ICI QU’ON CORRIGE
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=16,
                temperature=0.8,
                top_p=0.9,
                n=1,
            )
            text = response['choices'][0]['message']['content'].strip().strip(".").replace("\n", " ")
            if is_musical(text):
                return text
        except Exception as e:
            print(f"Erreur GPT-4o: {e}")
    return "relaxing ambient textures"

for i, row in tqdm(df.iterrows(), total=len(df)):
    bio = row["input_text"]
    df.at[i, "music_prompt"] = gpt4_music_prompt(bio)

output_path = "../../Dataset_outputs/music_prompt_dataset_strict_gpt4.csv"
os.makedirs("Dataset_outputs", exist_ok=True)
df.to_csv(output_path, index=False)

print(f"✅ Dataset musical strict généré via GPT-4o : {output_path}")

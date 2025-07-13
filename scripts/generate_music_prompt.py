#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import warnings
from datetime import datetime
import requests
import torch
from transformers import logging as transformers_logging, T5Tokenizer, T5ForConditionalGeneration

# Nouveau : support LoRA
from peft import PeftModel

warnings.filterwarnings("ignore")
transformers_logging.set_verbosity_error()

# Lecture des données passées par argument
if len(sys.argv) < 2:
    raise RuntimeError("Usage: generate_music_prompt.py \"bpm:.. steps:.. cal:..\"")

raw = sys.argv[1]
valid_keys = {"bpm", "steps", "cal", "sedentary", "asleep", "eff", "rem", "deep", "wake"}
bio_entries = []
for tok in raw.split():
    if ":" in tok:
        k, v = tok.split(":", 1)
        if k in valid_keys:
            bio_entries.append(f"{k}:{v}")
biometric_input = " ".join(bio_entries)

print(f"🧾 Données filtrées : {biometric_input}")

# === Chargement du modèle de base ===
print("🤖 Chargement de Flan-T5...")
base_dir = os.path.dirname(__file__)
model_base_path = os.path.join(base_dir, "..", "model", "trained_flan_small_3layers")
tokenizer = T5Tokenizer.from_pretrained(model_base_path)
model = T5ForConditionalGeneration.from_pretrained(model_base_path)

# === Intégration automatique du dernier LoRA ===
lora_root = os.path.join(base_dir, "..", "model")
lora_dirs = [d for d in os.listdir(lora_root) if d.startswith("lora_adapter_v")]
if lora_dirs:
    latest_lora = sorted(lora_dirs, key=lambda x: int(x.split("_v")[-1]))[-1]
    lora_path = os.path.join(lora_root, latest_lora)
    print(f"🎯 Adaptateur LoRA détecté : {latest_lora}")
    model = PeftModel.from_pretrained(model, lora_path)
else:
    print("⚠️ Aucun adaptateur LoRA trouvé, génération avec le modèle de base.")

device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device).eval()

inputs = tokenizer(f"Generate music style: {biometric_input}", return_tensors="pt", padding=True, truncation=True)
if torch.cuda.is_available():
    inputs = {k: v.to("cuda") for k, v in inputs.items()}

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=20,
        do_sample=True,
        temperature=0.8,
        top_p=0.9
    )
prompt = tokenizer.decode(outputs[0], skip_special_tokens=True).strip()
print(f"[PROMPT] {prompt}")

# Appel à MusicGen HF
print("🔗 Envoi du prompt à l’API MusicGen HF…")
HF_API = "https://douniaharag-fitmusicgen-api.hf.space/generate"
payload = {"prompt": prompt, "duration": 30}
try:
    resp = requests.post(HF_API, json=payload, timeout=300)
    resp.raise_for_status()
except Exception as e:
    print("❌ Erreur appel HF Space :", e)
    sys.exit(1)

# Sauvegarde du .wav
now = datetime.now()
filename = f"music_{now.strftime('%Y-%m-%d_%H-%M-%S')}.wav"
output_dir = os.path.join(base_dir, "outputs_son")
os.makedirs(output_dir, exist_ok=True)
filepath = os.path.join(output_dir, filename)

with open(filepath, "wb") as f:
    f.write(resp.content)

print(f"✅ Musique générée et sauvegardée dans : {filepath}")
print(f"[FILENAME] {filename}")

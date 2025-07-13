#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import torch
from transformers import T5Tokenizer, T5ForConditionalGeneration

def generate_music_prompt(input_str: str,
                          model_dir: str = "model/trained_flan_small_3layers",  # ✅ chemin local correct
                          max_input_length: int = 64,
                          max_output_length: int = 32) -> str:
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "6"

    # 1. Chargement du tokenizer et du modèle depuis le dossier local
    tokenizer = T5Tokenizer.from_pretrained(model_dir, local_files_only=True)
    model = T5ForConditionalGeneration.from_pretrained(model_dir, local_files_only=True)

    # 2. Assure-toi d'utiliser uniquement 3 couches
    model.encoder.block = torch.nn.ModuleList(model.encoder.block[:3])
    model.decoder.block = torch.nn.ModuleList(model.decoder.block[:3])
    model.config.num_layers = 3
    model.config.num_decoder_layers = 3

    # 3. Encodage de l'entrée
    input_ids = tokenizer.encode(input_str, return_tensors="pt", max_length=max_input_length, truncation=True)

    # 4. Génération
    output_ids = model.generate(input_ids, max_length=max_output_length, num_beams=4, early_stopping=True)
    output_str = tokenizer.decode(output_ids[0], skip_special_tokens=True)

    return output_str


# =============================
# 🚀 Test du modèle avec exemple Fitbit
# =============================
if __name__ == "__main__":
    input_biometrics = (
        "date:2025-05-18 time:00:09:00 bpm:75 steps:0 "
        "cal:1 sedentary:1 asleep:467 eff:95 rem:83 deep:55 wake:78"
    )

    print("🧪 Données d'entrée biométriques :")
    print(input_biometrics)

    prompt = generate_music_prompt(input_biometrics)

    print("\n🎵 Prompt musical généré :")
    print(prompt)

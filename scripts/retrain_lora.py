import os
import pandas as pd
import torch
from datasets import Dataset
from transformers import T5Tokenizer, T5ForConditionalGeneration, TrainingArguments, Trainer, DataCollatorForSeq2Seq

# 🔧 Patch pour éviter erreur clear_device_cache (Python 3.12 fix)
import transformers
transformers.trainer.clear_device_cache = lambda *args, **kwargs: None
os.environ["TRANSFORMERS_NO_ADVISORY_WARNINGS"] = "1"
os.environ["ACCELERATE_DISABLE_MAPPING_WARNINGS"] = "1"

from peft import get_peft_model, LoraConfig, TaskType, prepare_model_for_int8_training

# === 1. Chemins ===
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # racine projet
FEEDBACK_PATH = os.path.join(BASE_DIR,"ai_music_flask", "feedback", "user_feedback.csv")
MODEL_PATH = os.path.join(BASE_DIR, "model", "trained_flan_small_3layers")

# === 2. Charger les feedbacks utiles ===
df = pd.read_csv(FEEDBACK_PATH)
df = df[df["score"] < 3]
print(f"🧾 {len(df)} feedbacks avec score < 3 trouvés.")

if len(df) < 1:
    print("❌ Pas assez de feedbacks faibles pour réentraîner.")
    exit()

df = df[["input_text", "music_prompt"]].rename(columns={"input_text": "input", "music_prompt": "output"})
dataset = Dataset.from_pandas(df.reset_index(drop=True))

# === 3. Charger modèle + tokenizer ===
model = T5ForConditionalGeneration.from_pretrained(MODEL_PATH)
tokenizer = T5Tokenizer.from_pretrained(MODEL_PATH)

# === 4. Appliquer LoRA ===
peft_config = LoraConfig(
    task_type=TaskType.SEQ_2_SEQ_LM,
    r=8,
    lora_alpha=16,
    lora_dropout=0.1,
    bias="none"
)

model = prepare_model_for_int8_training(model)
model = get_peft_model(model, peft_config)

# === 5. Prétraitement des données ===
def preprocess(example):
    input_text = f"Generate music style: {example['input']}"
    model_inputs = tokenizer(input_text, max_length=64, padding="max_length", truncation=True)
    with tokenizer.as_target_tokenizer():
        labels = tokenizer(example["output"], max_length=16, padding="max_length", truncation=True)
    model_inputs["labels"] = labels["input_ids"]
    return model_inputs

tokenized_dataset = dataset.map(preprocess, remove_columns=dataset.column_names)

# === 6. Générer un nom de version auto (lora_adapter_vX) ===
model_base = os.path.join(BASE_DIR, "model")
existing = [d for d in os.listdir(model_base) if d.startswith("lora_adapter_v")]
version = 1 + max([int(d.split("_v")[-1]) for d in existing] + [0])
output_dir = os.path.join(model_base, f"lora_adapter_v{version}")
os.makedirs(output_dir, exist_ok=True)

# === 7. Entraînement rapide ===
training_args = TrainingArguments(
    output_dir=output_dir,
    per_device_train_batch_size=4,
    num_train_epochs=2,
    logging_steps=10,
    save_strategy="epoch",
    fp16=torch.cuda.is_available()
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_dataset,
    tokenizer=tokenizer,
    data_collator=DataCollatorForSeq2Seq(tokenizer)
)

print("🚀 Entraînement LoRA en cours...")
trainer.train()

# === 8. Sauvegarde ===
model.save_pretrained(output_dir)
tokenizer.save_pretrained(output_dir)

print(f"✅ Réentraînement terminé. Adaptateur LoRA sauvegardé dans : {output_dir}")

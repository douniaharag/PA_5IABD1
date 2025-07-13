import requests

# Attention à bien utiliser le nom complet de ton Space (avec le tiret)
API = "https://douniaharag-fitmusicgen-api.hf.space/generate"

payload = {
    "prompt": "Generate a calm piano melody",
    "duration": 12
}

resp = requests.post(API, json=payload)
if resp.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(resp.content)
    print("✅ Musique générée : output.wav")
else:
    print("❌ Erreur", resp.status_code, resp.text)

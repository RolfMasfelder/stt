import os

import requests
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

lm_studio_host = os.getenv("LM_STUDIO_HOST", "localhost")
lm_studio_port = os.getenv("LM_STUDIO_PORT", "1234")
lmstudio_url = f"http://{lm_studio_host}:{lm_studio_port}/v1/chat/completions"
model_name = os.getenv("LM_STUDIO_MODEL", "mistral-7b-instruct")

# Example transcript for testing
transcript = "Das ist ein Test-Transkript für die Zusammenfassung."

payload = {
    "model": model_name,
    "messages": [
        {"role": "system", "content": "Fasse Texte zusammen."},
        {"role": "user", "content": transcript},
    ],
}

response = requests.post(lmstudio_url, json=payload)
print(response.json()["choices"][0]["message"]["content"])

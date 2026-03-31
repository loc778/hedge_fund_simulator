import requests
import os
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")
# NEW — correct endpoint
API_URL = "https://router.huggingface.co/hf-inference/models/ProsusAI/finbert"
headers   = {"Authorization": f"Bearer {HF_TOKEN}"}

print(f"Token loaded: {HF_TOKEN[:10]}...")
print("Testing FinBERT connection...")

try:
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": "Reliance Industries reports strong quarterly profit"},
        timeout=30
    )
    print(f"Status code: {response.status_code}")
    print(f"Response: {response.text[:300]}")

except Exception as e:
    print(f"Connection failed: {e}")
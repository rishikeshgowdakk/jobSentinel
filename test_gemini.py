import os
from dotenv import load_dotenv
from google import genai
import json

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)
try:
    models = list(client.models.list())
    for m in models:
        print(m.name, m.supported_actions)
except Exception as e:
    print("Error:", e)

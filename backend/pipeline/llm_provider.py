import os
from abc import ABC, abstractmethod
from pathlib import Path
from dotenv import load_dotenv
import requests

load_dotenv()
env_path = Path(__file__).resolve().parent.parent / '.env'
if env_path.exists():
    load_dotenv(dotenv_path=env_path)


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> dict:
        pass


class GroqProvider(LLMProvider):
    def __init__(self):
        if "GROQ_API_KEY" not in os.environ:
            raise ValueError("GROQ_API_KEY not set")
        self.api_key = os.environ["GROQ_API_KEY"]
        self.model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    def generate(self, prompt: str) -> dict:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 120,
            "messages": [{"role": "user", "content": prompt}]
        }
        for attempt in range(5):
            resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            if resp.status_code == 429 and attempt < 4:
                import time
                time.sleep(2.5)
                continue
            break
        if resp.status_code != 200:
            raise RuntimeError(f"Request failed with status {resp.status_code}: {resp.text}")
        try:
            data = resp.json()
            return {
                "text": data["choices"][0]["message"]["content"].strip(),
                "input_tokens": data["usage"]["prompt_tokens"],
                "output_tokens": data["usage"]["completion_tokens"]
            }
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"Request failed: {e}")

import json, re
from google import genai
from google.genai import types
from ..config import settings

_client = None

def client():
    global _client
    if _client is None:
        if not settings.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY missing in .env")
        _client = genai.Client(api_key=settings.GEMINI_API_KEY)
    return _client

async def generate(prompt: str, json_mode: bool = False) -> str:
    cfg = types.GenerateContentConfig(response_mime_type="application/json") if json_mode else None
    r = await client().aio.models.generate_content(
        model=settings.GEMINI_MODEL, contents=prompt, config=cfg)
    return r.text or ""

def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            return json.loads(m.group(0))
        raise

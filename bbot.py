import os
import re
import sys
import requests
import feedparser
from gtts import gTTS
from google import genai

# 1. ENVIRONMENT CHECK
ENV_VARS = ["GEMINI_API_KEY", "GREEN_API_INSTANCE_ID", "GREEN_API_TOKEN", "WHATSAPP_PHONE_NUMBER"]
missing = [var for var in ENV_VARS if not os.getenv(var)]
if missing:
    sys.exit(f"❌ Missing environment variables: {', '.join(missing)}")

API_KEY, INSTANCE_ID, TOKEN, PHONE = (os.getenv(v) for v in ENV_VARS)

# 2. DATA FETCHERS
def get_weather(lat=50.8552, lon=0.5729):
    url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=auto"
    try:
        res = requests.get(url, timeout=5).json()
        return {
            "current": res.get("current", {}).get("temperature_2m"),
            "max": res.get("daily", {}).get("temperature_2m_max", [None])[0],
            "min": res.get("daily", {}).get("temperature_2m_min", [None])[0],
            "rain_mm": res.get("daily", {}).get("precipitation_sum", [None])[0]
        }
    except Exception as e:
        print(f"⚠️ Weather fetch failed: {e}")
        return "Weather data unavailable."

def get_news(url="https://feeds.bbci.co.uk/news/rss.xml", limit=5):
    try:
        feed = feedparser.parse(url)
        return [
            {
                "title": re.sub(r'<[^>]*>', '', e.title),
                "summary": re.sub(r'<[^>]*>', '', e.get("summary", ""))
            }
            for e in feed.entries[:limit]
        ]
    except Exception as e:
        print(f"⚠️ News fetch failed: {e}")
        return "News unavailable."

# 3. SCRIPT GENERATION
prompt = f"""You are a witty, sarcastic, deadpan commentator speaking to 'Dude'.
Live Data:
- Weather: {get_weather()}
- Headlines: {get_news()}

Write a 250-300 word broadcast script (spoken text only) formatted as:
1. Deadpan intro. 2. Hastings weather summary. 3. Commentary on 2 news stories.
4. Quick joke. 5. Non-technical maths fact. 6. Non-technical science fact.
7. Philosophical takeaway. 8. Upbeat sign-off."""

try:
    client = genai.Client(api_key=API_KEY)
    script_text = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt
    ).text
except Exception as e:
    sys.exit(f"❌ Gemini Generation Error: {e}")

# 4. AUDIO CONVERSION & WHATSAPP DELIVERY
audio_file = 'radio_briefing.mp3'
gTTS(text=script_text, lang='en', tld='co.uk').save(audio_file)

upload_url = f"https://media.green-api.com/waInstance{INSTANCE_ID}/sendFileByUpload/{TOKEN}"
chat_id = f"{PHONE.strip('+')}@c.us"

try:
    with open(audio_file, "rb") as f:
        res = requests.post(
            upload_url,
            data={'chatId': chat_id, 'fileName': audio_file},
            files={'file': (audio_file, f, 'audio/mpeg')},
            timeout=30
        )
        res.raise_for_status()
    print("✅ Broadcast sent successfully.")
except Exception as e:
    print(f"❌ WhatsApp Delivery Failed: {e}")
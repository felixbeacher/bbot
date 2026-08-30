import os
import sys
import requests
import feedparser
from gtts import gTTS
from google import genai

# ==========================================
# 1. FETCH DATA (WEATHER & NEWS)
# ==========================================

def get_weather(lat=50.8552, lon=0.5729):
    """Fetches today's weather forecast for Hastings from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        current = data.get("current", {})
        daily = data.get("daily", {})
        return {
            "current_temp": current.get("temperature_2m"),
            "max_temp": daily.get("temperature_2m_max", [None])[0],
            "min_temp": daily.get("temperature_2m_min", [None])[0],
            "rain_mm": daily.get("precipitation_sum", [None])[0],
        }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return None

def get_news_headlines(rss_url="http://feeds.bbci.co.uk/news/rss.xml", limit=5):
    """Parses top headlines from BBC RSS feed."""
    try:
        feed = feedparser.parse(rss_url)
        articles = []
        for entry in feed.entries[:limit]:
            articles.append({
                "title": entry.title,
                "summary": entry.get("summary", "No summary available.")
            })
        return articles
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []

# ==========================================
# 2. LOAD CREDENTIALS FROM ENVIRONMENT
# ==========================================

gemini_api_key = os.getenv("GEMINI_API_KEY")
id_instance = os.getenv("GREEN_API_INSTANCE_ID")
token_instance = os.getenv("GREEN_API_TOKEN")
phone_number = os.getenv("WHATSAPP_PHONE_NUMBER")

if not all([gemini_api_key, id_instance, token_instance, phone_number]):
    print("❌ MISSING KEYS: Ensure GEMINI_API_KEY, GREEN_API_INSTANCE_ID, GREEN_API_TOKEN, and WHATSAPP_PHONE_NUMBER are set in environment variables.")
    sys.exit(1)

# ==========================================
# 3. GENERATE SCRIPT WITH GEMINI
# ==========================================

weather_data = get_weather()
news_data = get_news_headlines()

client = genai.Client(api_key=gemini_api_key)

prompt = f"""You are a witty, sarcastic, deadpan morning radio DJ speaking to Felix, who lives in Hastings, UK and likes to be addressed as 'dude'.

Here is the live data for today:
- Weather: {weather_data}
- Headlines: {news_data}

Write a broadcast script that is around 60 seconds long (approx. 130 words).
- Start with a punchy introduction and a joke.
- Give a brief weather summary for Hastings (mention if he will need an umbrella for the day).
- Cover 2 or 3 of the most interesting headlines in a conversational style.
- End with an upbeat sign-off and some provoking philosophical thought.
Do not include sound effect notes or visual cues—just write pure spoken text.
"""

print("Generating broadcast script...")
response = client.models.generate_content(
    model='gemini-3.6-flash',
    contents=prompt
)

print("\n--- YOUR MORNING RADIO SCRIPT ---")
print(response.text)

# ==========================================
# 4. CONVERT SCRIPT TO AUDIO (MP3)
# ==========================================

audio_file = 'radio_briefing.mp3'
tts = gTTS(text=response.text, lang='en', tld='co.uk')
tts.save(audio_file)
print(f"\nAudio successfully generated and saved to {audio_file}")

# ==========================================
# 5. SEND AUDIO FILE VIA WHATSAPP
# ==========================================

chat_id = f"{str(phone_number).strip('+')}@c.us"
url = f"https://media.green-api.com/waInstance{id_instance}/sendFileByUpload/{token_instance}"

print(f"Sending audio to {chat_id}...")

try:
    with open(audio_file, "rb") as f:
        files = {'file': (audio_file, f, 'audio/mpeg')}
        payload = {
            'chatId': chat_id,
            'fileName': audio_file
        }
        res = requests.post(url, data=payload, files=files)

        print(f"Status Code: {res.status_code}")
        print(f"Server Response: {res.text}")

        data = res.json()

        print("\n--- Delivery Details ---")
        print("✅ Success! Your audio file was processed by the server.")
        print(f"• Message ID: {data.get('idMessage')}")
        print(f"• Hosted File Link: {data.get('urlFile')}")

except FileNotFoundError:
    print(f"❌ ERROR: {audio_file} not found.")
except Exception as e:
    print(f"❌ ERROR sending message: {e}")

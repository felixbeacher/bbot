import os  # Provides functions for interacting with the OS, such as managing file paths and environment variables.
import sys  # System-specific parameters and functions used to interact closely with the Python interpreter.
import requests  # HTTP library used for sending network requests to retrieve web content or APIs.
import feedparser  # Parser library designed for fetching and extracting data from RSS and Atom news feeds.
from gtts import gTTS  # Google Text-to-Speech library used to convert written text into spoken audio files.
from google import genai  # client library for interacting with Gemini models.

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

response = client.models.generate_content(
    model='gemini-3.6-flash',
    contents=prompt
)

# ==========================================
# 4. CONVERT SCRIPT TO AUDIO (MP3)
# ==========================================

audio_file = 'radio_briefing.mp3'
tts = gTTS(text=response.text, lang='en', tld='co.uk')
tts.save(audio_file)

# ==========================================
# 5. SEND AUDIO FILE VIA WHATSAPP
# ==========================================

chat_id = f"{phone_number.strip('+')}@c.us"
url = f"https://media.green-api.com/waInstance{id_instance}/sendFileByUpload/{token_instance}"

try:
    with open(audio_file, "rb") as f:
        files = {'file': (audio_file, f, 'audio/mpeg')}
        payload = {
            'chatId': chat_id,
            'fileName': audio_file
        }
        res = requests.post(url, data=payload, files=files)
        res.raise_for_status()

except FileNotFoundError:
    print(f"❌ ERROR: {audio_file} not found.")
except Exception as e:
    print(f"❌ ERROR sending message: {e}")
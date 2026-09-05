import os  # Provides functions for interacting with the OS, such as managing file paths and environment variables.
import sys  # System-specific parameters and functions used to interact closely with the Python interpreter.
import requests  # HTTP library used for sending network requests to retrieve web content or APIs.
import feedparser  # Parser library designed for fetching and extracting data from RSS and Atom news feeds.
from gtts import gTTS  # Google Text-to-Speech library used to convert written text into spoken audio files.
from google import genai  # client library for interacting with Gemini models.
from tenacity import retry, stop_after_attempt, wait_exponential  # Adds automatic retry logic for API calls

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

prompt = f"""You are a witty, sarcastic, deadpan commentator speaking to 'Dude'.

Here is the live data for today:
- Weather: {weather_data}
- Headlines: {news_data}

Write a broadcast script of approximately 250 to 300 words (around 2 minutes spoken length). Do not include sound effect notes, stage directions, or visual cues—write pure spoken text only.

Structure the script in this order:
1. A punchy, deadpan introduction.
2. A brief weather summary for Hastings (mention if an umbrella is needed).
3. Conversational commentary on 2 of the most interesting headlines.
4. A quick joke.
5. An interesting, non-technical maths concept or fact.
6. An interesting, non-technical science concept or fact.
7. A brief, thought-provoking philosophical takeaway.
8. An upbeat sign-off.
"""

# Retries the request up to 3 times with exponentially increasing wait times if 503 occurs
@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def generate_broadcast():
    return client.models.generate_content(
        model='gemini-2.5-flash-lite',
        contents=prompt
    )

try:
    response = generate_broadcast()
except Exception as e:
    print(f"❌ Gemini API call failed after retries: {e}")
    sys.exit(1)

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

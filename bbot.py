import os  # Provides functions for interacting with the OS, such as managing file paths and environment variables.[cite: 2]
import sys  # System-specific parameters and functions used to interact closely with the Python interpreter.[cite: 2]
import requests  # HTTP library used for sending network requests to retrieve web content or APIs.[cite: 2]
import feedparser  # Parser library designed for fetching and extracting data from RSS and Atom news feeds.[cite: 2]
from gtts import gTTS  # Google Text-to-Speech library used to convert written text into spoken audio files.[cite: 2]
from google import genai  # client library for interacting with Gemini models.[cite: 2]
from tenacity import retry, stop_after_attempt, wait_exponential  # Adds automatic retry logic for API calls

# ==========================================
# 1. FETCH DATA (WEATHER & NEWS)
# ==========================================

def get_weather(lat=50.8552, lon=0.5729):
    """Fetches today's weather forecast for Hastings from Open-Meteo."""
    url = "https://api.open-meteo.com/v1/forecast"[cite: 2]
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m",
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": "auto"
    }[cite: 2]
    try:
        response = requests.get(url, params=params, timeout=10)[cite: 2]
        response.raise_for_status()[cite: 2]
        data = response.json()[cite: 2]
        current = data.get("current", {})[cite: 2]
        daily = data.get("daily", {})[cite: 2]
        return {
            "current_temp": current.get("temperature_2m"),
            "max_temp": daily.get("temperature_2m_max", [None])[0],
            "min_temp": daily.get("temperature_2m_min", [None])[0],
            "rain_mm": daily.get("precipitation_sum", [None])[0],
        }[cite: 2]
    except Exception as e:
        print(f"Error fetching weather: {e}")[cite: 2]
        return None[cite: 2]

def get_news_headlines(rss_url="http://feeds.bbci.co.uk/news/rss.xml", limit=5):
    """Parses top headlines from BBC RSS feed."""
    try:
        feed = feedparser.parse(rss_url)[cite: 2]
        articles = [][cite: 2]
        for entry in feed.entries[:limit]:[cite: 2]
            articles.append({
                "title": entry.title,
                "summary": entry.get("summary", "No summary available.")
            })[cite: 2]
        return articles[cite: 2]
    except Exception as e:
        print(f"Error fetching news: {e}")[cite: 2]
        return [][cite: 2]

# ==========================================
# 2. LOAD CREDENTIALS FROM ENVIRONMENT
# ==========================================

gemini_api_key = os.getenv("GEMINI_API_KEY")[cite: 2]
id_instance = os.getenv("GREEN_API_INSTANCE_ID")[cite: 2]
token_instance = os.getenv("GREEN_API_TOKEN")[cite: 2]
phone_number = os.getenv("WHATSAPP_PHONE_NUMBER")[cite: 2]

if not all([gemini_api_key, id_instance, token_instance, phone_number]):[cite: 2]
    print("❌ MISSING KEYS: Ensure GEMINI_API_KEY, GREEN_API_INSTANCE_ID, GREEN_API_TOKEN, and WHATSAPP_PHONE_NUMBER are set in environment variables.")[cite: 2]
    sys.exit(1)[cite: 2]

# ==========================================
# 3. GENERATE SCRIPT WITH GEMINI
# ==========================================

weather_data = get_weather()[cite: 2]
news_data = get_news_headlines()[cite: 2]

client = genai.Client(api_key=gemini_api_key)[cite: 2]

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
"""[cite: 2]

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

audio_file = 'radio_briefing.mp3'[cite: 2]
tts = gTTS(text=response.text, lang='en', tld='co.uk')[cite: 2]
tts.save(audio_file)[cite: 2]

# ==========================================
# 5. SEND AUDIO FILE VIA WHATSAPP
# ==========================================

chat_id = f"{phone_number.strip('+')}@c.us"[cite: 2]
url = f"https://media.green-api.com/waInstance{id_instance}/sendFileByUpload/{token_instance}"[cite: 2]

try:
    with open(audio_file, "rb") as f:[cite: 2]
        files = {'file': (audio_file, f, 'audio/mpeg')}[cite: 2]
        payload = {
            'chatId': chat_id,
            'fileName': audio_file
        }[cite: 2]
        res = requests.post(url, data=payload, files=files)[cite: 2]
        res.raise_for_status()[cite: 2]

except FileNotFoundError:
    print(f"❌ ERROR: {audio_file} not found.")[cite: 2]
except Exception as e:
    print(f"❌ ERROR sending message: {e}")[cite: 2]

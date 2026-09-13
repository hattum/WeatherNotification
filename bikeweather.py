# import os
# import requests

# # topic = os.environ["NTFY_TOPIC"]
# topic = "mytopic6723"

# requests.post(
#     f"https://ntfy.sh/{topic}",
#     data="🚲 Testmelding vanuit GitHub Actions!".encode(),
#     headers={
#         "Title": "Fietsweer test"
#     }
# )

import os
import requests
from datetime import datetime, timedelta, timezone


# ==========================================
# Configuration
# ==========================================

KNMI_API_KEY = os.environ["KNMI_API_KEY"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

KNMI_BASE_URL = "https://api.dataplatform.knmi.nl/edr/v1"

# Your location.
# We will replace these with your actual coordinates later.
LATITUDE = 52.0907
LONGITUDE = 5.1214


# ==========================================
# KNMI API
# ==========================================

def get_weather_data():
    """
    Get weather data from the KNMI API.
    The exact collection and parameters depend on
    the KNMI forecast dataset we choose.
    """

    collection = "10-minute-in-situ-meteorological-observations"

    url = (
        f"{KNMI_BASE_URL}/collections/"
        f"{collection}"
    )

    headers = {
        "Authorization": KNMI_API_KEY
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30
    )

    response.raise_for_status()

    return response.json()


# ==========================================
# Analyze weather
# ==========================================

def get_cycling_advice(rain_probability, precipitation):
    """
    Turn the weather data into a simple cycling recommendation.
    """

    if precipitation > 0.5:
        return "❌ Rain expected. I would not cycle."

    if rain_probability >= 60:
        return "⚠️ There is a good chance of rain. Bring a rain jacket."

    return "✅ Looks good! Perfect cycling weather."


# ==========================================
# Send notification
# ==========================================

def send_notification(message):
    """
    Send a push notification to your phone using ntfy.
    """

    url = f"https://ntfy.sh/{NTFY_TOPIC}"

    response = requests.post(
        url,
        data=message.encode("utf-8"),
        headers={
            "Title": "Cycling weather 🚲",
            "Priority": "default"
        },
        timeout=30
    )

    response.raise_for_status()


# ==========================================
# Main program
# ==========================================

def main():

    print("Checking the weather...")

    weather = get_weather_data()

    print("KNMI data received.")

    # These values are placeholders for now.
    # We will get the real values from the forecast data.
    rain_probability = 20
    precipitation = 0.0

    advice = get_cycling_advice(
        rain_probability,
        precipitation
    )

    message = f"""
🚲 Good morning!

Weather between 08:00 and 09:00:

🌧️ Rain probability: {rain_probability}%
💧 Expected precipitation: {precipitation} mm

{advice}
""".strip()

    print(message)

    send_notification(message)

    print("📱 Notification sent!")


if __name__ == "__main__":
    main()
```

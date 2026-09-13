import os
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests
import xarray as xr


# ============================================================
# Configuration
# ============================================================

KNMI_API_KEY = os.environ["KNMI_API_KEY"]
NTFY_TOPIC = os.environ["NTFY_TOPIC"]

BASE_URL = "https://api.dataplatform.knmi.nl/open-data/v1"

DATASET = "QRF-RT-SSh"
VERSION = "v2025"

# Utrecht city centre
LATITUDE = 52.0907
LONGITUDE = 5.1214

# Rain threshold
RAIN_THRESHOLD_MM = 0.1

# Local timezone
LOCAL_TIMEZONE = ZoneInfo("Europe/Amsterdam")


# ============================================================
# Messages
# ============================================================

MORNING_MESSAGES = [
    "Succes met werken vandaag!",
    "Een mooie werkdag gewenst!",
    "Zet 'm op vandaag!",
    "Veel succes vandaag en maak er wat moois van!",
    "Tijd om te knallen! Succes vandaag!",
]

AFTERNOON_MESSAGES = [
    "Nog even volhouden, je bent er bijna!",
    "De laatste loodjes! Zet 'm op!",
    "Bijna klaar voor vandaag! Nog even knallen!",
    "Je kunt het! Nog een paar uurtjes!",
    "Nog even doorbijten, daarna lekker naar huis!",
]


# ============================================================
# KNMI API
# ============================================================

def list_files():
    """Get available QRF forecast files."""

    url = (
        f"{BASE_URL}/datasets/"
        f"{DATASET}/versions/{VERSION}/files"
    )

    headers = {
        "Authorization": KNMI_API_KEY
    }

    params = {
        "maxKeys": 1000,
        "orderBy": "created",
        "sorting": "desc",
    }

    response = requests.get(
        url,
        headers=headers,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    data = response.json()

    return [file["filename"] for file in data["files"]]


def get_download_url(filename):
    """Get a temporary download URL for a KNMI file."""

    url = (
        f"{BASE_URL}/datasets/"
        f"{DATASET}/versions/{VERSION}/files/"
        f"{filename}/url"
    )

    headers = {
        "Authorization": KNMI_API_KEY
    }

    response = requests.get(
        url,
        headers=headers,
        timeout=30,
    )

    response.raise_for_status()

    return response.json()["temporaryDownloadUrl"]


def download_file(download_url, filename):
    """Download a KNMI NetCDF file."""

    response = requests.get(
        download_url,
        timeout=120,
    )

    response.raise_for_status()

    with open(filename, "wb") as file:
        file.write(response.content)


# ============================================================
# Forecast selection
# ============================================================

def get_target_time():
    """
    Determine the forecast period based on the current local time.

    Morning run:
        07:00 -> forecast for 08:00–09:00

    Afternoon run:
        15:00 -> forecast for 16:00–17:00
    """

    now = datetime.now(LOCAL_TIMEZONE)

    if now.hour < 12:
        target_start_hour = 8
        period = "morning"
    else:
        target_start_hour = 16
        period = "afternoon"

    target_local = datetime(
        now.year,
        now.month,
        now.day,
        target_start_hour,
        0,
        tzinfo=LOCAL_TIMEZONE,
    )

    target_utc = target_local.astimezone(timezone.utc)

    return target_local, target_utc, period


def find_forecast_file(files, target_utc):
    """
    Find the forecast file for the requested valid time.

    KNMI filenames contain the valid timestamp at the end.
    """

    timestamp = target_utc.strftime("%Y%m%d%H00")

    matches = [
        filename
        for filename in files
        if timestamp in filename
    ]

    if not matches:
        raise RuntimeError(
            f"No forecast file found for "
            f"{target_utc:%Y-%m-%d %H:%M} UTC"
        )

    return matches[0]


# ============================================================
# Forecast analysis
# ============================================================

def analyse_forecast(filename):
    """Analyse precipitation for Utrecht."""

    dataset = xr.open_dataset(filename)

    try:
        # Select the grid cell closest to Utrecht.
        utrecht = dataset.sel(
            latitude=LATITUDE,
            longitude=LONGITUDE,
            method="nearest",
        )

        actual_latitude = float(utrecht.latitude)
        actual_longitude = float(utrecht.longitude)

        precipitation = utrecht["tp"]

        # Remove dimensions that contain only one value.
        precipitation = precipitation.squeeze()

        # There should be 51 ensemble members.
        values = precipitation.values

        # Average precipitation over all ensemble members.
        average_rain = float(values.mean())

        # Percentage of ensemble members predicting >= threshold.
        rainy_members = (values >= RAIN_THRESHOLD_MM).sum()

        rain_probability = (
            rainy_members / len(values)
        ) * 100

        return {
            "latitude": actual_latitude,
            "longitude": actual_longitude,
            "average_rain": average_rain,
            "rain_probability": rain_probability,
            "ensemble_members": len(values),
        }

    finally:
        dataset.close()


# ============================================================
# ntfy
# ============================================================

def send_notification(
    target_local,
    period,
    average_rain,
    rain_probability,
):
    """Send the forecast to ntfy."""

    if period == "morning":
        motivational_message = random.choice(MORNING_MESSAGES)
        time_period = "08:00–09:00"
    else:
        motivational_message = random.choice(AFTERNOON_MESSAGES)
        time_period = "16:00–17:00"

    if rain_probability >= 50:
        title = "Regen verwacht"
        priority = "high"

        message = (
            f"Regen verwacht in Utrecht tussen {time_period}.\n"
            f"Regenkans: {rain_probability:.0f}%\n"
            f"Gemiddelde verwachting: {average_rain:.2f} mm\n\n"
            f"{motivational_message}"
        )

    else:
        title = "Goed fietsweer"
        priority = "default"

        message = (
            f"Waarschijnlijk geen regen in Utrecht "
            f"tussen {time_period}.\n"
            f"Regenkans: {rain_probability:.0f}%\n"
            f"Gemiddelde verwachting: {average_rain:.2f} mm\n\n"
            f"{motivational_message}"
        )

    response = requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": priority,
            "Tags": "bike",
        },
        timeout=30,
    )

    response.raise_for_status()

    print("Notification sent successfully!")


# ============================================================
# Main
# ============================================================

def main():

    print("Starting bike weather check...")
    print()

    target_local, target_utc, period = get_target_time()

    print(
        f"Forecast period: "
        f"{target_local:%Y-%m-%d %H:%M %Z}"
    )

    print(
        f"Target UTC: "
        f"{target_utc:%Y-%m-%d %H:%M}"
    )

    print(
        f"Run type: {period}"
    )

    print()
    print("Finding KNMI forecast...")

    files = list_files()

    filename = find_forecast_file(
        files,
        target_utc,
    )

    print(f"Forecast file: {filename}")

    try:
        print()
        print("Downloading forecast...")

        download_url = get_download_url(filename)

        download_file(
            download_url,
            filename,
        )

        print("Forecast downloaded.")

        print()
        print("Analysing Utrecht forecast...")

        result = analyse_forecast(filename)

        print()
        print("==============================")
        print("Utrecht forecast")
        print("==============================")

        print(
            f"Grid location: "
            f"{result['latitude']:.4f}, "
            f"{result['longitude']:.4f}"
        )

        print(
            f"Ensemble members: "
            f"{result['ensemble_members']}"
        )

        print(
            f"Average precipitation: "
            f"{result['average_rain']:.2f} mm"
        )

        print(
            f"Rain probability: "
            f"{result['rain_probability']:.0f}%"
        )

        print()

        send_notification(
            target_local,
            period,
            result["average_rain"],
            result["rain_probability"],
        )

    finally:
        # Always remove the downloaded KNMI file.
        if os.path.exists(filename):
            os.remove(filename)
            print(f"Deleted downloaded file: {filename}")


if __name__ == "__main__":
    main()

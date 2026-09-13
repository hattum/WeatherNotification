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
import xarray as xr


# ==========================================
# Configuration
# ==========================================

KNMI_API_KEY = os.environ["KNMI_OPEN_DATA_API"]

BASE_URL = "https://api.dataplatform.knmi.nl/open-data/v1"

DATASET = "QRF-RT-SSh"
VERSION = "v2025"


# ==========================================
# KNMI API helper
# ==========================================

def list_latest_file():
    """Find the most recently created QRF forecast file."""

    url = (
        f"{BASE_URL}/datasets/"
        f"{DATASET}/versions/{VERSION}/files"
    )

    headers = {
        "Authorization": KNMI_API_KEY
    }

    params = {
        "maxKeys": 1,
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

    if not data.get("files"):
        raise RuntimeError("No QRF forecast files were found.")

    filename = data["files"][0]["filename"]

    print(f"Latest KNMI file: {filename}")

    return filename


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
    """Download the NetCDF file."""

    print("Downloading forecast...")

    response = requests.get(
        download_url,
        timeout=120,
    )

    response.raise_for_status()

    with open(filename, "wb") as file:
        file.write(response.content)

    print(f"Downloaded: {filename}")


# ==========================================
# Inspect forecast
# ==========================================

def inspect_forecast(filename):
    """Print information about the NetCDF forecast."""

    print("\nOpening forecast...")

    dataset = xr.open_dataset(filename)

    print("\n================================")
    print("Forecast information")
    print("================================")

    print(dataset)

    print("\nVariables:")
    for variable in dataset.data_vars:
        print(f"  - {variable}")

    print("\nCoordinates:")
    for coordinate in dataset.coords:
        print(f"  - {coordinate}")


# ==========================================
# Main
# ==========================================

def main():

    print("🌦️ Starting bike weather check...")
    print()

    filename = list_latest_file()

    download_url = get_download_url(filename)

    download_file(
        download_url,
        filename,
    )

    inspect_forecast(filename)

    print("\n✅ KNMI forecast successfully downloaded!")


if __name__ == "__main__":
    main()


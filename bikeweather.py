import os
import requests

# topic = os.environ["NTFY_TOPIC"]
topic = mytopic6723

requests.post(
    f"https://ntfy.sh/{topic}",
    data="🚲 Testmelding vanuit GitHub Actions!".encode(),
    headers={
        "Title": "Fietsweer test"
    }
)

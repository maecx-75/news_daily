import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

NEWS90_URL = "https://www.servustv.com/de/page/AAH3UWY312CUTMV2HTHX/servus-nachrichten-in-90-sekunden-10-00-uhr"

data = {
    "title": "Servus Nachrichten in 90 Sekunden",
    "short_title": "Servus Nachrichten in 90 Sekunden",
    "full_title": "Servus Nachrichten in 90 Sekunden",
    "url": NEWS90_URL,
    "href": NEWS90_URL,
    "image": "news90.png",
    "thumbnail": "news90.png",

    "news90_title": "Servus Nachrichten in 90 Sekunden",
    "news90_link": NEWS90_URL,
    "news90_image": "news90.png",
    "news90_thumbnail": "news90.png",

    "ticker": "Servus Nachrichten in 90 Sekunden",
    "ticker90": "Servus Nachrichten in 90 Sekunden",
    "topmeldung90": "Servus Nachrichten in 90 Sekunden"
}

old = {}
if JSON_PATH.exists():
    try:
        old = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        old = {}

if "google_headlines" in old:
    data["google_headlines"] = old["google_headlines"]

JSON_PATH.write_text(
    json.dumps(data, ensure_ascii=False, indent=2),
    encoding="utf-8"
)

print("headlines.json aktualisiert")
print(data["news90_link"])

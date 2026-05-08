import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"

data = {
    "title": "Nachrichten in 90 Sekunden - Aktuelle Folge",
    "short_title": "Nachrichten in 90 Sekunden - Aktuelle Folge",
    "full_title": "Nachrichten in 90 Sekunden - Aktuelle Folge",
    "url": "https://www.servustv.com/de/page/AAH3UWY312CUTMV2HTHX/servus-nachrichten-in-90-sekunden-10-00-uhr",
    "href": "https://www.servustv.com/de/page/AAH3UWY312CUTMV2HTHX/servus-nachrichten-in-90-sekunden-10-00-uhr",
    "image": "news90.png",
    "thumbnail": "news90.png",

    "news90_title": "Nachrichten in 90 Sekunden - Aktuelle Folge",
    "news90_link": "https://www.servustv.com/de/page/AAH3UWY312CUTMV2HTHX/servus-nachrichten-in-90-sekunden-10-00-uhr",
    "news90_image": "news90.png",
    "ticker": "Nachrichten in 90 Sekunden - Aktuelle Folge",
    "ticker90": "Nachrichten in 90 Sekunden - Aktuelle Folge",
    "topmeldung90": "Nachrichten in 90 Sekunden - Aktuelle Folge"
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
print(data["news90_title"])
print(data["news90_link"])

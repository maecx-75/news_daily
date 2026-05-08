import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "news1920.json"

data = {
    "title": "Servus Nachrichten 19:20",
    "url": "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111/"
}

with open(JSON_PATH, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("news1920.json aktualisiert")

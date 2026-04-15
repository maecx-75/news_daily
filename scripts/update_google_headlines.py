import json
import xml.etree.ElementTree as ET
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
RSS_URL = "https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRFZxYUdjU0FtUmxHZ0pCVkNnQVAB?hl=de&gl=AT&ceid=AT:de"

def clean_title(title: str) -> str:
    return title.replace(" - Google News", "").strip()

resp = requests.get(RSS_URL, timeout=20, headers={"User-Agent":"Mozilla/5.0"})
resp.raise_for_status()
root = ET.fromstring(resp.content)
titles = []
for item in root.findall("./channel/item/title"):
    text = (item.text or "").strip()
    if text:
        titles.append(clean_title(text))
    if len(titles) == 3:
        break
if not titles:
    raise RuntimeError("Keine Google-News-Headlines gefunden.")

data = {}
if JSON_PATH.exists():
    data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
data["google_headlines"] = titles
JSON_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("Updated:", titles)

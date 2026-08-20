import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
SERIES_ID = "AA-1Y5RJCD1H2111"
SERIES_URL = f"https://www.servustv.com/de/page/{SERIES_ID}"
API_URL_AT = f"https://tv-api.redbull.com/products/dynamic/v5.2/stv/de/at/{SERIES_ID}"
KNOWN_ID = "AAUUYP6RNA3IVBL8FFPC"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
}


def walk(obj, path="root"):
    yield path, obj
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from walk(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for i, value in enumerate(obj):
            yield from walk(value, f"{path}[{i}]")


def compact(obj, limit=1800):
    try:
        return re.sub(r"\s+", " ", json.dumps(obj, ensure_ascii=False))[:limit]
    except Exception:
        return ""


def get_latest_news90():
    print(f"[INFO] GitHub-Runner kann geografisch in den USA liegen.")
    print(f"[INFO] Deshalb wird die Österreich-Ausgabe jetzt ausdrücklich erzwungen.")
    print(f"[INFO] Österreich-API: {API_URL_AT}")

    with sync_playwright() as p:
        request = p.request.new_context(
            extra_http_headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "application/json,text/plain,*/*",
                "Referer": SERIES_URL,
                "Origin": "https://www.servustv.com",
            }
        )

        response = request.get(API_URL_AT, timeout=60000)
        print(f"[DIAG] AT-API HTTP-Status: {response.status}")
        if not response.ok:
            print("[WARNUNG] Österreich-API konnte nicht geladen werden.")
            return

        try:
            data = response.json()
        except Exception as exc:
            print(f"[WARNUNG] API-Antwort ist kein JSON: {exc}")
            return

        raw = json.dumps(data, ensure_ascii=False)
        print(f"[DIAG] Antwortgröße: {len(raw)} Zeichen")
        print(f"[DIAG] Bekannte aktuelle ID {KNOWN_ID} in AT-API: {KNOWN_ID in raw}")
        print(f"[DIAG] Text '90 Sekunden' in AT-API: {'90 Sekunden' in raw}")
        print(f"[DIAG] Titel 'Massive Explosion' in AT-API: {'Massive Explosion' in raw}")

        hits = []
        for path, obj in walk(data):
            if not isinstance(obj, (dict, list)):
                continue
            blob = compact(obj, 12000)
            low = blob.lower()
            if KNOWN_ID.lower() in low or "massive explosion" in low or "servus nachrichten in 90 sekunden" in low:
                # Kleine/nahe Objekte sind für die Strukturdiagnose am wertvollsten.
                hits.append((len(blob), path, obj))

        hits.sort(key=lambda x: x[0])
        print(f"[DIAG] Relevante AT-API-Strukturtreffer: {len(hits)}")
        for i, (_, path, obj) in enumerate(hits[:12], 1):
            print(f"[AT-TREFFER {i}] Pfad: {path}")
            print(f"[AT-TREFFER {i}] Vorschau: {compact(obj)}")

        if KNOWN_ID in raw:
            print("[ERFOLG] Die richtige österreichische Datenquelle ist gefunden.")
            print("[INFO] Nächster Schritt: Aus genau dieser Struktur wird automatisch die erste 90-Sekunden-Karte gelesen.")
        else:
            print("[WARNUNG] Auch die AT-API enthält die bekannte aktuelle ID noch nicht.")

        print("[INFO] Diagnose abgeschlossen; headlines.json bleibt bei diesem Test unverändert.")
        request.dispose()


if __name__ == "__main__":
    get_latest_news90()

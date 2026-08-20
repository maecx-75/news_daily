import json
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
SERIES_ID = "AA-1Y5RJCD1H2111"
KNOWN_ID = "AAUUYP6RNA3IVBL8FFPC"
SERIES_URL = f"https://www.servustv.com/de/page/{SERIES_ID}"
API_BASE = "https://tv-api.redbull.com/products/dynamic/v5.2/stv/de"
MARKETS = ["us", "at", "de", "ch"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
}


def compact_text(value, limit=800):
    try:
        if isinstance(value, str):
            text = value
        else:
            text = json.dumps(value, ensure_ascii=False)
    except Exception:
        text = str(value)
    return re.sub(r"\s+", " ", text)[:limit]


def fetch_json(request, url, label):
    try:
        response = request.get(url, timeout=60000)
        body = response.text()
        print(f"[TEST] {label}: HTTP {response.status}, {len(body)} Zeichen")
        print(f"[TEST] {label} Rohantwort: {compact_text(body, 500)}")
        try:
            data = response.json()
        except Exception:
            data = None
        return response.status, body, data
    except Exception as exc:
        print(f"[WARNUNG] {label} fehlgeschlagen: {exc}")
        return 0, "", None


def scan_payload(label, body):
    low = body.lower()
    print(f"[SCAN] {label}: bekannte ID={KNOWN_ID.lower() in low}; Massive Explosion={'massive explosion' in low}; 90 Sekunden={'90 sekunden' in low}")


def get_latest_news90():
    print("[INFO] Diagnose der ServusTV/Red-Bull-Datenquelle.")
    print("[INFO] Wir testen dieselbe Serienseite und den bekannten aktuellen Beitrag über mehrere Markt-Codes.")

    with sync_playwright() as p:
        request = p.request.new_context(
            extra_http_headers={
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "application/json,text/plain,*/*",
                "Referer": SERIES_URL,
                "Origin": "https://www.servustv.com",
            }
        )

        print("\n=== SERIENSEITE ===")
        for market in MARKETS:
            url = f"{API_BASE}/{market}/{SERIES_ID}"
            status, body, _ = fetch_json(request, url, f"Serie /{market}/")
            scan_payload(f"Serie /{market}/", body)

        print("\n=== BEKANNTER AKTUELLER BEITRAG ===")
        found_market = None
        for market in MARKETS:
            url = f"{API_BASE}/{market}/{KNOWN_ID}"
            status, body, data = fetch_json(request, url, f"Beitrag /{market}/")
            scan_payload(f"Beitrag /{market}/", body)
            if status == 200 and len(body) > 500 and (
                "massive explosion" in body.lower()
                or KNOWN_ID.lower() in body.lower()
            ):
                found_market = market
                print(f"[ERFOLG] Bekannter aktueller Beitrag ist über Markt-Code /{market}/ verfügbar.")

        if found_market:
            print(f"[ERFOLG] Wahrscheinlich richtiger Markt-Code: {found_market}")
            print("[INFO] Im nächsten Schritt verwenden wir genau diesen Markt-Code für die Serienabfrage und lesen daraus den neuesten Beitrag.")
        else:
            print("[WARNUNG] Der bekannte aktuelle Beitrag wurde in keinem getesteten Markt-Code eindeutig gefunden.")
            print("[INFO] Dann prüfen wir als Nächstes die exakte API-Antwort der Browser-Netzwerkanfrage inklusive Parameter/Headers.")

        print("[INFO] Diagnose abgeschlossen; headlines.json bleibt unverändert.")
        request.dispose()


if __name__ == "__main__":
    get_latest_news90()

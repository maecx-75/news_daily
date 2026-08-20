import json
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
SERIES_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
SERIES_ID = "AA-1Y5RJCD1H2111"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
}


def load_existing_data():
    try:
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def normalize_article_url(url):
    if not url:
        return ""
    parsed = urlparse(urljoin(SERIES_URL, url))
    if parsed.netloc not in {"www.servustv.com", "servustv.com"}:
        return ""
    path = parsed.path.rstrip("/")
    if not re.fullmatch(r"/de/page/[A-Z0-9-]+", path, flags=re.I):
        return ""
    if SERIES_ID.lower() in path.lower():
        return ""
    return f"https://www.servustv.com{path}"


def walk_json(obj, found, context=""):
    """Findet in JSON-Antworten ServusTV-Beiträge und ihren Kontext."""
    if isinstance(obj, dict):
        # Objekt als kompakte Textdarstellung untersuchen.
        try:
            blob = json.dumps(obj, ensure_ascii=False)
        except Exception:
            blob = ""
        low = blob.lower()
        if "90 sekunden" in low or "nachrichten in 90" in low:
            urls = re.findall(r'https?://(?:www\.)?servustv\.com/(?:de/)?page/[A-Z0-9-]+[^"\\ ]*', blob, re.I)
            ids = re.findall(r'AA[A-Z0-9-]{8,}', blob, re.I)
            found.append({
                "context": context,
                "urls": urls[:10],
                "ids": ids[:20],
                "preview": blob[:1800],
            })
        for k, v in obj.items():
            walk_json(v, found, f"{context}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            walk_json(v, found, f"{context}[{i}]")


def get_latest_news90():
    print(f"[INFO] Öffne Servus-Nachrichten-Seite: {SERIES_URL}")
    api_hits = []
    network_urls = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1600, "height": 1200},
        )
        page = context.new_page()

        def on_response(response):
            try:
                url = response.url
                ctype = (response.headers.get("content-type") or "").lower()
                # Nur wahrscheinliche Datenquellen protokollieren.
                if any(x in url.lower() for x in ("api", "graphql", "content", "page", "playlist", "rail", "collection")):
                    if url not in network_urls:
                        network_urls.append(url)
                if "json" not in ctype:
                    return
                data = response.json()
                hits = []
                walk_json(data, hits, url)
                for hit in hits:
                    hit["source"] = url
                    api_hits.append(hit)
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(SERIES_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
            try:
                button = page.get_by_role("button", name=re.compile(label, re.I))
                if button.count() and button.first.is_visible():
                    button.first.click(timeout=1500)
                    page.wait_for_timeout(1200)
                    break
            except Exception:
                pass

        # Ganze relevante Seite laden, damit auch lazy-loaded API-Aufrufe stattfinden.
        for _ in range(12):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(700)

        page.wait_for_timeout(3000)

        print(f"[DIAG] Beobachtete mögliche Daten-Endpunkte: {len(network_urls)}")
        for u in network_urls[:40]:
            print(f"[NETZWERK] {u}")

        print(f"[DIAG] JSON-Treffer mit '90 Sekunden': {len(api_hits)}")
        for i, hit in enumerate(api_hits[:20], 1):
            print(f"[API-TREFFER {i}] Quelle: {hit.get('source','')}")
            print(f"[API-TREFFER {i}] Pfad: {hit.get('context','')}")
            if hit.get("urls"):
                print(f"[API-TREFFER {i}] URLs: {' | '.join(hit['urls'])}")
            if hit.get("ids"):
                print(f"[API-TREFFER {i}] IDs: {' | '.join(hit['ids'])}")
            preview = re.sub(r"\s+", " ", hit.get("preview", ""))[:1200]
            print(f"[API-TREFFER {i}] Vorschau: {preview}")

        # Zusätzlich prüfen, ob die bekannte aktuelle ID irgendwo in Netzwerk/DOM auftaucht.
        known_id = "AAUUYP6RNA3IVBL8FFPC"
        body_html = page.content()
        print(f"[DIAG] Bekannte aktuelle ID {known_id} im gerenderten DOM: {known_id in body_html}")
        print(f"[DIAG] Bekannte aktuelle ID in beobachteten Netzwerk-URLs: {any(known_id in u for u in network_urls)}")

        # WICHTIG: Dieser Diagnose-Lauf verändert headlines.json absichtlich nicht.
        print("[INFO] Diagnose abgeschlossen; headlines.json bleibt unverändert.")
        browser.close()


if __name__ == "__main__":
    get_latest_news90()

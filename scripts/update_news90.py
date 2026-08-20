import json
import re
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
SERIES_ID = "AA-1Y5RJCD1H2111"
KNOWN_ID = "AAUUYP6RNA3IVBL8FFPC"
KNOWN_TITLE = "Massive Explosion: Großeinsatz in NÖ"
SERIES_URL = f"https://www.servustv.com/de/page/{SERIES_ID}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
}


def one_line(text, limit=1200):
    text = re.sub(r"\s+", " ", text or "")
    return text[:limit]


def around(text, needle, radius=500):
    low = text.lower()
    pos = low.find(needle.lower())
    if pos < 0:
        return ""
    start = max(0, pos - radius)
    end = min(len(text), pos + len(needle) + radius)
    return one_line(text[start:end], 1400)


def interesting_domain(url):
    host = (urlparse(url).netloc or "").lower()
    return (
        host.endswith("servustv.com")
        or host.endswith("redbull.com")
        or host.endswith("redbull.tv")
    )


def get_latest_news90():
    print("[INFO] Tiefendiagnose der echten ServusTV-Datenquelle.")
    print(f"[INFO] Kontrollbeitrag: {KNOWN_TITLE} ({KNOWN_ID})")
    print(f"[INFO] Öffne: {SERIES_URL}")

    requests_seen = []
    responses_seen = []
    hits = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1600, "height": 1400},
        )
        page = context.new_page()

        def on_request(req):
            try:
                if not interesting_domain(req.url):
                    return
                low = req.url.lower()
                if any(k in low for k in ("api", "dynamic", "product", "collection", "rail", "playlist", "page", "_rsc")):
                    requests_seen.append((req.method, req.url, req.post_data or ""))
            except Exception:
                pass

        def on_response(resp):
            try:
                if not interesting_domain(resp.url):
                    return
                ctype = (resp.headers.get("content-type") or "").lower()
                if not any(k in ctype for k in ("json", "text", "javascript", "x-component")):
                    return

                body = resp.text()
                responses_seen.append((resp.status, resp.url, ctype, len(body)))
                low = body.lower()

                matched = []
                for needle in (KNOWN_ID, "massive explosion", "90 sekunden", "servus nachrichten in 90 sekunden"):
                    if needle.lower() in low:
                        matched.append(needle)

                if matched:
                    snippets = []
                    for needle in matched[:3]:
                        snip = around(body, needle)
                        if snip:
                            snippets.append(f"{needle}: {snip}")
                    hits.append((resp.url, ctype, matched, snippets))
            except Exception:
                pass

        page.on("request", on_request)
        page.on("response", on_response)

        page.goto(SERIES_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
            try:
                btn = page.get_by_role("button", name=re.compile(label, re.I))
                if btn.count() and btn.first.is_visible():
                    btn.first.click(timeout=1500)
                    page.wait_for_timeout(1200)
                    break
            except Exception:
                pass

        # Lazy-loading und weitere Rails/Karten auslösen.
        for _ in range(14):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(700)
            try:
                more = page.get_by_text(re.compile(r"Mehr Einträge anzeigen|Mehr anzeigen", re.I))
                if more.count() and more.first.is_visible():
                    more.first.click(timeout=1800)
                    page.wait_for_timeout(1200)
            except Exception:
                pass

        page.wait_for_timeout(3500)

        print(f"[DIAG] Relevante Requests: {len(requests_seen)}")
        for i, (method, url, post) in enumerate(requests_seen[:80], 1):
            print(f"[REQUEST {i}] {method} {url}")
            if post:
                print(f"[REQUEST {i}] POST: {one_line(post, 900)}")

        print(f"[DIAG] Relevante Responses: {len(responses_seen)}")
        for i, (status, url, ctype, size) in enumerate(responses_seen[:80], 1):
            print(f"[RESPONSE {i}] HTTP {status} | {size} Zeichen | {ctype} | {url}")

        print(f"[DIAG] Inhaltstreffer: {len(hits)}")
        for i, (url, ctype, matched, snippets) in enumerate(hits[:30], 1):
            print(f"[TREFFER {i}] Quelle: {url}")
            print(f"[TREFFER {i}] Content-Type: {ctype}")
            print(f"[TREFFER {i}] Gefunden: {' | '.join(matched)}")
            for snip in snippets:
                print(f"[TREFFER {i}] Ausschnitt: {snip}")

        html = page.content()
        body_text = page.locator("body").inner_text(timeout=5000)
        print(f"[DOM] Bekannte ID vorhanden: {KNOWN_ID.lower() in html.lower()}")
        print(f"[DOM] Massive Explosion vorhanden: {'massive explosion' in body_text.lower()}")
        print(f"[DOM] 90 Sekunden vorhanden: {'90 sekunden' in body_text.lower()}")

        print("[INFO] Diagnose abgeschlossen; headlines.json bleibt unverändert.")
        browser.close()


if __name__ == "__main__":
    get_latest_news90()

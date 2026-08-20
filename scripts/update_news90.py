import json
import re
from playwright.sync_api import sync_playwright

SERIES_ID = "AA-1Y5RJCD1H2111"
KNOWN_ID = "AAUUYP6RNA3IVBL8FFPC"
SERIES_URL = f"https://www.servustv.com/de/page/{SERIES_ID}"


def main():
    print("[INFO] Diagnose: IP/Geo vs. Browser-Locale/Cookies bei ServusTV")
    print(f"[INFO] Kontroll-ID des aktuellen Beitrags: {KNOWN_ID}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            timezone_id="Europe/Vienna",
            geolocation={"latitude": 47.8095, "longitude": 13.0550},
            permissions=["geolocation"],
            viewport={"width": 1440, "height": 1200},
            extra_http_headers={
                "Accept-Language": "de-AT,de;q=0.9,en;q=0.7",
            },
        )
        page = context.new_page()

        responses = []
        def on_response(response):
            try:
                u = response.url
                if "servustv.com" in u or "redbull.com" in u:
                    ctype = (response.headers.get("content-type") or "").lower()
                    if any(x in ctype for x in ("json", "text", "html", "javascript", "component")):
                        try:
                            body = response.text()
                        except Exception:
                            return
                        low = body.lower()
                        if KNOWN_ID.lower() in low or "massive explosion" in low or "90 sekunden" in low:
                            responses.append((u, ctype, body))
            except Exception:
                pass

        page.on("response", on_response)
        page.goto(SERIES_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)

        # Consent akzeptieren, damit technisch notwendige/optionale Zustände gesetzt werden können.
        for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
            try:
                b = page.get_by_role("button", name=re.compile(label, re.I))
                if b.count() and b.first.is_visible():
                    b.first.click(timeout=2000)
                    page.wait_for_timeout(1500)
                    break
            except Exception:
                pass

        # Neu laden, nachdem Cookies gesetzt wurden.
        page.reload(wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(4000)
        for _ in range(10):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(500)

        html = page.content()
        text = page.locator("body").inner_text(timeout=10000)
        cookies = context.cookies()

        print(f"[DIAG] navigator.language: {page.evaluate('navigator.language')}")
        print(f"[DIAG] Zeitzone: {page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone')}")
        print(f"[DIAG] Cookies gesetzt: {len(cookies)}")
        for c in cookies:
            name = c.get('name','')
            value = c.get('value','')
            if any(k in name.lower() for k in ('country','market','locale','lang','region','geo','consent')):
                print(f"[COOKIE] {name}={value[:180]}")

        print(f"[DIAG] Kontroll-ID im DOM: {KNOWN_ID in html}")
        print(f"[DIAG] 'Massive Explosion' im DOM/Text: {'massive explosion' in (html + text).lower()}")
        print(f"[DIAG] '90 Sekunden' im DOM/Text: {'90 sekunden' in (html + text).lower()}")
        print(f"[DIAG] Relevante Netzwerkantworten: {len(responses)}")

        seen = set()
        for i, (url, ctype, body) in enumerate(responses, 1):
            key = (url, len(body))
            if key in seen:
                continue
            seen.add(key)
            low = body.lower()
            found = []
            if KNOWN_ID.lower() in low:
                found.append("AKTUELLE ID")
            if "massive explosion" in low:
                found.append("MASSIVE EXPLOSION")
            if "90 sekunden" in low:
                found.append("90 SEKUNDEN")
            print(f"[TREFFER {i}] {' | '.join(found)}")
            print(f"[TREFFER {i}] Quelle: {url}")
            print(f"[TREFFER {i}] Content-Type: {ctype}")

        if KNOWN_ID in html or "massive explosion" in (html + text).lower() or any(KNOWN_ID.lower() in b.lower() for _,_,b in responses):
            print("[ERFOLG] Österreichischer Browserzustand reicht aus; wir können darauf die Automatik aufbauen.")
        else:
            print("[ERGEBNIS] Auch mit de-AT, Europe/Vienna, Salzburg-Geolocation und Cookies fehlt der aktuelle Beitrag.")
            print("[ERGEBNIS] Damit spricht sehr viel dafür, dass ServusTV serverseitig nach der öffentlichen IP des GitHub-Runners ausliefert.")
            print("[INFO] headlines.json wird bei diesem Diagnose-Test nicht verändert.")

        browser.close()


if __name__ == "__main__":
    main()

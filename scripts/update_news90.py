import json
import re
from pathlib import Path
from urllib.parse import quote, urljoin, urlparse

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
JSON_PATH = ROOT / "headlines.json"
QUERY = "Servus Nachrichten in 90 Sekunden"
SEARCH_URL = f"https://www.servustv.com/de/search?query={quote(QUERY)}"

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
    parsed = urlparse(urljoin("https://www.servustv.com", url))
    if parsed.netloc not in {"www.servustv.com", "servustv.com"}:
        return ""
    path = parsed.path.rstrip("/")
    # Nur echte Beitragsseiten, keine Such-/Serienseiten.
    if not re.fullmatch(r"/de/page/[A-Z0-9-]+(?:/[^?#]+)?", path, flags=re.I):
        return ""
    return f"https://www.servustv.com{path}"


def read_meta(page, selector):
    try:
        loc = page.locator(selector).first
        if loc.count():
            return loc.get_attribute("content") or ""
    except Exception:
        pass
    return ""


def get_title_and_image(page):
    title = ""

    # Auf den Beitragsseiten ist die eigentliche sichtbare Headline meist H1/H2.
    for selector in ("h1", "h2"):
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 8)):
                txt = " ".join((loc.nth(i).inner_text() or "").split())
                low = txt.lower()
                if not txt:
                    continue
                if low in {
                    "servus nachrichten in 90 sekunden",
                    "servus nachrichten: einzelbeiträge",
                    "servustv on",
                }:
                    continue
                if low.startswith("servus nachrichten:"):
                    continue
                title = txt
                break
        except Exception:
            pass
        if title:
            break

    if not title:
        og = read_meta(page, 'meta[property="og:title"]')
        if og:
            title = re.sub(
                r"\s*\|\s*(Servus )?Nachrichten in 90 Sekunden.*$",
                "",
                og,
                flags=re.I,
            ).strip()

    image = read_meta(page, 'meta[property="og:image"]')
    if not image:
        image = read_meta(page, 'meta[name="twitter:image"]')

    return title, image


def find_latest_via_search(page):
    print(f"[INFO] Öffne ServusTV-Suche: {SEARCH_URL}")
    page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)

    # Consent schließen, falls vorhanden.
    for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
        try:
            button = page.get_by_role("button", name=re.compile(label, re.I))
            if button.count() and button.first.is_visible():
                button.first.click(timeout=1500)
                page.wait_for_timeout(1200)
                break
        except Exception:
            pass

    # Suchresultate lazy laden.
    for _ in range(5):
        page.mouse.wheel(0, 1000)
        page.wait_for_timeout(600)

    links = page.locator("a[href]")
    candidates = []

    for i in range(links.count()):
        a = links.nth(i)
        try:
            if not a.is_visible():
                continue
            href = normalize_article_url(a.get_attribute("href") or "")
            if not href:
                continue

            # Nicht nur Anchor-Text prüfen, sondern den umgebenden Kartencontainer.
            info = a.evaluate(
                """el => {
                    let n = el;
                    for (let i=0; i<8 && n; i++, n=n.parentElement) {
                        const txt = (n.innerText || '').trim();
                        const r = n.getBoundingClientRect();
                        if (txt.length > 20 && r.width > 200 && r.height > 80) {
                            return {text: txt, x:r.left, y:r.top + window.scrollY};
                        }
                    }
                    return {text:(el.innerText||'').trim(), x:0, y:0};
                }"""
            )
            text = " ".join((info.get("text") or "").split())
            low = text.lower()

            if "servus nachrichten in 90 sekunden" not in low and "nachrichten in 90 sekunden" not in low:
                continue

            if href not in [x[2] for x in candidates]:
                candidates.append((info.get("y", 10**9), info.get("x", 10**9), href, text))
        except Exception:
            continue

    # Die ServusTV-Suche ist chronologisch sortiert; erstes sichtbares Resultat = neuestes.
    candidates.sort(key=lambda x: (x[0], x[1]))

    print(f"[INFO] {len(candidates)} passende 90-Sekunden-Suchergebnisse gefunden.")
    for idx, (_, _, href, text) in enumerate(candidates[:8], 1):
        print(f"[KANDIDAT {idx}] {href} | {text[:180]}")

    if not candidates:
        return ""

    return candidates[0][2]


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 1200},
        )
        page = context.new_page()

        article_url = find_latest_via_search(page)
        if not article_url:
            print("[WARNUNG] Kein 90-Sekunden-Beitrag über die ServusTV-Suche gefunden.")
            print("[WARNUNG] Bestehende news90-Daten bleiben unverändert.")
            browser.close()
            return

        print(f"[INFO] Öffne neuesten Suchtreffer: {article_url}")
        page.goto(article_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        body_text = " ".join(page.locator("body").inner_text(timeout=5000).split())
        if "servus nachrichten in 90 sekunden" not in body_text.lower():
            print("[WARNUNG] Suchtreffer ist kein bestätigter 90-Sekunden-Beitrag.")
            print("[WARNUNG] Bestehende Daten bleiben unverändert.")
            browser.close()
            return

        title, image = get_title_and_image(page)
        if not title:
            print("[WARNUNG] Keine belastbare Headline auf dem neuesten Suchtreffer gefunden.")
            browser.close()
            return

        data = load_existing_data()
        old_link = data.get("news90_link", "")
        old_title = data.get("news90_title", "")

        data["news90_title"] = title
        data["news90_link"] = article_url
        if image:
            data["news90_image"] = image
            data["news90_thumbnail"] = image

        JSON_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        print(f"[ERFOLG] Aktuellster 90-Sekunden-Beitrag: {title}")
        print(f"[ERFOLG] Link: {article_url}")
        if image:
            print(f"[ERFOLG] Bild: {image}")

        if old_link == article_url and old_title == title:
            print("[INFO] Beitrag unverändert.")
        else:
            print("[INFO] Neuer Beitrag erkannt; headlines.json aktualisiert.")

        browser.close()


if __name__ == "__main__":
    main()

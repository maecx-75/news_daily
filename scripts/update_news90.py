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


def clean_title(text):
    text = " ".join((text or "").split())
    text = re.sub(r"\s*\|\s*(Servus )?Nachrichten in 90 Sekunden.*$", "", text, flags=re.I)
    text = re.sub(r"\s*-\s*ServusTV On\s*$", "", text, flags=re.I)
    return text.strip()


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


def read_meta(page, selector, attr="content"):
    try:
        loc = page.locator(selector).first
        if loc.count():
            return loc.get_attribute(attr) or ""
    except Exception:
        pass
    return ""


def title_from_page(page):
    candidates = []

    for selector in ("h1", "h2"):
        try:
            loc = page.locator(selector)
            for i in range(min(loc.count(), 10)):
                txt = " ".join((loc.nth(i).inner_text() or "").split())
                if txt:
                    candidates.append(txt)
        except Exception:
            pass

    for selector in ('meta[property="og:title"]', 'meta[name="twitter:title"]'):
        value = read_meta(page, selector)
        if value:
            candidates.append(value)

    try:
        if page.title():
            candidates.append(page.title())
    except Exception:
        pass

    generic = {
        "servus nachrichten in 90 sekunden",
        "servus nachrichten: einzelbeiträge",
        "servus nachrichten: aktuelle meldungen und videos",
        "servustv on",
    }

    for value in candidates:
        cleaned = clean_title(value)
        low = cleaned.lower()
        if not cleaned or low in generic or low.startswith("servus nachrichten:"):
            continue
        return cleaned

    return ""


def image_from_page(page):
    for selector in ('meta[property="og:image"]', 'meta[name="twitter:image"]'):
        value = read_meta(page, selector)
        if value:
            return urljoin(page.url, value)
    return ""


def find_first_news90_card(page):
    """Findet innerhalb der Rubrik die oberste Reihe und darin die linke Karte.

    Wichtig: Wir orientieren uns nicht mehr am ersten großen <img>, weil ServusTV
    intern Bilder/Slides klonen kann. Stattdessen nehmen wir die wiederholte
    Unterzeile 'Servus Nachrichten in 90 Sekunden' unter den Karten. So lässt
    sich die tatsächlich sichtbare linke Karte eindeutig bestimmen.
    """

    heading = None
    for selector in ("h1", "h2", "h3", "h4"):
        try:
            loc = page.locator(selector).filter(
                has_text=re.compile(r"^\s*Servus Nachrichten in 90 Sekunden\s*$", re.I)
            )
            if loc.count():
                heading = loc.first
                break
        except Exception:
            pass

    if heading is None:
        try:
            loc = page.get_by_text("Servus Nachrichten in 90 Sekunden", exact=True)
            if loc.count():
                heading = loc.first
        except Exception:
            pass

    if heading is None:
        raise RuntimeError("Rubrik 'Servus Nachrichten in 90 Sekunden' nicht gefunden.")

    heading.scroll_into_view_if_needed()
    page.wait_for_timeout(1200)
    hbox = heading.bounding_box()
    if not hbox:
        raise RuntimeError("Position der 90-Sekunden-Rubrik konnte nicht bestimmt werden.")

    heading_bottom = hbox["y"] + hbox["height"]
    print(f"[INFO] 90-Sekunden-Rubrik gefunden bei y={hbox['y']:.0f}")

    # Alle exakten Vorkommen des Rubriknamens suchen. Das erste ist die Überschrift,
    # die weiteren sichtbaren Vorkommen sind die Unterzeilen der Karten.
    labels = page.get_by_text("Servus Nachrichten in 90 Sekunden", exact=True)
    cards = []

    for i in range(labels.count()):
        label = labels.nth(i)
        try:
            box = label.bounding_box()
            if not box:
                continue
            if box["y"] <= heading_bottom + 20:
                continue
            if box["y"] > heading_bottom + 750:
                continue

            info = label.evaluate(
                """el => {
                    let n = el;
                    let best = null;
                    for (let i = 0; i < 10 && n; i++, n = n.parentElement) {
                        const r = n.getBoundingClientRect();
                        const txt = (n.innerText || '').trim();
                        const href = n.href || (n.querySelector && n.querySelector('a[href]') ? n.querySelector('a[href]').href : '');
                        if (r.width >= 250 && r.height >= 180 && txt.length >= 20) {
                            best = {x:r.left, y:r.top, w:r.width, h:r.height, text:txt, href:href};
                        }
                        if (r.width > window.innerWidth * 0.9) break;
                    }
                    return best;
                }"""
            )
            if not info:
                continue

            cards.append((info["y"], info["x"], label, info))
        except Exception:
            continue

    if not cards:
        raise RuntimeError("Keine sichtbaren 90-Sekunden-Karten unter der Rubrik gefunden.")

    # Zuerst oberste Kartenreihe bestimmen, danach wirklich ganz links wählen.
    min_y = min(item[0] for item in cards)
    first_row = [item for item in cards if abs(item[0] - min_y) <= 80]
    first_row.sort(key=lambda item: item[1])
    y, x, label, info = first_row[0]

    preview = " ".join(info.get("text", "").split())[:180]
    print(f"[INFO] Linke Karte der obersten Reihe bei x={x:.0f}, y={y:.0f}")
    print(f"[INFO] Kartentext: {preview}")

    href = normalize_article_url(info.get("href", ""))
    if href:
        print(f"[INFO] Link direkt an linker Karte gefunden: {href}")
        return href

    # Falls kein href vorhanden ist, klicken wir auf den Kartencontainer statt auf
    # das Bild. Das vermeidet, dass ein geklontes/überlagertes Bild geklickt wird.
    old_url = page.url
    try:
        label.evaluate(
            """el => {
                let n = el;
                let target = null;
                for (let i = 0; i < 10 && n; i++, n = n.parentElement) {
                    const r = n.getBoundingClientRect();
                    const txt = (n.innerText || '').trim();
                    if (r.width >= 250 && r.height >= 180 && txt.length >= 20) target = n;
                    if (r.width > window.innerWidth * 0.9) break;
                }
                if (target) target.click();
                else el.click();
            }"""
        )
    except Exception:
        page.mouse.click(info["x"] + info["w"] / 2, info["y"] + info["h"] / 2)

    page.wait_for_timeout(4000)

    if len(page.context.pages) > 1:
        newest = page.context.pages[-1]
        newest.wait_for_load_state("domcontentloaded", timeout=15000)
        href = normalize_article_url(newest.url)
        if href:
            print(f"[INFO] Ziel im neuen Tab: {href}")
            return href

    href = normalize_article_url(page.url)
    if href and page.url != old_url:
        print(f"[INFO] Ziel nach Klick: {href}")
        return href

    raise RuntimeError("Linke 90-Sekunden-Karte konnte nicht geöffnet werden.")


def get_latest_news90():
    print(f"[INFO] Öffne Servus-Nachrichten-Seite: {SERIES_URL}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            locale="de-AT",
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1440, "height": 1100},
        )
        page = context.new_page()
        page.goto(SERIES_URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        for label in ("Alle akzeptieren", "Akzeptieren", "Zustimmen"):
            try:
                button = page.get_by_role("button", name=re.compile(label, re.I))
                if button.count() and button.first.is_visible():
                    button.first.click(timeout=1500)
                    page.wait_for_timeout(1000)
                    break
            except Exception:
                pass

        for _ in range(8):
            try:
                exact = page.get_by_text("Servus Nachrichten in 90 Sekunden", exact=True)
                if exact.count() and exact.first.is_visible():
                    break
            except Exception:
                pass
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(700)

        try:
            article_url = find_first_news90_card(page)
        except Exception as exc:
            browser.close()
            print(f"[WARNUNG] {exc}")
            print("[WARNUNG] Bestehende news90-Daten bleiben unverändert.")
            return

        page.goto(article_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(2500)

        title = title_from_page(page)
        image = image_from_page(page)

        if not title:
            browser.close()
            print("[WARNUNG] Auf der Zielseite keine belastbare Headline gefunden.")
            print("[WARNUNG] Bestehende news90-Daten bleiben unverändert.")
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

        print(f"[ERFOLG] Aktuellster sichtbarer 90-Sekunden-Beitrag: {title}")
        print(f"[ERFOLG] Link: {article_url}")
        if image:
            print(f"[ERFOLG] Bild: {image}")

        if old_link == article_url and old_title == title:
            print("[INFO] Beitrag ist unverändert; kein inhaltliches Update nötig.")
        else:
            print("[INFO] Neuer Beitrag erkannt; headlines.json aktualisiert.")

        browser.close()


if __name__ == "__main__":
    get_latest_news90()

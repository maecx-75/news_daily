from playwright.sync_api import sync_playwright

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"
RAIL_ID = "f7c25019-f876-44ee-ab56-02e0d7bd231e"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent="Mozilla/5.0",
            viewport={"width": 1600, "height": 1000}
        )

        def handle_response(response):
            url = response.url

            try:
                body = response.text()
            except Exception:
                return

            if RAIL_ID in url or RAIL_ID in body or "Iran-Krieg" in body or "Arda Saatci" in body:
                print("===== TREFFER =====")
                print("URL:", url)
                print("CONTENT-TYPE:", response.headers.get("content-type"))
                print(body[:5000])

        page.on("response", handle_response)

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        for _ in range(16):
            page.mouse.wheel(0, 900)
            page.wait_for_timeout(1000)

        browser.close()

if __name__ == "__main__":
    main()

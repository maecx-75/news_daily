from playwright.sync_api import sync_playwright

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"

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
                ct = response.headers.get("content-type", "")
                if "json" not in ct and "text" not in ct and "javascript" not in ct:
                    return

                body = response.text()

                keywords = [
                    "Iran-Krieg",
                    "Iran",
                    "Servus Nachrichten in 90 Sekunden",
                    "Arda Saatci",
                    "Virus-Schiff",
                    "Geld-Transporte"
                ]

                if any(k in body for k in keywords):
                    print("===== TREFFER RESPONSE =====")
                    print("URL:", url)
                    print("CONTENT-TYPE:", ct)
                    print(body[:3000])

            except Exception:
                pass

        page.on("response", handle_response)

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        for _ in range(12):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(1000)

        browser.close()

if __name__ == "__main__":
    main()

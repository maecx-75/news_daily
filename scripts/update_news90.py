from playwright.sync_api import sync_playwright

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"

def main():
    seen = set()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent="Mozilla/5.0",
            viewport={"width": 1600, "height": 1000}
        )

        def log_request(request):
            url = request.url
            low = url.lower()

            keywords = [
                "redbull",
                "servustv",
                "rail",
                "rails",
                "collection",
                "collections",
                "dynamic",
                "v5.1",
                "cards",
                "search",
                "products",
                "page",
                "f7c25019"
            ]

            if any(k in low for k in keywords):
                if url not in seen:
                    seen.add(url)
                    print("REQ:", url)

        page.on("request", log_request)

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        for _ in range(20):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(1000)

        browser.close()

if __name__ == "__main__":
    main()

from playwright.sync_api import sync_playwright

PAGE_URL = "https://www.servustv.com/de/page/AA-1Y5RJCD1H2111"

def main():
    seen = []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            user_agent="Mozilla/5.0",
            viewport={"width": 1600, "height": 1000}
        )

        def log_response(response):
            url = response.url
            lower = url.lower()

            if any(word in lower for word in [
                "api",
                "graphql",
                "search",
                "page",
                "content",
                "playlist",
                "asset",
                "video",
                "items",
                "collection"
            ]):
                if url not in seen:
                    seen.append(url)

        page.on("response", log_response)

        page.goto(PAGE_URL, wait_until="networkidle", timeout=60000)

        for _ in range(12):
            page.mouse.wheel(0, 1000)
            page.wait_for_timeout(1000)

        print("DEBUG NETWORK URLS:")
        for url in seen[:120]:
            print(url)

        browser.close()

if __name__ == "__main__":
    main()

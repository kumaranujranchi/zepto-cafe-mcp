import asyncio
import urllib.parse
import os
from playwright.async_api import async_playwright

async def block_aggressively(route):
    # Block EVERYTHING except document and script (to minimize RAM)
    if route.request.resource_type in ["image", "media", "font", "stylesheet"]:
        await route.abort()
    else:
        await route.continue_()

async def scrape_platform(platform, items_list, is_mobile=False):
    async with async_playwright() as p:
        # Essential flags for low-RAM Docker environments
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-gpu", "--js-flags=--max-old-space-size=256"]
        )
        
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        if is_mobile:
            ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1"
            
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800} if not is_mobile else {'width': 375, 'height': 812},
            user_agent=ua,
            is_mobile=is_mobile
        )
        page = await context.new_page()
        # await page.route("**/*", block_aggressively) # Blocking CSS might break button clicks, let's keep it for now but block images
        await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

        print(f"--- {platform} ---")
        for item in items_list:
            short_item = " ".join(item.split()[:4])
            query = urllib.parse.quote(short_item)
            url = f"https://www.zepto.com/search?q={query}" if platform == "Zepto" else \
                  f"https://blinkit.com/s/?q={query}" if platform == "Blinkit" else \
                  f"https://www.swiggy.com/instamart/search?query={query}"
            
            try:
                await page.goto(url, timeout=60000, wait_until="domcontentloaded")
                await asyncio.sleep(5)
                # Click logic
                await page.evaluate("""
                    () => {
                        const phrases = ['ADD', 'Add', 'Add to cart'];
                        const els = document.querySelectorAll('button, div, span');
                        for (let el of els) {
                            let text = el.textContent.trim().toUpperCase();
                            if (phrases.includes(text) || (text === 'ADD' && el.offsetHeight > 0)) {
                                el.click();
                                return;
                            }
                        }
                    }
                """)
                await asyncio.sleep(1)
            except: pass

        # Extract total
        result = await page.evaluate("""
            () => {
                const text = document.body.innerText;
                const matches = text.match(/₹\s?\d+/g);
                return matches ? matches.join(', ') : 'Empty';
            }
        """)
        
        ss_path = f"/tmp/{platform.lower().replace(' ', '_')}.png"
        await page.screenshot(path=ss_path)
        await browser.close()
        return result, ss_path

async def compare_prices(items_text):
    items_list = [i.strip() for i in (items_text.split(',') if ',' in items_text else items_text.split('\n')) if i.strip()]
    results = {}
    screenshots = {}

    try:
        # Sequential processing with FULL browser restart to save RAM
        results["Zepto"], screenshots["Zepto"] = await scrape_platform("Zepto", items_list, is_mobile=False)
        results["Blinkit"], screenshots["Blinkit"] = await scrape_platform("Blinkit", items_list, is_mobile=True)
        results["Swiggy Instamart"], screenshots["Swiggy Instamart"] = await scrape_platform("Swiggy Instamart", items_list, is_mobile=False)
    except Exception as e:
        print(f"Global Error: {e}")

    summary = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS:**"]
    for platform, value in results.items(): 
        summary.append(f"**{platform}**: {value}")
    
    return {"text": "\n".join(summary), "screenshots": screenshots}

import asyncio
import urllib.parse
import os
from playwright.async_api import async_playwright

async def block_media(route):
    if route.request.resource_type in ["media", "font"]:
        await route.abort()
    else:
        await route.continue_()

async def search_and_add_generic(page, platform, item):
    # Use only first 4 words for better search matches
    short_item = " ".join(item.split()[:4])
    query = urllib.parse.quote(short_item)
    url = f"https://www.zepto.com/search?q={query}" if platform == "Zepto" else \
          f"https://blinkit.com/s/?q={query}" if platform == "Blinkit" else \
          f"https://www.swiggy.com/instamart/search?query={query}"
    
    print(f"[{platform}] Searching for: {short_item}")
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(7) # Extended wait for data centers
        
        # Aggressive Click logic
        success = await page.evaluate("""
            () => {
                const addPhrases = ['ADD', 'Add', 'Add to cart'];
                const els = document.querySelectorAll('button, div, span');
                for (let el of els) {
                    if (addPhrases.includes(el.textContent.trim().toUpperCase()) || 
                        (el.textContent.trim().toUpperCase() === 'ADD' && el.offsetHeight > 0)) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        print(f"[{platform}] Click success: {success}")
    except Exception as e:
        print(f"[{platform}] Error: {e}")

async def compare_prices(items_text):
    items_list = [i.strip() for i in (items_text.split(',') if ',' in items_text else items_text.split('\n')) if i.strip()]
    results = {}
    screenshots = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # Zepto & Instamart (Desktop View)
        for platform in ["Zepto", "Swiggy Instamart"]:
            context = await browser.new_context(viewport={'width': 1280, 'height': 800}, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
            page = await context.new_page()
            # await page.route("**/*", block_media) # Media off might trigger bot detection on desktop
            print(f"--- {platform} ---")
            for item in items_list: await search_and_add_generic(page, platform, item)
            results[platform] = await page.evaluate("() => document.body.innerText.match(/₹\\s?\\d+/g)?.join(', ') || 'Empty'")
            ss_path = f"/tmp/{platform.lower().replace(' ', '_')}.png"
            await page.screenshot(path=ss_path)
            screenshots[platform] = ss_path
            await context.close()

        # Blinkit (Mobile View worked better for search)
        context = await browser.new_context(viewport={'width': 375, 'height': 812}, is_mobile=True, user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1")
        page = await context.new_page()
        print("--- Blinkit ---")
        for item in items_list: await search_and_add_generic(page, "Blinkit", item)
        results["Blinkit"] = await page.evaluate("() => document.body.innerText.match(/₹\\s?\\d+/g)?.join(', ') || 'Empty'")
        ss_path = "/tmp/blinkit.png"
        await page.screenshot(path=ss_path)
        screenshots["Blinkit"] = ss_path
        
        await browser.close()

    summary = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS:**"]
    for platform, value in results.items(): summary.append(f"**{platform}**: {value}")
    return {"text": "\n".join(summary), "screenshots": screenshots}

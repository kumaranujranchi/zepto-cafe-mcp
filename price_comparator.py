import asyncio
import urllib.parse
import time
import os
from playwright.async_api import async_playwright

async def block_media(route):
    if route.request.resource_type in ["media", "font"]:
        await route.abort()
    else:
        await route.continue_()

async def search_and_add_zepto(page, item):
    query = urllib.parse.quote(item)
    url = f"https://www.zepto.com/search?q={query}"
    print(f"[Zepto] Searching for: {item}")
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        # Wait for any product card to appear
        try:
            await page.wait_for_selector("[data-testid='product-card']", timeout=10000)
        except:
            pass
        
        await asyncio.sleep(3)
        # Zepto Mobile Add Button
        success = await page.evaluate("""
            () => {
                const btn = document.querySelector("[data-testid='product-card-add-btn'], [data-testid='add-btn']");
                if (btn) { btn.click(); return true; }
                const anyAdd = Array.from(document.querySelectorAll('button')).find(b => b.textContent.includes('Add'));
                if (anyAdd) { anyAdd.click(); return true; }
                return false;
            }
        """)
        print(f"[Zepto] Clicked: {success}")
    except Exception as e:
        print(f"[Zepto] Error: {e}")

async def search_and_add_blinkit(page, item):
    query = urllib.parse.quote(item)
    url = f"https://blinkit.com/s/?q={query}"
    print(f"[Blinkit] Searching for: {item}")
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        # Wait for product grid
        try:
            await page.wait_for_selector("[data-testid='product-card']", timeout=10000)
        except:
            pass
            
        await asyncio.sleep(3)
        success = await page.evaluate("""
            () => {
                const addDiv = Array.from(document.querySelectorAll('div')).find(d => d.textContent.trim() === 'ADD');
                if (addDiv) { addDiv.click(); return true; }
                return false;
            }
        """)
        print(f"[Blinkit] Clicked: {success}")
    except Exception as e:
        print(f"[Blinkit] Error: {e}")

async def search_and_add_instamart(page, item):
    query = urllib.parse.quote(item)
    url = f"https://www.swiggy.com/instamart/search?query={query}"
    print(f"[Instamart] Searching for: {item}")
    try:
        # Instamart is picky, try desktop headers even in mobile view
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        await asyncio.sleep(5)
        success = await page.evaluate("""
            () => {
                const addBtn = Array.from(document.querySelectorAll('div, button')).find(el => el.textContent.trim() === 'ADD');
                if (addBtn) { addBtn.click(); return true; }
                return false;
            }
        """)
        print(f"[Instamart] Clicked: {success}")
    except Exception as e:
        print(f"[Instamart] Error: {e}")

async def compare_prices(items_text):
    items_list = [i.strip() for i in (items_text.split(',') if ',' in items_text else items_text.split('\n')) if i.strip()]
    results = {}
    screenshots = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using a very standard Desktop user agent to avoid 403 blocks
        context = await browser.new_context(
            viewport={'width': 375, 'height': 812},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1",
            geolocation={"latitude": 12.9716, "longitude": 77.5946},
            permissions=["geolocation"],
            extra_http_headers={
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            }
        )
        page = await context.new_page()
        await page.route("**/*", block_media)

        # Zepto
        print("--- Zepto ---")
        for item in items_list: await search_and_add_zepto(page, item)
        results['Zepto'] = await page.evaluate("() => document.querySelector('[data-testid=\"cart-btn\"]')?.innerText.split('\\n').join(' ') || 'Empty'")
        await page.screenshot(path="/tmp/zepto.png")
        screenshots['Zepto'] = "/tmp/zepto.png"

        # Blinkit
        print("--- Blinkit ---")
        for item in items_list: await search_and_add_blinkit(page, item)
        results['Blinkit'] = await page.evaluate("() => Array.from(document.querySelectorAll('div')).find(d => d.textContent.includes('View Cart'))?.innerText.split('\\n').join(' ') || 'Empty'")
        await page.screenshot(path="/tmp/blinkit.png")
        screenshots['Blinkit'] = "/tmp/blinkit.png"

        # Instamart
        print("--- Instamart ---")
        for item in items_list: await search_and_add_instamart(page, item)
        results['Swiggy Instamart'] = await page.evaluate("() => Array.from(document.querySelectorAll('div')).find(d => d.textContent.includes('View Cart'))?.innerText.split('\\n').join(' ') || 'Empty'")
        await page.screenshot(path="/tmp/instamart.png")
        screenshots['Swiggy Instamart'] = "/tmp/instamart.png"

        await browser.close()

    summary = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS:**"]
    for platform, value in results.items():
        summary.append(f"**{platform}**: {value}")
    
    return {"text": "\n".join(summary), "screenshots": screenshots}

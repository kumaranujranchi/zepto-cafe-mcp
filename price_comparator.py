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

async def search_and_add_generic(page, platform, item, url):
    print(f"[{platform}] Searching for: {item}")
    try:
        await page.goto(url, timeout=60000, wait_until="commit")
        await asyncio.sleep(6) # Wait for results
        
        # Try to click ADD button
        success = await page.evaluate("""
            () => {
                const addPhrases = ['ADD', 'Add to cart', 'Add To Cart', 'Add'];
                const els = document.querySelectorAll('button, div, span, a');
                for (let el of els) {
                    let txt = el.textContent.trim();
                    if (addPhrases.includes(txt) || (txt.toLowerCase() === 'add' && el.tagName === 'BUTTON')) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        print(f"[{platform}] Click success: {success}")
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[{platform}] Error: {e}")

async def get_cart_value(page, platform):
    try:
        return await page.evaluate("""
            () => {
                const els = document.querySelectorAll('div, button, a, span');
                for (let e of els) {
                    let txt = e.textContent;
                    if (txt.includes('₹') && (txt.toLowerCase().includes('view cart') || txt.toLowerCase().includes('checkout') || txt.toLowerCase().includes('cart'))) {
                        return txt.split('\\n').join(' ').trim();
                    }
                }
                return "Not Found";
            }
        """)
    except:
        return "Error"

async def compare_prices(items_text):
    items_list = [i.strip() for i in (items_text.split(',') if ',' in items_text else items_text.split('\n')) if i.strip()]
    results = {}
    screenshots = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # Using Mobile Viewport for simpler UI
        context = await browser.new_context(
            viewport={'width': 375, 'height': 812},
            is_mobile=True,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
            geolocation={"latitude": 12.9716, "longitude": 77.5946},
            permissions=["geolocation"]
        )
        page = await context.new_page()
        await page.route("**/*", block_media)

        platforms = {
            "Zepto": "https://www.zepto.com/search?q=",
            "Blinkit": "https://blinkit.com/s/?q=",
            "Swiggy Instamart": "https://www.swiggy.com/instamart/search?query="
        }

        for name, base_url in platforms.items():
            print(f"--- Starting {name} ---")
            for item in items_list:
                query = urllib.parse.quote(item)
                await search_and_add_generic(page, name, item, base_url + query)
            
            results[name] = await get_cart_value(page, name)
            
            # Take debug screenshot
            ss_path = f"/tmp/{name.replace(' ', '_').lower()}.png"
            await page.screenshot(path=ss_path)
            screenshots[name] = ss_path

        await browser.close()

    summary = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS:**"]
    for platform, value in results.items():
        summary.append(f"**{platform}**: {value}")
    
    return {"text": "\n".join(summary), "screenshots": screenshots}

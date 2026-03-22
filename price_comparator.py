import asyncio
import urllib.parse
import time
import random
from playwright.async_api import async_playwright

async def block_aggressively(route):
    """Block images, fonts, and media to speed up page loads."""
    if route.request.resource_type in ["image", "media", "font"]:
        await route.abort()
    else:
        await route.continue_()

async def search_and_add_zepto(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://www.zepto.com/search?q={query}"
    print(f"[Zepto] Searching for: {clean_item}")
    try:
        # Lower expectations for load state
        await page.goto(url, timeout=60000, wait_until="commit")
        await asyncio.sleep(5) # Give it time to render after commit
        
        # Click Add to Cart
        await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll("button");
                for (let btn of buttons) {
                    let txt = btn.textContent.toLowerCase();
                    if (txt.includes('add') || txt === 'add') {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[Zepto] Error adding {item}: {e}")

async def search_and_add_blinkit(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://blinkit.com/s/?q={query}"
    print(f"[Blinkit] Searching for: {clean_item}")
    try:
        await page.goto(url, timeout=60000, wait_until="commit")
        await asyncio.sleep(5)
        await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll("div, button");
                for (let btn of buttons) {
                    let txt = btn.textContent.trim().toUpperCase();
                    if (txt === 'ADD' || txt.includes('ADD TO CART')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[Blinkit] Error adding {item}: {e}")

async def search_and_add_instamart(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={query}"
    print(f"[Instamart] Searching for: {clean_item}")
    try:
        await page.goto(url, timeout=60000, wait_until="commit")
        await asyncio.sleep(5)
        await page.evaluate("""
            () => {
                const buttons = document.querySelectorAll("button, div");
                for (let btn of buttons) {
                    let txt = btn.textContent.trim().toUpperCase();
                    if (txt === 'ADD' || txt.includes('ADD TO CART')) {
                        btn.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        await asyncio.sleep(2)
    except Exception as e:
        print(f"[Instamart] Error adding {item}: {e}")

async def compare_prices(items_text):
    try:
        # Global timeout of 5 mins
        return await asyncio.wait_for(_compare_prices_internal(items_text), timeout=300.0)
    except asyncio.TimeoutError:
        return "❌ **Timeout Error:** Bot ko result nahi mil pa raha. Shayad platform ne block kar diya hai. Kripya thodi der baad try karein."
    except Exception as e:
        return f"❌ **General Error:** {str(e)}"

async def _compare_prices_internal(items_text):
    if ',' in items_text:
        items_list = [i.strip() for i in items_text.split(',')]
    else:
        items_list = [i.strip() for i in items_text.split('\n')]
    items_list = [i for i in items_list if i]

    results = {}
    
    async with async_playwright() as p:
        print("[System] Launching Chromium...")
        # Switching to Chromium as it's often more stable for automation
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 1280, 'height': 800},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            geolocation={"latitude": 12.9716, "longitude": 77.5946},
            permissions=["geolocation"]
        )
        page = await context.new_page()
        await page.route("**/*", block_aggressively)

        # Zepto
        try:
            print("--- Starting Zepto ---")
            for item in items_list:
                await search_and_add_zepto(page, item)
            results['Zepto'] = await page.evaluate("""
                () => {
                    let el = document.querySelector("[data-testid='cart-btn'], .cart-button, #cart-button");
                    if (el) return el.innerText.split('\\n').join(' ');
                    // Try finding any text with ₹
                    let items = document.querySelectorAll("div, span, p");
                    for (let it of items) {
                        if (it.innerText.includes('₹') && it.innerText.toLowerCase().includes('cart')) {
                            return it.innerText.split('\\n').join(' ');
                        }
                    }
                    return "Not Found";
                }
            """)
            print(f"[Zepto] Final: {results['Zepto']}")
        except Exception as e:
            print(f"[Zepto] Failed: {e}")
            results['Zepto'] = "Error"

        # Blinkit
        try:
            print("--- Starting Blinkit ---")
            for item in items_list:
                await search_and_add_blinkit(page, item)
            results['Blinkit'] = await page.evaluate("""
                () => {
                    let els = document.querySelectorAll("div, button");
                    for(let e of els){
                        if(e.textContent.includes('View Cart') && e.textContent.includes('₹')){
                            return e.innerText.split('\\n').join(' ');
                        }
                    }
                    return "Not Found";
                }
            """)
            print(f"[Blinkit] Final: {results['Blinkit']}")
        except Exception as e:
            print(f"[Blinkit] Failed: {e}")
            results['Blinkit'] = "Error"

        # Instamart
        try:
            print("--- Starting Instamart ---")
            for item in items_list:
                await search_and_add_instamart(page, item)
            results['Swiggy Instamart'] = await page.evaluate("""
                () => {
                    let els = document.querySelectorAll("div, button, a");
                    for(let e of els){
                        if(e.textContent.includes('View Cart') && e.textContent.includes('₹')){
                            return e.innerText.split('\\n').join(' ');
                        }
                    }
                    return "Not Found";
                }
            """)
            print(f"[Instamart] Final: {results['Swiggy Instamart']}")
        except Exception as e:
            print(f"[Instamart] Failed: {e}")
            results['Swiggy Instamart'] = "Error"

        await browser.close()
        print("[System] Browser closed.")

    output = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS:**"]
    for platform, value in results.items():
        output.append(f"**{platform}**: {value}")
    
    return "\n".join(output)

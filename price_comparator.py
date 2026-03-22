import asyncio
import urllib.parse
import time
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
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        # Click Add to Cart
        await page.evaluate("""
            const buttons = document.querySelectorAll("button");
            for (let btn of buttons) {
                if (btn.textContent.includes('Add To Cart') || btn.textContent === 'Add' || btn.textContent.includes('Add to cart')) {
                    btn.click();
                    break;
                }
            }
        """)
        await asyncio.sleep(1)
    except Exception as e:
        print(f"[Zepto] Error adding {item}: {e}")

async def search_and_add_blinkit(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://blinkit.com/s/?q={query}"
    print(f"[Blinkit] Searching for: {clean_item}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.evaluate("""
            const buttons = document.querySelectorAll("div, button");
            for (let btn of buttons) {
                if (btn.textContent.trim() === 'ADD' || btn.textContent.trim() === 'Add') {
                    btn.click();
                    break;
                }
            }
        """)
        await asyncio.sleep(1)
    except Exception as e:
        print(f"[Blinkit] Error adding {item}: {e}")

async def search_and_add_instamart(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={query}"
    print(f"[Instamart] Searching for: {clean_item}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
        await asyncio.sleep(2)
        await page.evaluate("""
            const buttons = document.querySelectorAll("button, div");
            for (let btn of buttons) {
                if (btn.textContent.trim() === 'ADD' || btn.textContent.trim() === 'Add') {
                    btn.click();
                    break;
                }
            }
        """)
        await asyncio.sleep(1)
    except Exception as e:
        print(f"[Instamart] Error adding {item}: {e}")

async def compare_prices(items_text):
    if ',' in items_text:
        items_list = [i.strip() for i in items_text.split(',')]
    else:
        items_list = [i.strip() for i in items_text.split('\n')]
    items_list = [i for i in items_list if i]

    results = {}
    
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        # Single context and page to save memory on 512MB RAM
        context = await browser.new_context(
            geolocation={"latitude": 28.6139, "longitude": 77.2090},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        )
        page = await context.new_page()
        await page.route("**/*", block_aggressively)

        # Zepto
        print("--- Zepto ---")
        for item in items_list:
            await search_and_add_zepto(page, item)
        results['Zepto'] = await page.evaluate("""
            () => {
                let el = document.querySelector("[data-testid='cart-btn']");
                return el ? el.innerText.split('\\n').join(' ') : "Not Found";
            }
        """)

        # Blinkit
        print("--- Blinkit ---")
        for item in items_list:
            await search_and_add_blinkit(page, item)
        results['Blinkit'] = await page.evaluate("""
            () => {
                let els = document.querySelectorAll("div");
                for(let e of els){
                    if(e.textContent.includes('View Cart') && e.textContent.includes('₹')){
                        return e.innerText.split('\\n').join(' ');
                    }
                }
                return "Not Found";
            }
        """)

        # Instamart
        print("--- Instamart ---")
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

        await browser.close()

    output = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS (Optimized Mode):**"]
    for platform, value in results.items():
        output.append(f"**{platform}**: {value}")
    
    return "\n".join(output)

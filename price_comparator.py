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
    except Exception as e:
        print(f"[Zepto] Navigation error: {e}")
    
    await asyncio.sleep(3)
    
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

async def search_and_add_blinkit(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://blinkit.com/s/?q={query}"
    print(f"[Blinkit] Searching for: {clean_item}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"[Blinkit] Navigation error: {e}")
    
    await asyncio.sleep(3)
    
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

async def search_and_add_instamart(page, item):
    clean_item = "".join(c for c in item if c.isalnum() or c.isspace())
    query = urllib.parse.quote(clean_item)
    url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={query}"
    print(f"[Instamart] Searching for: {clean_item}")
    try:
        await page.goto(url, timeout=45000, wait_until="domcontentloaded")
    except Exception as e:
        print(f"[Instamart] Navigation error: {e}")
    
    await asyncio.sleep(3)
    
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

async def fetch_zepto(context, items_list):
    page = await context.new_page()
    await page.route("**/*", block_aggressively)
    for item in items_list:
        await search_and_add_zepto(page, item)
    
    cart_value = "Not Found"
    try:
        val = await page.evaluate("""
            let el = document.querySelector("[data-testid='cart-btn']");
            if (el) return el.innerText;
            return null;
        """)
        if val:
            cart_value = val.strip().replace('\n', ' ')
    except:
        pass
    await page.close()
    return cart_value

async def fetch_blinkit(context, items_list):
    page = await context.new_page()
    await page.route("**/*", block_aggressively)
    for item in items_list:
        await search_and_add_blinkit(page, item)
    
    cart_value = "Not Found"
    try:
        val = await page.evaluate("""
            let els = document.querySelectorAll("div");
            for(let e of els){
                if(e.textContent.includes('View Cart') && e.textContent.includes('₹')){
                    return e.innerText;
                }
            }
            return null;
        """)
        if val:
            cart_value = val.strip().replace('\n', ' ')
    except:
        pass
    await page.close()
    return cart_value

async def fetch_instamart(context, items_list):
    page = await context.new_page()
    await page.route("**/*", block_aggressively)
    for item in items_list:
        await search_and_add_instamart(page, item)
    
    cart_value = "Not Found"
    try:
        val = await page.evaluate("""
            let els = document.querySelectorAll("div, button, a");
            for(let e of els){
                if(e.textContent.includes('View Cart') && e.textContent.includes('₹')){
                    return e.innerText;
                }
            }
            return null;
        """)
        if val:
            cart_value = val.strip().replace('\n', ' ')
    except:
        pass
    await page.close()
    return cart_value

async def compare_prices(items_text):
    if ',' in items_text:
        items_list = [i.strip() for i in items_text.split(',')]
    else:
        items_list = [i.strip() for i in items_text.split('\n')]
    items_list = [i for i in items_list if i]

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            geolocation={"latitude": 28.6139, "longitude": 77.2090},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        )

        # Run all three platforms concurrently
        zepto_task = fetch_zepto(context, items_list)
        blinkit_task = fetch_blinkit(context, items_list)
        instamart_task = fetch_instamart(context, items_list)

        results_list = await asyncio.gather(zepto_task, blinkit_task, instamart_task, return_exceptions=True)
        
        platforms = ["Zepto", "Blinkit", "Swiggy Instamart"]
        results = {}
        for i, res in enumerate(results_list):
            if isinstance(res, Exception):
                results[platforms[i]] = f"Error: {res}"
            else:
                results[platforms[i]] = res

        await browser.close()

    output = ["🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n", "📊 **CART TOTALS (PARALLEL MODE):**"]
    for platform, value in results.items():
        output.append(f"**{platform}**: {value}")
    output.append("\n_Note: Teeno platforms ek saath check kiye gaye hain (Fast Mode)._")
    return "\n".join(output)

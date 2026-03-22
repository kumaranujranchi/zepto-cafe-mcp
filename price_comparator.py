import time
import urllib.parse
from playwright.sync_api import sync_playwright

def search_and_add_zepto(page, item):
    query = urllib.parse.quote(item)
    url = f"https://www.zepto.com/search?q={query}"
    print(f"[Zepto] Searching for: {item} -> {url}")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    time.sleep(4)

    # Click Add to Cart
    print(f"[Zepto] Clicking Add To Cart for {item}...")
    page.evaluate("""
        const buttons = document.querySelectorAll("button");
        for (let btn of buttons) {
            if (btn.textContent.includes('Add To Cart') || btn.textContent === 'Add' || btn.textContent.includes('Add to cart')) {
                btn.click();
                break;
            }
        }
    """)
    time.sleep(2)

def get_zepto_cart_value(page, items_list):
    for item in items_list:
        search_and_add_zepto(page, item.strip())
        
    print("[Zepto] Extracting cart value...")
    cart_value = "Not Found"
    try:
        val = page.evaluate("""
            let el = document.querySelector("[data-testid='cart-btn']");
            if (el) return el.innerText;
            return null;
        """)
        if val:
            cart_value = val.strip().replace('\n', ' ')
    except Exception as e:
        cart_value = f"Error: {e}"

    print(f"[Zepto] Cart Value extracted: {cart_value}")
    return cart_value


def search_and_add_blinkit(page, item):
    query = urllib.parse.quote(item)
    url = f"https://blinkit.com/s/?q={query}"
    print(f"[Blinkit] Searching for: {item} -> {url}")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    time.sleep(4)

    print(f"[Blinkit] Clicking ADD for {item}...")
    page.evaluate("""
        // The ADD button in blinkit search results is often a div or button
        const buttons = document.querySelectorAll("div, button");
        for (let btn of buttons) {
            if (btn.textContent.trim() === 'ADD' || btn.textContent.trim() === 'Add') {
                btn.click();
                break;
            }
        }
    """)
    time.sleep(2)

def get_blinkit_cart_value(page, items_list):
    for item in items_list:
        search_and_add_blinkit(page, item.strip())
        
    print("[Blinkit] Extracting cart value...")
    cart_value = "Not Found"
    try:
        val = page.evaluate("""
            let els = document.querySelectorAll("div");
            for(let e of els){
                // Blinkit cart bottom bar usually contains View Cart and ₹
                if(e.textContent.includes('View Cart') && e.textContent.includes('₹')){
                    return e.innerText;
                }
            }
            return null;
        """)
        if val:
            cart_value = val.strip().replace('\n', ' ')
    except Exception as e:
        cart_value = f"Error: {e}"

    print(f"[Blinkit] Cart Value extracted: {cart_value}")
    return cart_value


def search_and_add_instamart(page, item):
    query = urllib.parse.quote(item)
    url = f"https://www.swiggy.com/instamart/search?custom_back=true&query={query}"
    print(f"[Instamart] Searching for: {item} -> {url}")
    page.goto(url)
    page.wait_for_load_state("networkidle")
    time.sleep(4)

    print(f"[Instamart] Clicking Add for {item}...")
    page.evaluate("""
        const buttons = document.querySelectorAll("button, div");
        for (let btn of buttons) {
            if (btn.textContent.trim() === 'ADD' || btn.textContent.trim() === 'Add') {
                btn.click();
                break;
            }
        }
    """)
    time.sleep(2)

def get_instamart_cart_value(page, items_list):
    for item in items_list:
        search_and_add_instamart(page, item.strip())
        
    print("[Instamart] Extracting cart value...")
    cart_value = "Not Found"
    try:
        val = page.evaluate("""
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
    except Exception as e:
        cart_value = f"Error: {e}"

    print(f"[Instamart] Cart Value extracted: {cart_value}")
    return cart_value


def compare_prices(items_text):
    print(f"🚀 Starting Price Comparison (Search-Based) for: {items_text}")
    
    # Simple parsing: split by commas if commas exist, else split by newlines
    if ',' in items_text:
        items_list = [i.strip() for i in items_text.split(',')]
    else:
        items_list = [i.strip() for i in items_text.split('\n')]
        
    items_list = [i for i in items_list if i] # remove empty strings
    
    results = {}
    with sync_playwright() as p:
        # Launching Firefox in headless mode for server deployment
        browser = p.firefox.launch(headless=True)
        # Using a context with Delhi geolocation (or generic) to bypass some location prompts
        context = browser.new_context(
            geolocation={"latitude": 28.6139, "longitude": 77.2090},
            permissions=["geolocation"],
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        
        # We need a separate page for each to avoid cart conflicts across domains holding state?
        # Actually different domains don't share carts anyway.
        
        page_z = context.new_page()
        results['Zepto'] = get_zepto_cart_value(page_z, items_list)
        
        page_b = context.new_page()
        results['Blinkit'] = get_blinkit_cart_value(page_b, items_list)
        
        page_i = context.new_page()
        results['Swiggy Instamart'] = get_instamart_cart_value(page_i, items_list)
        
        browser.close()

    output = []
    output.append("🛒 **ITEMS SEARCHED:**\n" + ", ".join(items_list) + "\n")
    output.append("📊 **CART TOTALS:**")
    for platform, value in results.items():
        output.append(f"**{platform}**: {value}")
        
    output.append("\n_Note: This uses the first available item on search results, which might occasionally differ in brand or size._")
    
    return "\n".join(output)

if __name__ == "__main__":
    test_items = "Amul Taza Milk, Lay's Classic Salted"
    print(compare_prices(test_items))

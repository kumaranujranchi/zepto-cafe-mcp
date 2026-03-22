import logging
import os
import asyncio
import threading
import uvicorn
from fastapi import FastAPI
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from price_comparator import compare_prices

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Dummy Health Check Server for Koyeb ---
app = FastAPI()

@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "Price Comparator Bot is running"}

def run_health_server():
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
# -------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = (
        "👋 Welcome to the Smart Price Comparator Bot!\n\n"
        "Just send me a list of groceries you want to buy, separated by commas or new lines.\n\n"
        "Example:\n"
        "`Amul Taza Milk, Lay's Classic Salted, Bread`\n\n"
        "I will search for these items on Zepto, Blinkit, and Swiggy Instamart and return the total cart value for each so you can decide where to order from! 🛒"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, parse_mode='Markdown')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items_text = update.message.text.strip()
    
    if not items_text:
        return
        
    msg = await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=f"⏳ *Searching and calculating prices...*\nThis might take a minute depending on the number of items.",
        parse_mode='Markdown'
    )
    
    try:
        # Run playwright automation in a separate thread so we don't block the async event loop
        result = await asyncio.to_thread(compare_prices, items_text)
        
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=result,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error during comparison: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=msg.message_id,
            text=f"❌ An error occurred: {str(e)}"
        )

if __name__ == '__main__':
    # Load environment variables from .env file (if running locally)
    load_dotenv()
    
    # Start the health check server in a separate thread so it doesn't block the bot
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Ensure TELEGRAM_BOT_TOKEN is set in the environment
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set! Exiting.")
        exit(1)
        
    application = ApplicationBuilder().token(token).build()
    
    start_handler = CommandHandler('start', start)
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    logger.info("Bot started successfully. Waiting for grocery lists...")
    application.run_polling()

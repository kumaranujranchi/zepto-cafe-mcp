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

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
@app.get("/health")
def health_check(): return {"status": "ok"}

def run_health_server():
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me your grocery list, and I'll compare prices across Zepto, Blinkit, and Instamart!")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    items_text = update.message.text.strip()
    if not items_text: return
    
    status_msg = await update.message.reply_text("⏳ *Searching and calculating (Debug Mode)...*", parse_mode='Markdown')
    
    try:
        result = await compare_prices(items_text)
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text=result["text"], parse_mode='Markdown')
        
        # Send debug screenshots
        for platform, path in result.get("screenshots", {}).items():
            if os.path.exists(path):
                with open(path, 'rb') as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=f"Debug view for {platform}")
    except Exception as e:
        logger.error(f"Error: {e}")
        await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text=f"❌ Error: {str(e)}")

if __name__ == '__main__':
    load_dotenv()
    threading.Thread(target=run_health_server, daemon=True).start()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token: exit(1)
    application = ApplicationBuilder().token(token).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    application.run_polling()

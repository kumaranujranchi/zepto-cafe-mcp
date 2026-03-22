# Quick Commerce Price Comparator Bot

This project runs a Telegram bot that takes a list of grocery items and automatically searches them on three quick-commerce platforms (Zepto, Blinkit, and Swiggy Instamart) using Playwright. It calculates the total cart value for each platform and returns it, allowing you to quickly compare prices!

## Deployment (Koyeb Free Tier)

1. Go to [Koyeb.com](https://app.koyeb.com/) and click **Create App** (choose Github deployment).
2. Connect this repository.
3. **Important**: Change the service type to **Worker** (not Web Service). Yeh zaroori hai kyunki bot background me lagaatar chalega aur HTTP server nahi banayega.
4. Under `Environment Variables`, add your Telegram token:
   - `TELEGRAM_BOT_TOKEN`: Your token from @BotFather
5. Click **Deploy**! Koyeb apne aap Dockerfile se bot bana kar live kar dega.

## Usage
Simply start a chat with your Telegram Bot and send a list of queries:
```
Amul Taza Milk
Lay's Classic Salted
Aashirvaad Atta 5kg
```
The bot will return the totals across platforms.

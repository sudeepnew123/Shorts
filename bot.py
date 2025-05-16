import os
import random
from flask import Flask, request
from telegram import Update
from telegram.ext import Dispatcher, CommandHandler, CallbackContext
from shorts import get_random_short

from telegram import Bot

TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=TOKEN)
app = Flask(__name__)

dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# /start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! Use /shorts to get a random YouTube Short!")

# /shorts command
def shorts(update: Update, context: CallbackContext):
    try:
        short_url = get_random_short()
        update.message.reply_text(f"Here's a short for you:\n{short_url}")
    except Exception as e:
        update.message.reply_text("Failed to get short.")
        print("Error in /shorts:", e)

# Register handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("shorts", shorts))

# Flask webhook route
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK"

# Home route (optional)
@app.route('/')
def home():
    return 'Bot is live!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

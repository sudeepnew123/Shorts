import os
import threading
import random
import time
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler
from yt_dlp import YoutubeDL

TOKEN = os.environ.get("BOT_TOKEN")
GROUP_ID = int(os.environ.get("GROUP_ID"))
CHANNEL_URL = os.environ.get("CHANNEL_URL")  # Example: https://www.youtube.com/@SomeChannel/shorts
COOKIES_PATH = "cookies.txt"  # Optional if required
bot = Bot(token=TOKEN)
app = Flask(__name__)
dispatcher = Dispatcher(bot, update_queue=None, use_context=True)

# Download folder
DOWNLOAD_DIR = "downloads"
if not os.path.exists(DOWNLOAD_DIR):
    os.makedirs(DOWNLOAD_DIR)

# Global track of last message
last_msg_id = None

def get_channel_shorts():
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'force_generic_extractor': True,
        'cookies': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(CHANNEL_URL, download=False)
        urls = []
        for entry in info.get('entries', []):
            if 'shorts' in entry.get('url', ''):
                urls.append(f"https://www.youtube.com{entry['url']}")
        return urls

def download_video(url):
    ydl_opts = {
        'format': 'mp4',
        'outtmpl': f'{DOWNLOAD_DIR}/%(id)s.%(ext)s',
        'noplaylist': True,
        'cookies': COOKIES_PATH if os.path.exists(COOKIES_PATH) else None,
        'quiet': True
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"{DOWNLOAD_DIR}/{info['id']}.mp4"

def send_random_short(context):
    global last_msg_id
    try:
        urls = get_channel_shorts()
        if not urls:
            return

        random.shuffle(urls)
        for url in urls:
            try:
                video_path = download_video(url)
                if last_msg_id:
                    bot.delete_message(chat_id=GROUP_ID, message_id=last_msg_id)

                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton("➡️ Next", callback_data="next")]
                ])
                msg = bot.send_video(chat_id=GROUP_ID, video=open(video_path, 'rb'), reply_markup=keyboard)
                last_msg_id = msg.message_id
                break
            except:
                continue
    except Exception as e:
        print("Error sending short:", e)

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Bot is running and ready to post Shorts!")

def shorts_cmd(update, context):
    send_random_short(context)

def button(update: Update, context):
    query = update.callback_query
    query.answer()
    if query.data == "next":
        send_random_short(context)

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("shorts", shorts_cmd))
    dispatcher.add_handler(CallbackQueryHandler(button))

    print("Bot is live.")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

if __name__ == "__main__":
    main()

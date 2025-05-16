import os
import threading
import time
import requests
import yt_dlp
from flask import Flask, request
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler
from pymongo import MongoClient

# Environment variables
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
GROUP_ID = int(os.environ.get("GROUP_ID"))
MONGO_URL = os.environ.get("MONGO_URL")
COOKIES_PATH = "cookies.txt"
CHANNEL_URL = os.environ.get("CHANNEL_URL")

# Init
bot = Bot(token=TOKEN)
app = Flask(__name__)
client = MongoClient(MONGO_URL)
db = client.shorts_bot
shorts_col = db.shorts
progress_col = db.progress
dispatcher = Dispatcher(bot=bot, update_queue=None, use_context=True)

# Download Short
def download_short(url):
    ydl_opts = {
        'format': 'mp4',
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'noplaylist': True,
        'cookies': COOKIES_PATH,
        'quiet': True
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return f"downloads/{info['id']}.mp4", info['id']

# Get Shorts from Channel
def get_channel_shorts():
    ydl_opts = {
        'extract_flat': True,
        'quiet': True,
        'cookies': COOKIES_PATH
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        data = ydl.extract_info(CHANNEL_URL, download=False)
        return [entry['url'] for entry in data['entries'] if "shorts" in entry['url']]

# Post Short to Group
def post_short(video_path, video_id):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("➡️ Next", callback_data=f"next_{video_id}"),
         InlineKeyboardButton("❤️ Like", callback_data=f"like_{video_id}")]
    ])
    msg = bot.send_video(chat_id=GROUP_ID, video=open(video_path, 'rb'), reply_markup=keyboard)
    shorts_col.insert_one({"video_id": video_id, "file_id": msg.video.file_id})
    progress_col.update_one({"group": GROUP_ID}, {"$set": {"last_msg": msg.message_id}}, upsert=True)
    return msg

# Delete old message
def delete_last():
    doc = progress_col.find_one({"group": GROUP_ID})
    if doc and 'last_msg' in doc:
        try:
            bot.delete_message(chat_id=GROUP_ID, message_id=doc['last_msg'])
        except:
            pass

# /start command
def start(update, context):
    if update.effective_user.id == ADMIN_ID:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Bot is running.")

# /shorts command
def shorts_command(update, context):
    if update.effective_chat.id != GROUP_ID:
        return
    try:
        urls = get_channel_shorts()
        for url in urls[::-1]:
            video_id = url.split("=")[-1]
            if not shorts_col.find_one({"video_id": video_id}):
                video_path, vid = download_short(f"https://youtube.com/watch?v={url}")
                delete_last()
                post_short(video_path, vid)
                break
        else:
            context.bot.send_message(chat_id=GROUP_ID, text="No new Shorts found.")
    except Exception as e:
        print("Error in /shorts command:", e)
        context.bot.send_message(chat_id=GROUP_ID, text="Error fetching Shorts.")

# Button Callback Handler
def button_handler(update: Update, context):
    query = update.callback_query
    query.answer()
    if query.data.startswith("next_"):
        vid = query.data.split("_")[1]
        next_short = shorts_col.find_one({"video_id": {"$ne": vid}})
        if next_short:
            delete_last()
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("➡️ Next", callback_data=f"next_{next_short['video_id']}"),
                 InlineKeyboardButton("❤️ Like", callback_data=f"like_{next_short['video_id']}")]
            ])
            msg = bot.send_video(chat_id=GROUP_ID, video=next_short['file_id'], reply_markup=keyboard)
            progress_col.update_one({"group": GROUP_ID}, {"$set": {"last_msg": msg.message_id}}, upsert=True)
    elif query.data.startswith("like_"):
        query.edit_message_reply_markup(reply_markup=None)
        context.bot.send_message(chat_id=GROUP_ID, text=f"{query.from_user.first_name} liked this short!")

# Webhook Handler
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return 'ok'

# Main
def main():
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("shorts", shorts_command))
    dispatcher.add_handler(CallbackQueryHandler(button_handler))

if __name__ == '__main__':
    main()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))

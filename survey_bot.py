import logging
import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)
import yt_dlp

BOT_TOKEN = "8967496208:AAG67w79I71QfzSIykgFE0P8zYeNIASSQfU"

logging.basicConfig(level=logging.INFO)

QUALITIES = {
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
}

def is_twitter_url(url):
    return any(d in url for d in ["twitter.com", "x.com", "t.co"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 ربات دانلود توییتر\n\nلینک ویدیو رو بفرست تا دانلود کنم."
    )

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip().split("?")[0]
    if not is_twitter_url(url):
        await update.message.reply_text("❌ فقط لینک توییتر (x.com) قبول میکنم.")
        return

    context.user_data["url"] = url
    keyboard = [[
        InlineKeyboardButton("480p", callback_data="480p"),
        InlineKeyboardButton("720p", callback_data="720p"),
        InlineKeyboardButton("1080p", callback_data="1080p"),
    ]]
    await update.message.reply_text(
        "کیفیت ویدیو رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_quality(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    quality = query.data
    url = context.user_data.get("url")

    if not url:
        await query.edit_message_text("❌ لینک پیدا نشد. دوباره لینک بفرست.")
        return

    await query.edit_message_text(f"⏳ در حال دانلود {quality}...")

    output_path = f"/tmp/{query.id}.mp4"
    ydl_opts = {
        "format": QUALITIES[quality],
        "outtmpl": output_path,
        "quiet": True,
        "merge_output_format": "mp4",
        "noplaylist": True,
    }

    try:
        loop = asyncio.get_event_loop()
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        await loop.run_in_executor(None, download)

        if os.path.exists(output_path):
            size = os.path.getsize(output_path)
            if size > 50 * 1024 * 1024:
                await query.edit_message_text("❌ فایل بیش از ۵۰MB است و تلگرام قبول نمیکنه.")
            else:
                await query.edit_message_text("📤 در حال ارسال...")
                with open(output_path, "rb") as f:
                    await context.bot.send_video(
                        chat_id=query.message.chat_id,
                        video=f,
                        supports_streaming=True
                    )
                await query.delete_message()
            os.remove(output_path)
        else:
            await query.edit_message_text("❌ دانلود ناموفق بود.")
    except Exception as e:
        logging.error(e)
        await query.edit_message_text("❌ خطا در دانلود. لینک رو چک کن.")
        if os.path.exists(output_path):
            os.remove(output_path)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    app.add_handler(CallbackQueryHandler(handle_quality))
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()

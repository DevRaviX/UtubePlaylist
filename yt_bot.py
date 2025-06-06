import os
import subprocess
import json
from shutil import make_archive
from datetime import timedelta

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

user_links = {}
user_downloads = {}

format_map = {
    "144p": "bestvideo[height<=144]+bestaudio/best",
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "1080p": "bestvideo[height<=1080]+bestaudio/best",
    "mp3": "mp3"
}


def clean_link(url):
    url = url.split("&")[0]
    return url


def get_video_info(url, yt_format):
    try:
        result = subprocess.run(["yt-dlp", "-f", yt_format, "-j", url], stdout=subprocess.PIPE, text=True)
        info = json.loads(result.stdout)
        filesize = info.get("filesize") or info.get("filesize_approx")
        if filesize:
            size_mb = round(filesize / (1024 * 1024), 2)
            return f"💾 Estimated Size: {size_mb} MB"
        else:
            return "⚠️ Size info not available"
    except Exception as e:
        return f"❌ Error fetching info: {e}"


def get_preview_info(url):
    try:
        result = subprocess.run(["yt-dlp", "-j", url], stdout=subprocess.PIPE, text=True)
        info = json.loads(result.stdout)
        title = info.get("title", "N/A")
        duration = str(timedelta(seconds=info.get("duration", 0)))
        channel = info.get("channel", "Unknown Channel")
        return f"🎬 *Title:* {title}\n⏱ *Duration:* {duration}\n📺 *Channel:* {channel}", info.get("thumbnail")
    except:
        return "⚠️ Couldn't fetch preview info", None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Send me a YouTube link (video or playlist)!")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = clean_link(update.message.text.strip())
    user_id = update.message.from_user.id
    user_links[user_id] = link

    preview_text, thumb_url = get_preview_info(link)

    if thumb_url:
        await update.message.reply_photo(thumb_url, caption=preview_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(preview_text, parse_mode="Markdown")

    buttons = [
        [InlineKeyboardButton("🎞 144p", callback_data="144p"),
         InlineKeyboardButton("📼 360p", callback_data="360p")],
        [InlineKeyboardButton("📺 480p", callback_data="480p"),
         InlineKeyboardButton("🎥 720p", callback_data="720p")],
        [InlineKeyboardButton("🎬 1080p", callback_data="1080p")],
        [InlineKeyboardButton("🎵 MP3 (Audio Only)", callback_data="mp3")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Choose format to download:", reply_markup=reply_markup)


async def download_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    format_choice = query.data
    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.edit_message_text("❌ Link expired. Please send again.")
        return

    fmt = format_map.get(format_choice)
    output_template = os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s")

    # Playlist handling
    if "playlist?list=" in url and format_choice != "mp3":
        yt_format = "bestvideo+bestaudio/best"
    else:
        yt_format = fmt

    # Show estimated size
    size_msg = get_video_info(url, yt_format) if format_choice != "mp3" else "🎵 MP3 selected"
    await query.message.reply_text(size_msg)

    # Build download command
    cmd = ["yt-dlp", "-o", output_template]
    if format_choice == "mp3":
        cmd += ["-x", "--audio-format", "mp3"]
    else:
        cmd += ["-f", yt_format]

    cmd.append("--yes-playlist")
    cmd.append(url)

    try:
        subprocess.run(cmd, check=True)

        files = os.listdir(DOWNLOAD_DIR)
        if len(files) > 3:
            zip_path = os.path.join(DOWNLOAD_DIR, "all_files")
            make_archive(zip_path, 'zip', DOWNLOAD_DIR)
            await query.message.reply_document(open(zip_path + ".zip", "rb"))
            os.remove(zip_path + ".zip")
        else:
            for idx, file in enumerate(files, 1):
                path = os.path.join(DOWNLOAD_DIR, file)
                await query.message.reply_text(f"📤 Sending file {idx}/{len(files)}")
                await query.message.reply_document(open(path, "rb"))
                os.remove(path)

        # Update stats
        user_downloads[user_id] = user_downloads.get(user_id, 0) + 1
        await query.message.reply_text(f"✅ Total downloads by you: {user_downloads[user_id]}")

    except Exception as e:
        await query.message.reply_text(f"❌ Download failed: {e}")


# Run bot
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(download_callback))

app.run_polling()

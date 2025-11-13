import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import requests
import re

# লগিং সেটআপ
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# বট কনফিগারেশন
BOT_TOKEN = "8493215042:AAFfr5bQ7DJuPvds8VlmKlDnIQ-cOM0nJwY"  # এখানে আপনার বট টোকেন দিন
CHANNEL_USERNAME = "@your_channel"  # আপনার চ্যানেলের ইউজারনেম
GROUP_USERNAME = "@your_group"      # আপনার গ্রুপের ইউজারনেম

# ইউজার স্টেট ম্যানেজমেন্ট
user_states = {}

# চেক করে ব্যবহারকারী চ্যানেল/গ্রুপে আছে কিনা
async def is_user_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        channel_member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        group_member = await context.bot.get_chat_member(GROUP_USERNAME, user_id)
        return channel_member.status in ['member', 'administrator', 'creator'] and group_member.status in ['member', 'administrator', 'creator']
    except:
        return False

# স্টার্ট কমান্ড
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # চেক করুন ব্যবহারকারী চ্যানেল/গ্রুপে আছে কিনা
    if await is_user_member(user_id, context):
        await show_quotation_menu(update, context)
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("👥 Join Group", url=f"https://t.me/{GROUP_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ Already Joined", callback_data="check_membership")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🚀 **Welcome to Video Downloader Bot!**\n\n"
            "📋 **Requirements:**\n"
            f"1. Join our channel: {CHANNEL_USERNAME}\n"
            f"2. Join our group: {GROUP_USERNAME}\n\n"
            "After joining, click **✅ Already Joined** to continue!",
            reply_markup=reply_markup
        )

# মেম্বারশিপ চেক করার জন্য ক্যালব্যাক
async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if await is_user_member(user_id, context):
        await show_quotation_menu_from_callback(query, context)
    else:
        await query.edit_message_text(
            "❌ **You haven't joined our channel/group yet!**\n\n"
            "Please join both and try again!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Check Again", callback_data="check_membership")
            ]])
        )

# কোয়োটেশন মেনু দেখান
async def show_quotation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📸 Instagram Video Download", callback_data="instagram")],
        [InlineKeyboardButton("📘 Facebook Video Download", callback_data="facebook")],
        [InlineKeyboardButton("📺 YouTube Video Download", callback_data="youtube")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.message:
        await update.message.reply_text(
            "🎯 **Select your quotation:**\n"
            "Choose which platform you want to download from:",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            "🎯 **Select your quotation:**\n"
            "Choose which platform you want to download from:",
            reply_markup=reply_markup
        )

async def show_quotation_menu_from_callback(query, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📸 Instagram Video Download", callback_data="instagram")],
        [InlineKeyboardButton("📘 Facebook Video Download", callback_data="facebook")],
        [InlineKeyboardButton("📺 YouTube Video Download", callback_data="youtube")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✅ **Membership Verified!**\n\n"
        "🎯 **Select your quotation:**\n"
        "Choose which platform you want to download from:",
        reply_markup=reply_markup
    )

# প্ল্যাটফর্ম সিলেক্ট করার জন্য ক্যালব্যাক
async def platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    platform = query.data
    
    # ইউজার স্টেট সেট করুন
    user_states[user_id] = platform
    
    platform_names = {
        "instagram": "Instagram",
        "facebook": "Facebook", 
        "youtube": "YouTube"
    }
    
    await query.edit_message_text(
        f"🔗 **{platform_names[platform]} Video Download**\n\n"
        "Please send your video link now:\n"
        "Example: https://www.instagram.com/p/xxxxx/\n\n"
        "📝 **Send the link in this chat**"
    )

# ভিডিও লিঙ্ক প্রসেস করা
async def handle_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    video_url = update.message.text
    
    # চেক করুন ব্যবহারকারী চ্যানেল/গ্রুপে আছে কিনা
    if not await is_user_member(user_id, context):
        await update.message.reply_text("❌ Please join our channel and group first using /start command!")
        return
    
    # চেক করুন ইউজারের স্টেট আছে কিনা
    if user_id not in user_states:
        await update.message.reply_text("❌ Please select a platform first using /start command!")
        return
    
    platform = user_states[user_id]
    
    # ভিডিও ডাউনলোড শুরু করুন
    await update.message.reply_text("⏬ Downloading your video... Please wait!")
    
    try:
        video_path = await download_video(video_url, platform)
        
        if video_path:
            # ভিডিও ফাইল পাঠান
            with open(video_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption=f"✅ **Download Complete!**\n\n"
                           f"Platform: {platform.capitalize()}\n"
                           f"Enjoy your video! 🎉"
                )
            
            # টেম্প ফাইল ডিলিট করুন
            os.remove(video_path)
            
            # ইউজার স্টেট রিসেট করুন
            if user_id in user_states:
                del user_states[user_id]
                
        else:
            await update.message.reply_text("❌ Download failed! Please check your link and try again.")
    
    except Exception as e:
        logger.error(f"Download error: {e}")
        await update.message.reply_text("❌ Error downloading video! Please try again later.")

# ভিডিও ডাউনলোড ফাংশন
async def download_video(url: str, platform: str) -> str:
    try:
        ydl_opts = {
            'outtmpl': 'downloads/%(title)s.%(ext)s',
            'format': 'best',
            'quiet': True,
        }
        
        # ডাউনলোড ডিরেক্টরি তৈরি করুন
        os.makedirs('downloads', exist_ok=True)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
            
    except Exception as e:
        logger.error(f"Download error for {platform}: {e}")
        return None

# হেল্প কমান্ড
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 **Video Downloader Bot Help**\n\n"
        "📋 **Available Commands:**\n"
        "/start - Start the bot\n"
        "/help - Show this help message\n\n"
        "📱 **Supported Platforms:**\n"
        "• Instagram\n"
        "• Facebook\n"
        "• YouTube\n\n"
        "🔗 **How to use:**\n"
        "1. Use /start\n"
        "2. Join channel & group\n"
        "3. Select platform\n"
        "4. Send video link\n"
        "5. Get your video!"
    )

# মেইন ফাংশন
def main():
    # বট অ্যাপ্লিকেশন তৈরি করুন
    application = Application.builder().token(BOT_TOKEN).build()
    
    # হ্যান্ডলার যোগ করুন
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(check_membership, pattern="^check_membership$"))
    application.add_handler(CallbackQueryHandler(platform_selected, pattern="^(instagram|facebook|youtube)$"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_video_link))
    
    # বট শুরু করুন
    print("🤖 Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
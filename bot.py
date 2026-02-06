import telebot
import re
import time
import threading
from datetime import datetime, timedelta
from telebot.types import ChatPermissions

# =====================
# 🔧 CONFIG
# =====================
BOT_TOKEN = "8372879804:AAEKowoa_EaSy6TeA1aoT9jUNEm1pEeLXe8"

FORBIDDEN_WORDS = [
    "dm me",
    "inbox",
    "inbox me",
    "pm me"
]

MAX_WARNINGS = 3
AUTO_DELETE_SEC = 0
FOOTER = "THANK YOU TEAM CYBER SHR☠️"

# =====================
# ⏱ MUTE TIME
# =====================
MUTE_MINUTES = 30

# =====================
# 🔗 LINK RULES
# =====================
YOUTUBE_REGEX = re.compile(r"(youtube\.com|youtu\.be)", re.I)
LINK_REGEX = re.compile(r"https?://\S+", re.I)
# =====================

bot = telebot.TeleBot(BOT_TOKEN)
warnings = {}  # key = (chat_id, user_id)

# =====================
# 🛠 UTIL FUNCTIONS
# =====================
def is_admin(chat_id, user_id):
    try:
        return any(a.user.id == user_id for a in bot.get_chat_administrators(chat_id))
    except:
        return False

def get_username(u):
    return f"@{u.username}" if u.username else (u.first_name or "User")

def auto_delete(chat_id, msg_id, sec=AUTO_DELETE_SEC):
    def delete_later():
        time.sleep(sec)
        try:
            bot.delete_message(chat_id, msg_id)
        except:
            pass
    threading.Thread(target=delete_later, daemon=True).start()

def mute_user(chat_id, user_id):
    until = datetime.now() + timedelta(minutes=MUTE_MINUTES)
    bot.restrict_chat_member(
        chat_id,
        user_id,
        until_date=until,
        permissions=ChatPermissions(can_send_messages=False)
    )

def unmute_user(chat_id, user_id):
    bot.restrict_chat_member(
        chat_id,
        user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )

def warn_user(chat_id, user_id, user_obj, reason):
    key = (chat_id, user_id)
    warnings[key] = warnings.get(key, 0) + 1
    wc = warnings[key]
    uname = get_username(user_obj)

    if wc < MAX_WARNINGS:
        mute_user(chat_id, user_id)

        msg = bot.send_message(
            chat_id,
            f"⚠️ WARNING {wc}/{MAX_WARNINGS}\n"
            f"👤 User: {uname}\n"
            f"🚫 Reason: {reason}\n"
            f"🔇 Muted for {MUTE_MINUTES} minutes\n\n"
            f"{FOOTER}"
        )
        #auto_delete(chat_id, msg.message_id)
    else:
        bot.kick_chat_member(chat_id, user_id)
        msg = bot.send_message(
            chat_id,
            f"❌ USER KICKED\n"
            f"👤 User: {uname}\n"
            f"📛 Reason: Reached {MAX_WARNINGS} warnings\n\n"
            f"{FOOTER}"
        )
        #auto_delete(chat_id, msg.message_id)
        warnings.pop(key, None)
        
        #math captcha,👋👋👋
@bot.message_handler(content_types=['new_chat_members'])
def welcome(message):
    chat_id = message.chat.id

    for user in message.new_chat_members:
        if user.is_bot:
            continue

        username = f"@{user.username}" if user.username else user.first_name

        # generate math captcha
        a = random.randint(1, 9)
        b = random.randint(1, 9)
        answer = a + b

        captcha_users[user.id] = answer
        mute(chat_id, user.id)

        bot.send_message(
            chat_id,
            f"👋 Welcome {username}\n"
            f"🔥 Welcome to CYBER SHR Telegram Group\n\n"
            f"🧮 **Verify yourself**\n"
            f"Solve: `{a} + {b} = ?`\n\n"
            f"Type: `/verify {answer}`"
            + FOOTER,
            parse_mode="Markdown"
        )

@bot.message_handler(commands=['verify'])
def verify_user(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id not in captcha_users:
        bot.reply_to(message, "ℹ️ You are already verified.")
        return

    try:
        user_answer = int(message.text.split()[1])
    except:
        bot.reply_to(message, "❌ Wrong format. Example: `/verify 10`")
        return

    if user_answer == captcha_users[user_id]:
        unmute(chat_id, user_id)
        del captcha_users[user_id]
        bot.reply_to(message, "✅ Verification successful! You can chat now.")
    else:
        bot.reply_to(message, "❌ Wrong answer! Try again.")

# =====================
# 🚨 AUTO MODERATION
# =====================
@bot.message_handler(func=lambda m: True, content_types=["text"])
def auto_moderation(m):
    chat_id = m.chat.id
    user_id = m.from_user.id
    text = m.text.lower()

    if is_admin(chat_id, user_id):
        return

    reason = None

    for w in FORBIDDEN_WORDS:
        if w in text:
            reason = "DM / Inbox is not allowed"
            break

    if LINK_REGEX.search(text) and not YOUTUBE_REGEX.search(text):
        reason = "Only YouTube links are allowed"

    if not reason:
        return

    try:
        bot.delete_message(chat_id, m.message_id)
    except:
        pass

    warn_user(chat_id, user_id, m.from_user, reason)

# =====================
# 🧑‍💻 ADMIN COMMANDS
# =====================
@bot.message_handler(commands=["unmute"])
def cmd_unmute(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return

    if not m.reply_to_message:
        return bot.reply_to(m, "❗ Unmute করতে user এর message এ reply করো")

    user_id = m.reply_to_message.from_user.id

    bot.restrict_chat_member(
        m.chat.id,
        user_id,
        permissions=telebot.types.ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )

    bot.reply_to(
        m,
        f"✅ User Unmuted Successfully\n"
        f"👤 User: {get_username(m.reply_to_message.from_user)}\n\n"
        f"{FOOTER}"
    )
@bot.message_handler(commands=["unmute"])
def cmd_unmute(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return

    chat_id = m.chat.id

    # Case 1: reply based unmute
    if m.reply_to_message:
        uid = m.reply_to_message.from_user.id
        unmute_user(chat_id, uid)
        bot.reply_to(m, "✅ User unmuted")
        return

    # Case 2: /unmute @username
    parts = m.text.split()
    if len(parts) == 2 and parts[1].startswith("@"):
        username = parts[1][1:].lower()
        try:
            for member in bot.get_chat_administrators(chat_id):
                pass
            members = bot.get_chat_members_count(chat_id)
        except:
            bot.reply_to(m, "❌ Cannot fetch members")
            return

        try:
            chat = bot.get_chat(chat_id)
            for member in bot.get_chat_administrators(chat_id):
                pass
        except:
            pass

        try:
            for user in bot.get_chat_administrators(chat_id):
                pass
        except:
            pass

        try:
            for member in bot.get_chat_administrators(chat_id):
                pass
        except:
            pass

        try:
            for member in bot.get_chat_administrators(chat_id):
                pass
        except:
            pass

        # Telegram API limitation: direct username lookup not allowed
        bot.reply_to(
            m,
            "ℹ️ @username unmute works **only if the user recently sent a message**.\n"
            "👉 Best method: reply to user's message and use /unmute"
        )
        return

    bot.reply_to(m, "❗ Usage:\n/unmute (reply)\n/unmute @username")

@bot.message_handler(commands=["resetwarn"])
def cmd_reset(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    if not m.reply_to_message:
        return bot.reply_to(m, "Reply to a user message.")
    key = (m.chat.id, m.reply_to_message.from_user.id)
    warnings.pop(key, None)
    bot.reply_to(m, f"✅ Warnings reset\n{FOOTER}")

@bot.message_handler(commands=["checkwarn"])
def cmd_check(m):
    if not is_admin(m.chat.id, m.from_user.id):
        return
    if not m.reply_to_message:
        return bot.reply_to(m, "Reply to a user message.")
    key = (m.chat.id, m.reply_to_message.from_user.id)
    wc = warnings.get(key, 0)
    bot.reply_to(m, f"⚠️ Warnings: {wc}/{MAX_WARNINGS}\n{FOOTER}")

@bot.message_handler(commands=["rules"])
def rules(m):
    bot.reply_to(
        m,
        "📜 𝗚𝗥𝗢𝗨𝗣 𝗥𝗨𝗟𝗘𝗦📢 \n"
    
        "1️⃣ 𝙽𝙾 𝚂𝙿𝙰𝙼𝙼𝙸𝙽𝙶 ❌\n"
        "2️⃣ 𝙳𝙼 / 𝙸𝚗𝚋𝚘𝚡 𝚁𝙴𝚀𝚄𝚂𝚃 𝙽𝙾𝚃 𝙰𝙻𝙻𝙾𝚆𝙳\n"
        "3️⃣ 𝙽𝙾 𝚂𝙴𝙻𝙻𝙸𝙽𝙶❌\n"
        "3️⃣ 𝙽𝙾 𝙿𝚁𝙾𝙼𝙾𝚃𝙸𝙾𝙽❌\n"
        "4️⃣ 𝙽𝙾 𝚂𝙷𝙰𝚁𝙸𝙽𝙶 𝙰𝙽𝚈 𝚂𝙾𝙲𝙸𝙰𝙻𝙼𝙴𝙳𝙸𝙰 𝚅𝙸𝙳𝙴𝙾 𝙻𝙸𝙽𝙺❌\n"
        "5️⃣ 𝙽𝙾 𝚂𝙷𝙰𝚁𝙸𝙽𝙶 𝙾𝙵 𝙰𝙳𝚄𝙻𝚃 𝚅𝙸𝙳𝙴𝙾🔞\n"
        "6️⃣ 𝙽𝙾 𝚂𝙷𝙰𝚁𝙸𝙽𝙶\n"
        "7️⃣ 3 𝚆𝙰𝚁𝙽𝙸𝙽𝙶𝚂 ⚠️ = 𝙺𝙸𝙲𝙺 🚫\n"
        "8️⃣ 𝙰𝙽𝚈 𝚂𝙴𝚁𝙸𝙾𝚄𝚂 𝙿𝚁𝙾𝙱𝙻𝙴𝙼 𝙲𝙾𝙽𝚃𝙰𝙲𝚃 𝙶𝚁𝙾𝚄𝙿 𝙰𝙳𝙼𝙸𝙽𝚂\n"
        f"{FOOTER}"
    )

# =====================
print("🚨 Moderation Bot Running (30-minute mute + unmute command)...")
bot.infinity_polling()

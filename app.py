import os
import sys
import telebot
import subprocess
import signal
import re
import time
import logging
import threading
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

bot = telebot.TeleBot("7440766590:AAE3x9E1C_D9jY4p8cJVbC3KP21FkOMk5xk", parse_mode="HTML")
logging.basicConfig(level=logging.INFO)

if not os.path.exists("user_bots"):
    os.makedirs("user_bots")

running_bots = {}
user_bot_limits = {}
user_sessions = {}
bot_start_times = {}
bot_error_logs = {}
user_files_count = {}
OWNER_ID = 6067142319

def create_main_keyboard():
    return ReplyKeyboardMarkup(row_width=2, resize_keyboard=True).add(
        KeyboardButton("🤖 New Bot"),
        KeyboardButton("📂 My Bots"),
        KeyboardButton("✏️ Edit Bot"),
        KeyboardButton("🗑️ Delete Bot"),
        KeyboardButton("🔄 Update Channel"),
        KeyboardButton("📞 Contact Owner")
    )

def create_cancel_keyboard():
    return ReplyKeyboardMarkup(resize_keyboard=True).add("🚫 Cancel")

@bot.message_handler(commands=['upgrade'])
def upgrade_user(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        _, user_id, new_limit = message.text.split()
        user_id = int(user_id)
        new_limit = int(new_limit)
        user_bot_limits[user_id] = new_limit
        bot.send_message(message.chat.id, f"User {user_id} upgraded to {new_limit} bot limit")
    except:
        bot.send_message(message.chat.id, "Usage: /upgrade USER_ID NEW_LIMIT")

@bot.message_handler(commands=['downgrade'])
def downgrade_user(message):
    if message.from_user.id != OWNER_ID:
        return
    try:
        _, user_id = message.text.split()
        user_id = int(user_id)
        user_bot_limits[user_id] = 3
        bot.send_message(message.chat.id, f"User {user_id} downgraded to free tier (3 bots)")
    except:
        bot.send_message(message.chat.id, "Usage: /downgrade USER_ID")

def start_script(chat_id, script_path, bot_name):
    try:
        process = subprocess.Popen(
            ["python", script_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            text=True
        )
        
        running_bots.setdefault(chat_id, {})[bot_name] = process
        bot_start_times[bot_name] = time.time()
        bot_error_logs[bot_name] = ""
        
        def monitor_process():
            while True:
                if process.poll() is not None:
                    error_log = process.stderr.read()
                    if error_log:
                        bot_error_logs[bot_name] = error_log[-3000:]
                        bot.send_message(chat_id, f"{bot_name} crashed\n\n{error_log[-3000:]}")
                    running_bots[chat_id].pop(bot_name, None)
                    break
                time.sleep(5)
        
        threading.Thread(target=monitor_process, daemon=True).start()
    except Exception as e:
        bot.send_message(chat_id, f"Failed to start {bot_name}:\n{str(e)[:3000]}", reply_markup=create_main_keyboard())

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "None"
    files_count = user_files_count.get(user_id, 0)
    limit = user_bot_limits.get(user_id, 3)
    status = "Free User" if limit <= 3 else "Premium User"
    
    welcome_msg = f"""
<b>Welcome, {name}!</b>

🆔 <b>Your User ID:</b> <code>{user_id}</code>
✳️ <b>Username:</b> {username}
🔰 <b>Your Status:</b> {status}
📁 <b>Files Uploaded:</b> {files_count} / {limit}

🤖 <b>Host & run python (.py) script</b>
   Upload single script file or direct code

👇 <b>Use buttons below:</b>
    """
    
    bot.send_message(message.chat.id, welcome_msg, reply_markup=create_main_keyboard())

@bot.message_handler(func=lambda msg: msg.text == "🔄 Update Channel")
def update_channel(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Join Update Group", url="https://t.me/starexxchat"))
    bot.send_message(message.chat.id, "Join our update channel for latest news:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "📞 Contact Owner")
def contact_owner(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Contact Owner", url="https://t.me/starexx7"))
    bot.send_message(message.chat.id, "Contact the bot owner for support:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text == "🤖 New Bot")
def new_bot(message):
    if message.chat.type != "private":
        return
    
    user_id = message.from_user.id
    current_bots = len(running_bots.get(user_id, {}))
    limit = user_bot_limits.get(user_id, 3)
    
    if current_bots >= limit:
        bot.send_message(message.chat.id, f"You've reached your limit of {limit} bots", reply_markup=create_main_keyboard())
        return
    
    user_sessions[user_id] = {"action": "newbot"}
    bot.send_message(message.chat.id, "Enter a name for your new bot:", reply_markup=create_cancel_keyboard())

@bot.message_handler(func=lambda msg: user_sessions.get(msg.from_user.id, {}).get("action") == "newbot")
def receive_bot_name(message):
    if message.text == "🚫 Cancel":
        user_sessions.pop(message.from_user.id)
        bot.send_message(message.chat.id, "Cancelled", reply_markup=create_main_keyboard())
        return
    
    bot_name = message.text.strip()
    if not re.match(r"^[a-zA-Z0-9_-]{3,20}$", bot_name):
        bot.send_message(message.chat.id, "Invalid name (3-20 chars, a-z, 0-9, _-)", reply_markup=create_cancel_keyboard())
        return
    
    user_sessions[message.from_user.id] = {"action": "get_code", "bot_name": bot_name}
    bot.send_message(message.chat.id, f"Send Python code for {bot_name} (text or .py file):", reply_markup=create_cancel_keyboard())

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if user_sessions.get(message.from_user.id, {}).get("action") == "get_code":
        if message.document.file_size > 1024*1024:
            bot.send_message(message.chat.id, "File too large (max 1MB)", reply_markup=create_cancel_keyboard())
            return
        
        bot_name = user_sessions[message.from_user.id]["bot_name"]
        file_path = os.path.join("user_bots", f"{bot_name}.py")
        
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(file_path, "wb") as f:
            f.write(downloaded_file)
        
        user_files_count[message.from_user.id] = user_files_count.get(message.from_user.id, 0) + 1
        bot.send_message(message.chat.id, f"Bot {bot_name} started successfully!", reply_markup=create_main_keyboard())
        start_script(message.chat.id, file_path, bot_name)
        user_sessions.pop(message.from_user.id)

@bot.message_handler(func=lambda msg: user_sessions.get(msg.from_user.id, {}).get("action") == "get_code")
def handle_code(message):
    if message.text == "🚫 Cancel":
        user_sessions.pop(message.from_user.id)
        bot.send_message(message.chat.id, "Cancelled", reply_markup=create_main_keyboard())
        return
    
    bot_name = user_sessions[message.from_user.id]["bot_name"]
    file_path = os.path.join("user_bots", f"{bot_name}.py")
    
    with open(file_path, "w") as f:
        f.write(message.text)
    
    bot.send_message(message.chat.id, f"Bot {bot_name} started successfully!", reply_markup=create_main_keyboard())
    start_script(message.chat.id, file_path, bot_name)
    user_sessions.pop(message.from_user.id)

@bot.message_handler(func=lambda msg: msg.text == "📂 My Bots")
def list_bots(message):
    user_id = message.from_user.id
    if user_id not in running_bots or not running_bots[user_id]:
        bot.send_message(message.chat.id, "You have no running bots", reply_markup=create_main_keyboard())
        return
    
    markup = InlineKeyboardMarkup()
    for name in running_bots[user_id]:
        markup.add(InlineKeyboardButton(name, callback_data=f"info_{name}"))
    
    current_bots = len(running_bots[user_id])
    limit = user_bot_limits.get(user_id, 3)
    bot.send_message(message.chat.id, f"Your bots ({current_bots}/{limit}):", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('info_'))
def show_bot_info(call):
    bot_name = call.data[5:]
    user_id = call.from_user.id
    
    if user_id not in running_bots or bot_name not in running_bots[user_id]:
        bot.answer_callback_query(call.id, "Bot not found")
        return
    
    process = running_bots[user_id][bot_name]
    status = "Online" if process.poll() is None else "Offline"
    uptime = time.strftime("%H:%M:%S", time.gmtime(time.time() - bot_start_times.get(bot_name, time.time())))
    logs = bot_error_logs.get(bot_name, "No logs available")
    
    info_text = f"""
<b>Bot Dashboard: {bot_name}</b>

<b>Status:</b> {status}
<b>Uptime:</b> {uptime}

<b>Logs:</b>
<code>{logs}</code>
"""
    
    bot.edit_message_text(info_text, call.message.chat.id, call.message.message_id, parse_mode="HTML")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if message.from_user.id != OWNER_ID:
        return
    
    if not message.reply_to_message:
        bot.send_message(message.chat.id, "Reply to a message to broadcast")
        return
    
    users = set(running_bots.keys())
    success = 0
    
    for user in users:
        try:
            if message.reply_to_message.photo:
                bot.send_photo(user, message.reply_to_message.photo[-1].file_id, 
                             caption=message.reply_to_message.caption)
            elif message.reply_to_message.document:
                bot.send_document(user, message.reply_to_message.document.file_id,
                                caption=message.reply_to_message.caption)
            else:
                bot.send_message(user, message.reply_to_message.text)
            success += 1
        except:
            pass
    
    bot.send_message(message.chat.id, f"Broadcast sent to {success} users")

print("Bot is running...")
bot.infinity_polling()

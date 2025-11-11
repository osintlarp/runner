import os
import json
import time
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
)

BOT_TOKEN = "DEIN_TELEGRAM_BOT_TOKEN_HIER"
MAP_DIR = os.path.join(os.path.expanduser("~"), "map")
MAP_FILE = os.path.join(MAP_DIR, "user_map.json")
TOKENS_DIR = os.path.join(MAP_DIR, "tokens")
TOKENS_FILE = os.path.join(TOKENS_DIR, "user_tokens.json")
RATE_FILE = os.path.join(MAP_DIR, "rate_limits.json")
DEFAULT_TOKEN = "BOT-QWPPXCYNNMJUWGAG-X"
WAITING_FOR_TOKEN = 1
WAITING_FOR_IG_USERNAME = 2
WAITING_FOR_REDDIT_USER = 3
RATE_LIMIT = 5
RATE_RESET = 3600

def ensure_dirs():
    os.makedirs(MAP_DIR, exist_ok=True)
    os.makedirs(TOKENS_DIR, exist_ok=True)
    for f in [TOKENS_FILE, RATE_FILE]:
        if not os.path.exists(f):
            with open(f, "w", encoding="utf-8") as x:
                json.dump({}, x, indent=2)

def load_json(p):
    try:
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_json(p, data):
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def is_token_valid(token):
    if token == DEFAULT_TOKEN:
        return True
    m = load_json(MAP_FILE)
    for v in m.values():
        try:
            if v.get("api_key") == token:
                return True
        except:
            continue
    return False

def store_user_token(user_id, token):
    data = load_json(TOKENS_FILE)
    data[str(user_id)] = token
    save_json(TOKENS_FILE, data)

def get_user_token(user_id):
    data = load_json(TOKENS_FILE)
    return data.get(str(user_id))

def check_rate_limit(user_id):
    data = load_json(RATE_FILE)
    u = str(user_id)
    now = time.time()
    if u not in data:
        data[u] = {"count": 0, "reset": now + RATE_RESET}
    entry = data[u]
    if now > entry["reset"]:
        entry["count"] = 0
        entry["reset"] = now + RATE_RESET
    if entry["count"] >= RATE_LIMIT:
        save_json(RATE_FILE, data)
        return False
    entry["count"] += 1
    data[u] = entry
    save_json(RATE_FILE, data)
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Send token", callback_data="send_token"),
            InlineKeyboardButton("Proceed with limits", callback_data="proceed_limits")
        ],
        [
            InlineKeyboardButton("Get token", url="https://vaul3t.org/dashboard")
        ]
    ])
    await update.message.reply_text(
        "Hello,\n\nSend VAUL3T API token or proceed with rate limits\n\nRate limits : 5/h",
        reply_markup=keyboard
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "send_token":
        context.user_data["awaiting_token"] = True
        await query.message.reply_text("Please enter your VAUL3T API token.")
    elif query.data == "proceed_limits":
        store_user_token(user_id, DEFAULT_TOKEN)
        await query.message.reply_text("Proceeding without token. You will have 5 lookups per hour.")

async def handle_token_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_token"):
        return
    token = update.message.text.strip()
    user_id = update.effective_user.id
    if is_token_valid(token):
        store_user_token(user_id, token)
        context.user_data.pop("awaiting_token", None)
        await update.message.reply_text("API Token Set. You can now use /instagram or /report_reddit_user.")
    else:
        await update.message.reply_text("Invalid token. Please try again or proceed with limits.")

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    if not token:
        token = DEFAULT_TOKEN
        store_user_token(user_id, token)
        await update.message.reply_text("No token found, proceeding with 5 lookups per hour.")
    if token == DEFAULT_TOKEN:
        if not check_rate_limit(user_id):
            await update.message.reply_text("Rate limit reached (5 lookups/hour). Please wait before retrying.")
            return ConversationHandler.END
    await update.message.reply_text("Please enter the Instagram username to search for:")
    context.user_data["vaul3t_token"] = token
    return WAITING_FOR_IG_USERNAME

async def handle_ig_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    token = context.user_data.get("vaul3t_token") or get_user_token(update.effective_user.id)
    chat_id = update.effective_chat.id
    wait_msg = await update.message.reply_text("Please wait....")
    url = f"https://api.vaul3t.org/v1/osint/instagram?username={username}"
    headers = {"Authorization": token}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)
        except: pass
        await update.message.reply_text("Error, contact Admin")
        return ConversationHandler.END
    if resp.status_code != 200:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)
        except: pass
        await update.message.reply_text("Error, contact Admin")
        return ConversationHandler.END
    try:
        data = resp.json()
    except:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)
        except: pass
        await update.message.reply_text("Error, contact Admin")
        return ConversationHandler.END
    try: await context.bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)
    except: pass
    out_lines = []
    d = data.get("data", {})
    wanted = [
        "autosend_disabled","can_email_reset","can_flashcall_reset",
        "can_p2s_reset","can_sms_reset","can_wa_reset",
        "fb_login_option","has_valid_phone","obfuscated_email",
        "obfuscated_phone","wa_account_recovery_type"
    ]
    for k in wanted:
        out_lines.append(f"{k}: {d.get(k,'N/A')}")
    user_obj = d.get("user",{})
    out_lines.append("")
    out_lines.append("user:")
    out_lines.append(f" is_private: {user_obj.get('is_private','N/A')}")
    out_lines.append(f" is_threads_only_user: {user_obj.get('is_threads_only_user','N/A')}")
    out_lines.append(f" is_verified: {user_obj.get('is_verified','N/A')}")
    out_lines.append(f" full_name: {user_obj.get('full_name','N/A')}")
    out_lines.append(f" id: {user_obj.get('id','N/A')}")
    out_lines.append(f" fbid_v2: {user_obj.get('fbid_v2','N/A')}")
    out_lines.append(f" username: {user_obj.get('username','N/A')}")
    message_text = "```\n" + "\n".join(out_lines) + "\n```"
    try:
        await update.message.reply_markdown_v2(message_text)
    except:
        await update.message.reply_text("\n".join(out_lines))
    return ConversationHandler.END

async def report_reddit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    token = get_user_token(user_id)
    if not token:
        token = DEFAULT_TOKEN
        store_user_token(user_id, token)
        await update.message.reply_text("No token found, proceeding with 5 reports per hour.")
    if token == DEFAULT_TOKEN:
        if not check_rate_limit(user_id):
            await update.message.reply_text("Rate limit reached (5 reports/hour). Please wait before retrying.")
            return ConversationHandler.END
    await update.message.reply_text("Please enter a valid Reddit user ID to report:")
    context.user_data["vaul3t_token"] = token
    return WAITING_FOR_REDDIT_USER

async def handle_reddit_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reddit_id = update.message.text.strip()
    token = context.user_data.get("vaul3t_token") or get_user_token(update.effective_user.id)
    chat_id = update.effective_chat.id
    wait_msg = await update.message.reply_text("Reporting user, please wait...")
    url = f"https://api.vaul3t.org/v1/osint/reddit/report_user?userID={reddit_id}"
    headers = {"Authorization": token}
    try:
        resp = requests.get(url, headers=headers, timeout=30)
    except:
        try: await context.bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)
        except: pass
        await update.message.reply_text("Error, contact Admin")
        return ConversationHandler.END
    try: await context.bot.delete_message(chat_id=chat_id, message_id=wait_msg.message_id)
    except: pass
    if resp.status_code != 200:
        await update.message.reply_text(f"Error: {resp.text}")
        return ConversationHandler.END
    try:
        data = resp.json()
    except:
        await update.message.reply_text("Error parsing response")
        return ConversationHandler.END
    try:
        report_details = data["data"]["reportUserDetails"]
        out_text = f"__typename: {report_details.get('__typename','N/A')}\nok: {report_details.get('ok',False)}\nreported: {report_details.get('ok',False)}"
        await update.message.reply_text(out_text)
    except Exception as e:
        await update.message.reply_text(f"Error processing response: {str(e)}")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Canceled.")
    return ConversationHandler.END

def main():
    ensure_dirs()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(button_handler))
    conv_token = ConversationHandler(
        entry_points=[],
        states={WAITING_FOR_TOKEN:[MessageHandler(filters.TEXT & (~filters.COMMAND), handle_token_message)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    conv_ig = ConversationHandler(
        entry_points=[CommandHandler("instagram", instagram_command)],
        states={WAITING_FOR_IG_USERNAME:[MessageHandler(filters.TEXT & (~filters.COMMAND), handle_ig_username)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    conv_reddit = ConversationHandler(
        entry_points=[CommandHandler("report_reddit_user", report_reddit_command)],
        states={WAITING_FOR_REDDIT_USER: [MessageHandler(filters.TEXT & (~filters.COMMAND), handle_reddit_user)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv_token)
    app.add_handler(conv_ig)
    app.add_handler(conv_reddit)
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()

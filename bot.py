import os
import json
import requests
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

BOT_TOKEN = "DEIN_TELEGRAM_BOT_TOKEN_HIER"

MAP_DIR = os.path.join(os.path.expanduser("~"), "map")
MAP_FILE = os.path.join(MAP_DIR, "user_map.json")
TOKENS_DIR = os.path.join(MAP_DIR, "tokens")
TOKENS_FILE = os.path.join(TOKENS_DIR, "user_tokens.json")

WAITING_FOR_TOKEN = 1
WAITING_FOR_IG_USERNAME = 2

def ensure_dirs():
    os.makedirs(MAP_DIR, exist_ok=True)
    os.makedirs(TOKENS_DIR, exist_ok=True)
    if not os.path.exists(TOKENS_FILE):
        with open(TOKENS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)

def load_map():
    try:
        with open(MAP_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def is_token_valid(token):
    m = load_map()
    for v in m.values():
        try:
            if v.get("api_key") == token:
                return True
        except:
            continue
    return False

def store_user_token(user_id, token):
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    data[str(user_id)] = token
    with open(TOKENS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def get_user_token(user_id):
    try:
        with open(TOKENS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get(str(user_id))
    except:
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("I dont own one", url="https://vaul3t.org/dashboard")]])
    await update.message.reply_text(
        "Hello, Please enter a valid VAUL3T API token , this will be used to make your request .",
        reply_markup=keyboard
    )
    return WAITING_FOR_TOKEN

async def handle_token_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    user_id = update.effective_user.id
    if is_token_valid(token):
        store_user_token(user_id, token)
        await update.message.reply_text("API Token Set, Use commands to serach for user")
        return ConversationHandler.END
    else:
        await update.message.reply_text("Token invalid. Please enter a valid token or visit the dashboard (button).")
        return WAITING_FOR_TOKEN

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = get_user_token(update.effective_user.id)
    if not token:
        await update.message.reply_text("You don't have a token set. Please send your VAUL3T token first (use /start).")
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

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Canceled.")
    return ConversationHandler.END

def main():
    ensure_dirs()
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    conv_token = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_FOR_TOKEN:[MessageHandler(filters.TEXT & (~filters.COMMAND), handle_token_message)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        name="token_conv",
        persistent=False
    )
    conv_ig = ConversationHandler(
        entry_points=[CommandHandler("instagram", instagram_command)],
        states={WAITING_FOR_IG_USERNAME:[MessageHandler(filters.TEXT & (~filters.COMMAND), handle_ig_username)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        name="ig_conv",
        persistent=False
    )
    app.add_handler(conv_token)
    app.add_handler(conv_ig)
    app.run_polling()

if __name__ == "__main__":
    main()

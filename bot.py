import os, json, secrets, time, requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters
)

BOT_TOKEN = "DEIN_BOT_TOKEN"
DOMAIN = "https://vaul3t.org"
USER_DIR = "/var/www/users"
CONNECT_FILE = os.path.join(USER_DIR, "connect.json")
MAP_DIR = os.path.join(os.path.expanduser("~"), "map")
MAP_FILE = os.path.join(MAP_DIR, "user_map.json")

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=4)

def is_connected(telegram_id):
    user_map = load_json(MAP_FILE)
    telegram_id = str(telegram_id)
    for v in user_map.values():
        if isinstance(v, dict) and v.get("telegram_id") == telegram_id:
            return True
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Hello, Please make sure to connect your VAUL3T account using /connect before executing commands\n\nAll requests will automatically be made with your VAUL3T API token.\n\nThis means it affects your API limits. The standard limitation is 200 requests per month with basic endpoints.\n\nHigher endpoints require a VIP account type.\n\nIt’s recommended to use the API instead of the Bot but not necessary."
    keyboard = [[InlineKeyboardButton("Create Account", url=f"{DOMAIN}/register")],[InlineKeyboardButton("Connect", callback_data="connect_now")]]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    if is_connected(telegram_id):
        await update.message.reply_text("User already connected.")
        return
    connect_data = load_json(CONNECT_FILE)
    sha = secrets.token_hex(20)
    connect_data[sha] = {"telegram_id": telegram_id,"created_at": int(time.time())}
    save_json(CONNECT_FILE, connect_data)
    link = f"{DOMAIN}/connect/account?provider=telegram&sha={sha}"
    keyboard = [[InlineKeyboardButton("Connect", url=link)]]
    await update.message.reply_text("Connect using this link:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "connect_now":
        telegram_id = query.from_user.id
        if is_connected(telegram_id):
            await query.edit_message_text("User already connected.")
            return
        connect_data = load_json(CONNECT_FILE)
        sha = secrets.token_hex(20)
        connect_data[sha] = {"telegram_id": telegram_id,"created_at": int(time.time())}
        save_json(CONNECT_FILE, connect_data)
        link = f"{DOMAIN}/connect/account?provider=telegram&sha={sha}"
        keyboard = [[InlineKeyboardButton("Connect", url=link)]]
        await query.edit_message_text("Connect using this link:", reply_markup=InlineKeyboardMarkup(keyboard))

async def instagram_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = str(update.effective_user.id)
    user_map = load_json(MAP_FILE)
    connected_user = None
    for v in user_map.values():
        if isinstance(v, dict) and v.get("telegram_id") == telegram_id:
            connected_user = v
            break
    if not connected_user:
        text = "Hello, Please make sure to connect your VAUL3T account using /connect before executing commands\n\nAll requests will automatically be made with your VAUL3T API token.\n\nUse /connect to link your account."
        await update.message.reply_text(text)
        return
    await update.message.reply_text("Enter a valid Instagram username:")

    def check_username(msg):
        return msg.from_user.id == update.effective_user.id

    response = await context.bot.wait_for_message(filters=filters.TEXT, check=check_username)
    username = response.text.strip()
    api_key = connected_user.get("api_key")
    url = f"https://api.vaul3t.org/v1/osint/instagram?username={username}"
    headers = {"Authorization": api_key}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        data = r.json()
    except Exception as e:
        await update.message.reply_text(f"Error fetching Instagram data: {e}")
        return
    if not data.get("success"):
        await update.message.reply_text("Failed to retrieve data.")
        return
    user_data = data.get("data", {})
    user_info = user_data.get("user", {})
    output = {
        "can_email_reset": user_data.get("can_email_reset"),
        "can_flashcall_reset": user_data.get("can_flashcall_reset"),
        "can_p2s_reset": user_data.get("can_p2s_reset"),
        "can_sms_reset": user_data.get("can_sms_reset"),
        "can_wa_reset": user_data.get("can_wa_reset"),
        "fb_login_option": user_data.get("fb_login_option"),
        "has_valid_phone": user_data.get("has_valid_phone"),
        "obfuscated_email": user_data.get("obfuscated_email"),
        "obfuscated_phone": user_data.get("obfuscated_phone"),
        "wa_account_recovery_type": user_data.get("wa_account_recovery_type"),
        "username": user_info.get("username"),
        "user_id": user_info.get("pk"),
        "full_name": user_info.get("full_name"),
        "multiple_users_found": user_data.get("multiple_users_found")
    }
    message_text = "```\n" + json.dumps(output, indent=4) + "\n```"
    await update.message.reply_text(message_text, parse_mode="Markdown")

async def block_unconnected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    if not is_connected(telegram_id):
        await update.message.reply_text("You must connect your VAUL3T account first.\nUse /connect")
        return
    await update.message.reply_text("Command executed successfully.")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("connect", connect_command))
app.add_handler(CallbackQueryHandler(button_handler))
app.add_handler(CommandHandler("instagram", instagram_command))
app.add_handler(MessageHandler(filters.COMMAND, block_unconnected))
app.add_handler(MessageHandler(filters.TEXT, block_unconnected))
app.run_polling()

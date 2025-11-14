import os, json, secrets, time
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
    text = (
        "Hello, Please make sure to connect your VAUL3T account using /connect before executing commands\n\n"
        "All requests will automatically be made with your VAUL3T API token.\n\n"
        "This means it affects your API limits. The standard limitation is 200 requests per month with basic endpoints.\n\n"
        "Higher endpoints require a VIP account type.\n\n"
        "It’s recommended to use the API instead of the Bot but not necessary."
    )

    keyboard = [
        [InlineKeyboardButton("Create Account", url=f"{DOMAIN}/register")],
        [InlineKeyboardButton("Connect", callback_data="connect_now")]
    ]

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id

    if is_connected(telegram_id):
        await update.message.reply_text("User already connected.")
        return

    connect_data = load_json(CONNECT_FILE)
    sha = secrets.token_hex(20)

    connect_data[sha] = {
        "telegram_id": telegram_id,
        "created_at": int(time.time())
    }

    save_json(CONNECT_FILE, connect_data)

    link = f"{DOMAIN}/connect/account?provider=telegram&sha={sha}"

    keyboard = [
        [InlineKeyboardButton("Connect", url=link)]
    ]

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

        connect_data[sha] = {
            "telegram_id": telegram_id,
            "created_at": int(time.time())
        }

        save_json(CONNECT_FILE, connect_data)

        link = f"{DOMAIN}/connect/account?provider=telegram&sha={sha}"

        keyboard = [
            [InlineKeyboardButton("Connect", url=link)]
        ]

        await query.edit_message_text("Connect using this link:", reply_markup=InlineKeyboardMarkup(keyboard))

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
app.add_handler(MessageHandler(filters.COMMAND, block_unconnected))
app.add_handler(MessageHandler(filters.TEXT, block_unconnected))

app.run_polling()

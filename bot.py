import os, json, secrets, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, MessageHandler, Filters

BOT_TOKEN = "DEIN_BOT_TOKEN"
DOMAIN = "https://vaul3t.org"

USER_DIR = "/var/www/users"
CONNECT_FILE = os.path.join(USER_DIR, "connect.json")
MAP_FILE = "root/map/user_map.json"

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

def start(update: Update, context: CallbackContext):
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

    update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

def connect_command(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id

    if is_connected(telegram_id):
        update.message.reply_text("User already connected.")
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

    update.message.reply_text("Connect using this link:", reply_markup=InlineKeyboardMarkup(keyboard))

def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data == "connect_now":
        telegram_id = query.from_user.id

        if is_connected(telegram_id):
            query.edit_message_text("User already connected.")
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

        query.edit_message_text("Connect using this link:", reply_markup=InlineKeyboardMarkup(keyboard))

def block_unconnected(update: Update, context: CallbackContext):
    telegram_id = update.effective_user.id

    if not is_connected(telegram_id):
        update.message.reply_text("You must connect your VAUL3T account first.\nUse /connect")
        return

    update.message.reply_text("Command executed successfully.")

updater = Updater(BOT_TOKEN)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CommandHandler("connect", connect_command))
dp.add_handler(MessageHandler(Filters.command, block_unconnected))
dp.add_handler(MessageHandler(Filters.text, block_unconnected))
dp.add_handler(MessageHandler(Filters.callback_query, button_handler))

dp.add_handler(MessageHandler(Filters.all, block_unconnected))

updater.start_polling()
updater.idle()

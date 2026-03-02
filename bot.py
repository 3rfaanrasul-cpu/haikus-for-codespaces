import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from supabase import create_client, Client
import os
import random

# ---------- CONFIGURATION ----------
BOT_TOKEN = "8652283982:AAEn5auHG4Xr7UXMAact6F6EI7k7Qfi7tzU"
SUPABASE_URL = "https://mxmxjnlhevtimoxgkxqg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im14bXhqbmxoZXZ0aW1veGdreHFnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzI0ODgzMzQsImV4cCI6MjA4ODA2NDMzNH0.LgbS0GnQq-EVsxm1QFOHuj1UQ_On_8IT36Q8lGnhBaQ"
ADMIN_USER_ID = 5971083539  # Your Telegram user ID

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------- LOGGING ----------
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)

# ---------- HELPER FUNCTIONS ----------
def get_user(user_id):
    response = supabase.table("users").select("*").eq("user_id", user_id).execute()
    if not response.data:
        supabase.table("users").insert({"user_id": user_id}).execute()
        return {"user_id": user_id, "balance": 0}
    return response.data[0]

def update_balance(user_id, amount):
    user = get_user(user_id)
    new_balance = user["balance"] + amount
    supabase.table("users").update({"balance": new_balance}).eq("user_id", user_id).execute()
    return new_balance

# ---------- COMMANDS ----------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_user(user.id)
    await update.message.reply_text(
        f"Welcome {user.first_name}!\n"
        f"💰 Your balance: 0\n\n"
        "Use /deposit to add credits.\n"
        "Use /play to start betting.\n"
        "Use /balance to check your credits."
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    await update.message.reply_text(f"Your balance: {user['balance']} credits.")

async def deposit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "To add credits, send money via Telebirr / bank to [your details].\n"
        "Then send the transaction ID to the admin @your_username."
    )

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🎲 Dice (2x payout)", callback_data="game_dice")],
        [InlineKeyboardButton("🪙 Coin Flip (1.9x payout)", callback_data="game_coin")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose a game:", reply_markup=reply_markup)

async def game_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user = get_user(user_id)
    context.user_data["game"] = query.data
    await query.edit_message_text("Enter your bet amount (credits):")

async def handle_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)

    try:
        bet = int(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a number.")
        return

    if bet <= 0:
        await update.message.reply_text("Bet must be positive.")
        return
    if bet > user["balance"]:
        await update.message.reply_text("Insufficient balance.")
        return

    game = context.user_data.get("game")
    if not game:
        await update.message.reply_text("Please choose a game first via /play.")
        return

    if game == "game_dice":
        roll = random.randint(1, 6)
        win = roll in [5, 6]
        payout = bet * 2 if win else 0
    elif game == "game_coin":
        flip = random.choice(["heads", "tails"])
        # For simplicity, we'll simulate user choosing heads
        win = (flip == "heads")
        payout = int(bet * 1.9) if win else 0
    else:
        await update.message.reply_text("Invalid game.")
        return

    new_balance = update_balance(user_id, payout - bet)
    result_msg = f"🎲 You {'won' if win else 'lost'}!\nBet: {bet}\nPayout: {payout}\nNew balance: {new_balance}"
    await update.message.reply_text(result_msg)
    context.user_data.pop("game", None)

async def admin_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_USER_ID:
        await update.message.reply_text("Unauthorized.")
        return
    try:
        target_id = int(context.args[0])
        amount = int(context.args[1])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /add <user_id> <amount>")
        return
    new_balance = update_balance(target_id, amount)
    await update.message.reply_text(f"Added {amount} credits. New balance: {new_balance}")

# ---------- MAIN ----------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("deposit", deposit))
    app.add_handler(CommandHandler("play", play))
    app.add_handler(CallbackQueryHandler(game_callback, pattern="^game_"))
    app.add_handler(CommandHandler("add", admin_add))
    app.add_handler(CommandHandler("help", lambda u,c: u.message.reply_text("Commands: /start, /balance, /deposit, /play")))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_bet))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
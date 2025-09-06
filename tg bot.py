import os
from dotenv import load_dotenv
import telebot
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
 raise RuntimeError("error")
bot = telebot.TeleBot(TOKEN)
@bot.message_handler(commands=['start'])
def start(message):
 bot.reply_to(message, "привет я чат бот Вахида, чем могу тебе помочь? /help")
@bot.message_handler(commands=['help'])
def help_cmd(message):
 bot.reply_to(message, "для того чтобы я смог тебе помочь напиши нашему боссу @wahidabdullahi1 /about")
@bot.message_handler(commands=['about'])
def aboutme(message):
 bot.reply_to(message,"меня зовут бот, меня создал Вахид 09.09.2025, я ещё не очень крутой, но Вахид обещал, что сделает меня многофункциональным.")
if __name__ == "__main__":
 bot.infinity_polling(skip_pending=True)
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
 bot.reply_to(message, " @<25F! / F2>= ?5@2O= 1>F!  0?<H< /help")
@bot.message_handler(commands=['help'])
def help_cmd(message):
 bot.reply_to(message, "/start 4 =0G0FP\n/help 4 ?><>IP")
if __name__ == "__main__":
 bot.infinity_polling(skip_pending=True)
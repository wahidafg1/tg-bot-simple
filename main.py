import os
from gc import callbacks
from random import choice
import requests
from typing import List
from telebot import types
from dotenv import load_dotenv
import telebot
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
 raise RuntimeError("error")
bot = telebot.TeleBot(TOKEN)
def make_main_kb() -> types.ReplyKeyboardMarkup:
 kb = types.ReplyKeyboardMarkup(resize_keyboard=True)

 kb.row("О боте", "Сумма")
 kb.row("/help")
 return kb

def parse_ints_from_text(text: str) -> List[int]:
  """Выделяет из текста целые числа: нормализует запятые, игнорирует токены-команды."""
  text = text.replace(",", " ")
  tokens = [tok for tok in text.split() if not tok.startswith("/")]
  return [int(tok) for tok in tokens if is_int_token(tok)]


def is_int_token(t: str) -> bool:
 """Проверка токена на целое число (с поддержкой знака минус)."""
 if not t:
  return False
 t = t.strip()
 if t in {"-", ""}:
  return False
 return t.lstrip("-").isdigit()
@bot.message_handler(func=lambda m: m.text == "Сумма")
def kb_sum(m: types.Message) -> None:
    bot.send_message(m.chat.id, "Введите числа через пробел или запятую:")
    bot.register_next_step_handler(m, on_sum_numbers)

def on_sum_numbers(m: types.Message) -> None:
    numbers = parse_ints_from_text(m.text)
   # logging.info("KB-sum next step from id=%s text=%r -> %r", m.from_user.id if m.from_user else "?", m.text, numbers)
    if not numbers:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10")
    else:
        bot.reply_to(m, f"Сумма: {sum(numbers)}")

@bot.message_handler(func=lambda m: m.text == "Максимум")
def kb_max(m: types.Message) -> None:
    bot.send_message(m.chat.id, "Введите числа через пробел или запятую:")
    bot.register_next_step_handler(m, on_max_numbers)

def on_max_numbers(m: types.Message) -> None:
    numbers = parse_ints_from_text(m.text)
   # logging.info("KB-sum next step from id=%s text=%r -> %r", m.from_user.id if m.from_user else "?", m.text, numbers)
    if not numbers:
        bot.reply_to(m, "Не вижу чисел. Пример: 2 3 10")
    else:
        maximum = max(numbers)
        bot.reply_to(m, f"Максимум: {maximum}")

@bot.message_handler(commands=['hide'])
def hide_kb(m):
 rm = types.ReplyKeyboardRemove()
 bot.send_message(m.chat.id, "спрятал клавиатуру", reply_markup=rm)

@bot.message_handler(commands=['confirm'])
def confirm_cmd(m):
   kb = types.InlineKeyboardMarkup()
   kb.add(
      types.InlineKeyboardButton("yes" ,  callback_data="confirm:yes"),
      types.InlineKeyboardButton("No", callback_data = "confirm:no"),
   )
   bot.send_message(m.chat.id, "подвердить действие?", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm:"))
def on_confirm(c):

 choice = c.data.split(":", 1)[1]

 bot.answer_callback_query(c.id, "принято")

 bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)

 bot.send_message(c.message.chat.id, "готово" if choice == "yes" else "Отменено")


@bot.message_handler(commands=['start'])
def start(message):
 print(f"[PING] Пользователь {message.from_user.username} ({message.chat.id}) вызвал /start")
 bot.reply_to(message, "привет я чат бот Вахида, чем могу тебе помочь? /help")
 bot.send_message(
  message.chat.id,
  "Привет! Доступно: /about, /sum, /help /hide /confirm,\n"
  "Или воспользуйтесь кнопками ниже.",
  reply_markup=make_main_kb()
 )

@bot.message_handler(commands=['help'])
def help_cmd(message):
 bot.reply_to(message, "для того чтобы я смог тебе помочь напиши нашему боссу @wahidabdullahi1 /about")
@bot.message_handler(commands=['about'])
def aboutme(message):
 bot.reply_to(message,"меня зовут бот, меня создал Вахид 09.09.2025, я ещё не очень крутой, но Вахид обещал, что сделает меня многофункциональным.")
@bot.message_handler(commands=['sum'])
def cmd_sum(message):
 parts = message.text.split()
 numbers= []

 for p in parts[1:]:
  if p.isdigit(): #только положительные числа
   numbers.append(int(p))

 if not numbers:
  bot.reply_to(message, "напиши числа: /sum 2 3 10")
 else:
  bot.reply_to(message, f"сумма:{sum(numbers)}")

@bot.message_handler(commands=['weather'])
def weather_cmd(message):
 weather = fetch_weather_moscow_open_meteo()
 bot.reply_to(message, f"{weather}")

def fetch_weather_moscow_open_meteo() -> str:
 url = "https://api.open-meteo.com/v1/forecast"
 params = {
  "latitude": 55.7558,
  "longitude": 37.6173,
  "current": "temperature_2m",
  "timezone": "Europe/Moscow"
 }
 try:
  r = requests.get(url, params=params, timeout=5)
  r.raise_for_status()
  t = r.json()["current"]["temperature_2m"]
  return f"Москва: сейчас {round(t)}°C"
 except Exception:
  return "Не удалось получить погоду."

if __name__ == "__main__":
 bot.infinity_polling(skip_pending=True)
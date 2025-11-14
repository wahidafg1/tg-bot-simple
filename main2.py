import os
from dotenv import load_dotenv
import telebot
import time
import json
import datetime
from collections import defaultdict
from db import *
from telebot import types
import random
from db import (get_character_by_id)
from openrouter_client import chat_once, OpenRouterError

# Загрузка переменных окружения
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise RuntimeError("В .env файле нет TOKEN")

init_db()

bot = telebot.TeleBot(TOKEN)

# Структура для хранения активности пользователей
user_activity = defaultdict(list)
MAX_NOTES_PER_USER = 50  # Лимит заметок на пользователя


# Загрузка заметок из файла
def load_notes():
    global notes, note_counter
    try:
        with open('notes.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            notes = data.get('notes', {})
            # Конвертируем ключи обратно в int (json сохраняет как str)
            notes = {int(k): v for k, v in notes.items()}
            note_counter = data.get('counter', 1)
    except FileNotFoundError:
        notes = {}
        note_counter = 1


# Сохранение заметок в файл
def save_notes():
    with open('notes.json', 'w', encoding='utf-8') as f:
        json.dump({
            'notes': notes,
            'counter': note_counter
        }, f, ensure_ascii=False, indent=2)


# Загрузка активности из файла
def load_activity():
    global user_activity
    try:
        with open('activity.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Конвертируем строковые ключи обратно в int
            user_activity = {int(k): v for k, v in data.items()}
    except FileNotFoundError:
        user_activity = {}


# Сохранение активности в файл
def save_activity():
    with open('activity.json', 'w', encoding='utf-8') as f:
        json.dump(user_activity, f, ensure_ascii=False, indent=2)


# Функция для записи активности пользователя
def log_activity(user_id):
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    if user_id not in user_activity:
        user_activity[user_id] = []

    # Добавляем сегодняшнюю дату, если её ещё нет
    if today not in user_activity[user_id]:
        user_activity[user_id].append(today)
        # Сохраняем только последние 30 дней активности
        user_activity[user_id] = user_activity[user_id][-30:]
        save_activity()


# Функция для подсчета заметок пользователя
def count_user_notes(user_id):
    # В текущей реализации все заметки общие для всех пользователей
    # В реальном приложении нужно хранить user_id для каждой заметки
    return len(notes)  # Упрощенная версия


# Функция для создания ASCII гистограммы
def create_activity_chart(user_id):
    today = datetime.datetime.now()
    week_days = []

    # Получаем последние 7 дней
    for i in range(6, -1, -1):
        day = today - datetime.timedelta(days=i)
        week_days.append(day.strftime("%Y-%m-%d"))

    # Считаем активность по дням
    activity_data = []
    for day in week_days:
        if user_id in user_activity and day in user_activity[user_id]:
            activity_data.append('█')  # Полный блок для дня с активностью
        else:
            activity_data.append('░')  # Пустой блок для дня без активности

    # Создаем красивую гистограмму
    chart = "📊 Ваша активность за неделю:\n\n"

    # Добавляем дни недели
    days_names = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
    chart += "     " + "  ".join(days_names) + "\n"

    # Добавляем график
    chart += "     " + "  ".join(activity_data) + "\n"

    # Добавляем даты
    dates = [(today - datetime.timedelta(days=i)).strftime("%d.%m") for i in range(6, -1, -1)]
    chart += "     " + " ".join(dates) + "\n\n"

    # Статистика
    active_days = sum(1 for day in week_days if user_id in user_activity and day in user_activity[user_id])
    chart += f"📈 Активных дней: {active_days}/7"

    return chart


# Загружаем данные при старте
load_notes()
load_activity()


def cmd_start(message: types.Message) -> None:
    """
    Поприветствовать пользователя и кратко описать команды.
    """
    text = (
        "Привет! Это заметочник на SQLite.\n\n"
        "Команды:\n"
        " /note_add <текст>\n"
        " /note_list [N]\n"
        " /note_find <подстрока>\n"
        " /note_edit <id> <текст>\n"
        " /note_del <id>\n"
        " /note_count\n"
        " /note_export\n"
        " /note_stats [days]\n"
        " /models\n"
        " /model <id>\n"
    )


# Добавляем недостающую функцию
def _build_messages_for_character(character, question):
    """
    Создает список сообщений для общения с персонажем
    """
    character_name = character.get('name', 'Персонаж')
    system_prompt = character.get('system_prompt', f'Ты - {character_name}. Отвечай в соответствии со своей ролью.')

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question}
    ]

    return messages


@bot.message_handler(commands=["characters"])
def cmd_characters(message: types.Message) -> None:
    """
    Показать список персонажей
    """
    user_id = message.from_user.id
    items = list_characters()
    if not items:
        bot.reply_to(message, "Каталог персонажей пуст.")
        return

    # Текущий персонаж пользователя
    try:
        current = get_user_character(user_id)["id"]
    except Exception:
        current = None

    lines = ["Доступные персонажи:"]
    for p in items:
        star = "*" if current is not None and p["id"] == current else ""
        lines.append(f"{star} {p['id']}. {p['name']}")

    lines.append("\nВыбор: /character <ID>")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["character"])
def cmd_character(message: types.Message) -> None:
    user_id = message.from_user.id
    arg = message.text.replace("/character", "", 1).strip()
    if not arg:
        p = get_user_character(user_id)
        bot.reply_to(message, f"Текущий персонаж: {p['name']}\n(Сменить: /characters, затем /character <ID>)")
        return
    if not arg.isdigit():
        bot.reply_to(message, "Использование: /character <ID из /characters>")
        return
    try:
        p = set_user_character(user_id, int(arg))
        bot.reply_to(message, f"Персонаж установлен: {p['name']}")
    except ValueError:
        bot.reply_to(message, "Неизвестный ID персонажа. Сначала /characters.")


@bot.message_handler(commands=["whoami"])
def cmd_whoami(message: types.Message) -> None:
    character = get_user_character(message.from_user.id)
    model = get_active_model()
    bot.reply_to(message, f"Модель: {model['label']} ({model['key']})\nПерсонаж: {character['name']}")


@bot.message_handler(commands=["ask_random"])
def cmd_ask_random(message: types.Message) -> None:
    q = message.text.replace("/ask_random", "", 1).strip()
    if not q:
        bot.reply_to(message, "Использование: /ask_random <вопрос>")
        return
    q = q[:600]

    items = list_characters()
    if not items:
        bot.reply_to(message, "Каталог персонажей пуст.")
        return
    chosen = random.choice(items)
    character = get_character_by_id(chosen["id"])

    msgs = _build_messages_for_character(character, q)
    model_key = get_active_model()["key"]
    try:
        text, ms = chat_once(msgs, model=model_key, temperature=0.2, max_tokens=400)
        out = (text or "").strip()[:4000]
        bot.reply_to(message, f"{out}\n\n({ms} сек; модель: {model_key}; как: {character['name']})")
    except OpenRouterError as e:
        bot.reply_to(message, f"Ошибка: {e}")
    except Exception:
        bot.reply_to(message, "Непредвиденная ошибка.")


@bot.message_handler(commands=["models"])
def cmd_models(message: types.Message) -> None:
    items = list_models()
    if not items:
        bot.reply_to(message, "Список моделей пуст.")
        return
    lines = ["Доступные модели:"]
    for m in items:
        star = "★" if m["active"] else " "
        lines.append(f"{star} {m['id']}. {m['label']}  [{m['key']}]")
    lines.append("\nАктивировать: /model <ID>")
    bot.reply_to(message, "\n".join(lines))


@bot.message_handler(commands=["model"])
def cmd_model(message: types.Message) -> None:
    arg = message.text.replace('/model', '', 1).strip()
    if not arg:
        active = get_active_model()
        bot.reply_to(message,
                     f"Текущая активная модель: {active['label']} {active['key']}\n(список: /model <ID> или /models)")
        return
    if not arg.isdigit():
        bot.reply_to(message, "Использование: /model <ID из /models>")
        return
    try:
        active = set_active_model(int(arg))
        bot.reply_to(message, f"Активная модель переключена: {active['label']} {active['key']}")
    except ValueError:
        bot.reply_to(message, "Неизвестный ID модели. Сначала /models.")


@bot.message_handler(commands=['start'])
def start(message):
    log_activity(message.from_user.id)
    bot.reply_to(message, "Привет! Я бот для заметок. Используй /help для списка команд.")


@bot.message_handler(commands=["start", "help"])
def cmd_start(message: types.Message) -> None:
    text = (
        "Привет! Это заметочник на SQLite.\n\n"
        "Команды:\n"
        " /note_add <текст>\n"
        " /note_list [N]\n"
        " /note_find <подстрока>\n"
        " /note_edit <id> <текст>\n"
        " /note_del <id>\n"
        " /note_count\n"
        " /note_export\n"
        " /note_stats [days]\n"
        " /models\n"
        " /model <id>\n"
        " /ask <вопрос>\n"
        " /ask_random <вопрос>\n"
        " /characters\n"
        " /character <id>\n"
        " /whoami\n"
        " /ask_model <ID> <вопрос>\n"
    )
    bot.reply_to(message, text)


@bot.message_handler(commands=['help'])
def help_cmd(message):
    log_activity(message.from_user.id)
    help_text = """
Доступные команды:
/note_add <текст> - Добавить заметку
/note_list - Показать все заметки
/note_find <запрос> - Найти заметку
/note_edit <id> <новый текст> - Изменить заметку
/note_del <id> - Удалить заметку
/note_count - Показать количество заметок
/note_export - Экспортировать заметки в файл
/note_stats - Статистика активности
"""
    bot.reply_to(message, help_text)


@bot.message_handler(commands=['note_add'])
def note_add(message):
    log_activity(message.from_user.id)

    # Проверяем лимит заметок
    user_notes_count = count_user_notes(message.from_user.id)
    if user_notes_count >= MAX_NOTES_PER_USER:
        bot.reply_to(message, f"❌ Превышен лимит заметок! Максимум {MAX_NOTES_PER_USER} заметок на пользователя.")
        return

    global note_counter
    text = message.text.replace('/note_add', '').strip()
    if not text:
        bot.reply_to(message, "Ошибка: Укажите текст заметки.")
        return

    notes[note_counter] = text
    save_notes()  # Сохраняем после добавления
    bot.reply_to(message, f"✅ Заметка #{note_counter} добавлена: {text}")
    note_counter += 1


@bot.message_handler(commands=['note_count'])
def note_count(message):
    log_activity(message.from_user.id)
    count = len(notes)
    user_notes_count = count_user_notes(message.from_user.id)

    if count == 0:
        bot.reply_to(message, "У вас пока нет заметок.")
    elif count == 1:
        bot.reply_to(message, f"У вас 1 заметка. (Лимит: {MAX_NOTES_PER_USER})")
    elif 2 <= count <= 4:
        bot.reply_to(message, f"У вас {count} заметки. (Лимит: {MAX_NOTES_PER_USER})")
    else:
        bot.reply_to(message, f"У вас {count} заметок. (Лимит: {MAX_NOTES_PER_USER})")


@bot.message_handler(commands=['note_list'])
def note_list(message):
    log_activity(message.from_user.id)
    if not notes:
        bot.reply_to(message, "Заметок пока нет.")
        return
    response = "📝 Список заметок:\n" + "\n".join([f"{id}: {text}" for id, text in notes.items()])
    bot.reply_to(message, response)


@bot.message_handler(commands=['note_find'])
def note_find(message):
    log_activity(message.from_user.id)
    query = message.text.replace('/note_find', '').strip()
    if not query:
        bot.reply_to(message, "Ошибка: Укажите поисковый запрос.")
        return
    found = {id: text for id, text in notes.items() if query in text}
    if not found:
        bot.reply_to(message, "Заметки не найдены.")
        return
    response = "🔍 Найденные заметки:\n" + "\n".join([f"{id}: {text}" for id, text in found.items()])
    bot.reply_to(message, response)


@bot.message_handler(commands=['note_edit'])
def note_edit(message):
    log_activity(message.from_user.id)
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        bot.reply_to(message, "Ошибка: Используйте /note_edit <id> <новый текст>")
        return
    try:
        note_id = int(parts[1])
        new_text = parts[2]
    except ValueError:
        bot.reply_to(message, "Ошибка: ID должен быть числом.")
        return
    if note_id not in notes:
        bot.reply_to(message, f"Ошибка: Заметка #{note_id} не найдена.")
        return
    notes[note_id] = new_text
    save_notes()  # Сохраняем после изменения
    bot.reply_to(message, f"✏️ Заметка #{note_id} изменена на: {new_text}")


@bot.message_handler(commands=['note_del'])
def note_del(message):
    log_activity(message.from_user.id)
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Ошибка: Укажите ID заметки для удаления.")
        return
    try:
        note_id = int(parts[1])
    except ValueError:
        bot.reply_to(message, "Ошибка: ID должен быть числом.")
        return
    if note_id not in notes:
        bot.reply_to(message, f"Ошибка: Заметка #{note_id} не найдена.")
        return
    del notes[note_id]
    save_notes()  # Сохраняем после удаления
    bot.reply_to(message, f"🗑️ Заметка #{note_id} удалена.")


@bot.message_handler(commands=['note_export'])
def note_export(message):
    log_activity(message.from_user.id)
    if not notes:
        bot.reply_to(message, "Нет заметок для экспорта.")
        return

    # Создаем имя файла с timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"notes_{timestamp}.txt"

    # Записываем заметки в файл
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Экспорт заметок от {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
        f.write("=" * 50 + "\n\n")
        for note_id, text in notes.items():
            f.write(f"Заметка #{note_id}:\n")
            f.write(f"{text}\n")
            f.write("-" * 30 + "\n")

    # Отправляем файл пользователю
    with open(filename, 'rb') as f:
        bot.send_document(message.chat.id, f, caption="📁 Ваши заметки экспортированы!")

    # Удаляем временный файл
    os.remove(filename)


@bot.message_handler(commands=["ask_model"])
def cmd_ask_model(message: types.Message) -> None:
    """
    Выполнить запрос к конкретной модели по ID без смены активной модели
    Использование: /ask_model <ID модели> <вопрос>
    """
    user_id = message.from_user.id
    args = message.text.replace("/ask_model", "", 1).strip().split(maxsplit=1)

    if len(args) < 2 or not args[0].isdigit():
        bot.reply_to(message, "Использование: /ask_model <ID модели> <вопрос>\n\nСписок моделей: /models")
        return

    model_id = int(args[0])
    question = args[1].strip()[:600]

    if not question:
        bot.reply_to(message, "Ошибка: Укажите текст вопроса.")
        return

    # Получаем информацию о запрашиваемой модели
    try:
        models = list_models()
        target_model = None
        for model in models:
            if model["id"] == model_id:
                target_model = model
                break

        if not target_model:
            bot.reply_to(message, f"Ошибка: Модель с ID {model_id} не найдена.\nСписок моделей: /models")
            return

    except Exception as e:
        bot.reply_to(message, f"Ошибка при получении списка моделей: {e}")
        return

    # Получаем текущего персонажа пользователя
    try:
        character = get_user_character(user_id)
    except Exception as e:
        bot.reply_to(message, f"Ошибка при получении персонажа: {e}")
        return

    # Формируем сообщения для персонажа
    msgs = _build_messages_for_character(character, question)

    # Выполняем запрос к указанной модели
    try:
        text, ms = chat_once(msgs, model=target_model["key"], temperature=0.2, max_tokens=400)
        out = (text or "").strip()[:4000]

        # Формируем ответ с информацией о модели
        active_model = get_active_model()
        model_info = f"🎯 Запрос к модели: {target_model['label']}\n"
        if target_model["id"] == active_model["id"]:
            model_info += f"📋 (текущая активная модель)\n"

        bot.reply_to(message,
                     f"{model_info}\n{out}\n\n({ms} мс; модель: {target_model['key']}; персонаж: {character['name']})")

    except OpenRouterError as e:
        bot.reply_to(message, f"❌ Ошибка API: {e}")
    except Exception as e:
        bot.reply_to(message, f"❌ Непредвиденная ошибка: {e}")

@bot.message_handler(commands=['note_stats'])
def note_stats(message):
    log_activity(message.from_user.id)
    user_id = message.from_user.id

    # Создаем ASCII график активности
    chart = create_activity_chart(user_id)

    # Добавляем общую статистику
    total_notes = len(notes)
    user_notes_count = count_user_notes(user_id)

    stats_text = f"\n📊 Общая статистика:\n"
    stats_text += f"• Всего заметок: {total_notes}\n"
    stats_text += f"• Ваших заметок: {user_notes_count}\n"
    stats_text += f"• Лимит: {MAX_NOTES_PER_USER} заметок\n"

    if user_id in user_activity:
        total_active_days = len(user_activity[user_id])
        stats_text += f"• Всего активных дней: {total_active_days}"

    bot.reply_to(message, chart + stats_text)


if __name__ == "__main__":
    print("Бот запускается...")
    bot.infinity_polling(skip_pending=True)
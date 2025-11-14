import time
import random

class OpenRouterError(Exception):
    pass

def chat_once(messages, model, temperature=0.7, max_tokens=400):
    """
    Простая имитация общения с ИИ (заглушка).
    """
    start = time.time()
    question = messages[-1]["content"]
    fake_answers = [
        "Интересный вопрос! 🤔 Я думаю, что...",
        "Хороший выбор темы! Вот что я думаю:",
        "Позволь объяснить коротко:",
    ]
    response = random.choice(fake_answers) + f" {question}"
    ms = int((time.time() - start) * 1000)
    return response, ms
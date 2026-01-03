"""
config.py - Конфигурация бота для работы на PythonAnywhere и локально
"""

import os
from dotenv import load_dotenv

# Определяем, находимся ли мы на PythonAnywhere
PYTHONANYWHERE = 'pythonanywhere.com' in os.environ.get('PYTHONANYWHERE_DOMAIN', '') or \
                 'PYTHONANYWHERE' in os.environ

# Загружаем переменные из файла .env
load_dotenv()

# Получаем токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что токен был загружен
if not BOT_TOKEN:
    if PYTHONANYWHERE:
        error_msg = (
            "❌ ОШИБКА: BOT_TOKEN не найден на PythonAnywhere!\n\n"
            "Чтобы исправить:\n"
            "1. Зайдите в панель PythonAnywhere → вкладка 'Web'\n"
            "2. Прокрутите вниз до 'Environment variables'\n"
            "3. Добавьте переменную: BOT_TOKEN=ваш_токен\n"
            "4. Перезапустите веб-приложение (кнопка 'Reload')\n\n"
            "Или в консоли выполните:\n"
            "echo 'export BOT_TOKEN=\"ваш_токен\"' >> ~/.virtualenvs/venv/bin/postactivate"
        )
    else:
        error_msg = (
            "❌ ОШИБКА: BOT_TOKEN не найден!\n"
            "Проверьте, что:\n"
            "1. Файл .env существует в папке с ботом\n"
            "2. В файле .env есть строка: BOT_TOKEN=ваш_токен\n"
            "3. Токен скопирован правильно (без лишних пробелов)\n"
            "Пример содержимого .env:\n"
            "BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456"
        )
    raise ValueError(error_msg)

# Настройки базы данных
if PYTHONANYWHERE:
    # На PythonAnywhere используем абсолютный путь
    DATABASE_URL = "sqlite:////home/ваш_логин/папка_с_ботом/deadlines.db"  # ЗАМЕНИТЕ!
else:
    DATABASE_URL = "sqlite:///deadlines.db"  # Локально

# Часовой пояс
TIMEZONE = "Europe/Moscow"

# Режим запуска
USE_WEBHOOKS = PYTHONANYWHERE or os.environ.get('USE_WEBHOOKS', 'false').lower() == 'true'

print(f"✅ Конфигурация загружена: {'PythonAnywhere' if PYTHONANYWHERE else 'Локальный'} режим")
print(f"   Webhooks: {'Включены' if USE_WEBHOOKS else 'Отключены'}")
print(f"   База данных: {DATABASE_URL}")
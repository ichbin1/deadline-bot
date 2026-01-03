"""
pythonanywhere_config.py - Конфигурация для PythonAnywhere
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем токен
if not BOT_TOKEN:
    raise ValueError(
        "❌ ОШИБКА: BOT_TOKEN не найден!\n"
        "На PythonAnywhere нужно:\n"
        "1. Зайти в вкладку 'Consoles'\n"
        "2. Создать новую консоль (Bash)\n"
        "3. Выполнить команду:\n"
        "   echo 'BOT_TOKEN=ваш_токен' > .env\n"
        "4. Или добавить переменную в разделе 'Web' → 'Environment variables'"
    )

# Настройки базы данных (используем SQLite)
DATABASE_URL = "sqlite:////home/ваш_логин/папка_с_ботом/deadlines.db"  # ЗАМЕНИТЕ ПУТЬ!

# Часовой пояс
TIMEZONE = "Europe/Moscow"

# Настройки Flask
FLASK_ENV = "production"
FLASK_DEBUG = False

# Настройки PythonAnywhere
PYTHONANYWHERE_DOMAIN = os.getenv("PYTHONANYWHERE_DOMAIN", "")
USE_WEBHOOKS = True

print(f"✅ Конфигурация загружена: PythonAnywhere домен = {PYTHONANYWHERE_DOMAIN}")
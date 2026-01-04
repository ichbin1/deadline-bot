"""
pythonanywhere_wsgi.py - WSGI файл для PythonAnywhere
"""

import sys
import os

# Добавляем путь к проекту
path = '/home/Semenmind/deadline-bot'  # ЗАМЕНИТЕ НА СВОЙ ПУТЬ!
if path not in sys.path:
    sys.path.append(path)

# Устанавливаем переменные окружения
os.environ['PYTHONANYWHERE'] = 'true'
os.environ['USE_WEBHOOKS'] = 'true'

# Импортируем Flask приложение
from pythonanywhere_app import app as application

# Инициализируем бота
from pythonanywhere_app import init_app
init_app()

print("✅ Бот инициализирован для PythonAnywhere")
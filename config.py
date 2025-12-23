
import os
from dotenv import load_dotenv

# Загружаем переменные из файла .env
# load_dotenv() ищет файл .env в текущей папке и загружает из него переменные
load_dotenv()

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Проверяем, что токен был загружен
if not BOT_TOKEN:
    raise ValueError(
        "❌ ОШИБКА: BOT_TOKEN не найден!\n"
        "Проверьте, что:\n"
        "1. Файл .env существует в папке с ботом\n"
        "2. В файле .env есть строка: BOT_TOKEN=ваш_токен\n"
        "3. Токен скопирован правильно (без лишних пробелов)\n"
        "Пример содержимого .env:\n"
        "BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz-123456"
    )

# Другие настройки (можно добавить позже)
DATABASE_URL = "sqlite:///deadlines.db"  # Путь к базе данных
TIMEZONE = "Europe/Moscow"  # Часовой пояс
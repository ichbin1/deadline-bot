"""
main.py - Основной файл бота для отслеживания дедлайнов
Поддерживает личные и групповые дедлайны для учебных групп
"""

import logging
from datetime import datetime, timedelta

# Исправленные импорты для python-telegram-bot версии 20.x
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes
)
from telegram.constants import ParseMode

# Импортируем наши модули
import config
import database as db
import keyboards as kb
import reminders
import asyncio

# ========== НАСТРОЙКА ЛОГИРОВАНИЯ ==========

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== КОНСТАНТЫ СОСТОЯНИЙ ==========

# Состояния для добавления личного дедлайна
PERSONAL_SUBJECT, PERSONAL_TASK, PERSONAL_DATE, PERSONAL_PRIORITY = range(4)

# Состояния для добавления группового дедлайна
GROUP_SUBJECT, GROUP_TASK, GROUP_DATE, GROUP_CATEGORY, GROUP_IMPORTANCE = range(4, 9)

# Состояния для настройки группы
SET_GROUP = 9

# Состояния для редактирования дедлайна
EDIT_CHOICE, EDIT_VALUE = 10, 11

# ========== СПРАВОЧНЫЕ ФУНКЦИИ ==========

def format_deadline_message(deadline, deadline_type="personal"):
    """Форматирует сообщение о дедлайне для красивого отображения"""
    from utils.time_utils import TimeManager
    
    # Конвертируем время из БД в московское
    deadline_moscow = TimeManager.from_db_to_moscow(deadline.deadline)
    deadline_str = TimeManager.format_for_display(deadline_moscow)
    
    # Рассчитываем сколько времени осталось
    time_left = deadline_moscow - TimeManager.now()
    time_left_str = TimeManager.format_time_left(time_left)
    
    # Определяем статус
    if time_left.total_seconds() < 0:
        status = "🔴 ПРОСРОЧЕНО"
    elif time_left.total_seconds() < 3600:  # меньше часа
        status = "🔴 МЕНЕЕ ЧАСА"
    elif time_left.days == 0:
        hours = time_left.seconds // 3600
        status = f"🟠 СЕГОДНЯ ({hours} ч.)"
    elif time_left.days <= 3:
        status = f"🟡 {time_left.days} д."
    else:
        status = f"🟢 {time_left.days} д."
    
    # Формируем сообщение
    message = ""
    
    if deadline_type == "personal":
        message += f"📝 **Личный дедлайн**\n"
        message += f"🏷️ Приоритет: {deadline.priority}\n"
    else:
        message += f"👥 **Групповой дедлайн**\n"
        message += f"📚 Категория: {deadline.category}\n"
        if deadline.is_important:
            message += f"⚠️ Важный для всех\n"
    
    message += f"\n📚 **Предмет:** {deadline.subject}\n"
    message += f"📋 **Задание:** {deadline.task}\n"
    message += f"⏰ **Дедлайн:** {deadline_str}\n"
    message += f"📊 **Статус:** {status} ({time_left_str})\n"
    
    if deadline_type == "personal" and deadline.is_completed:
        message += f"\n✅ **ВЫПОЛНЕНО**\n"
    
    return message

def calculate_time_left(deadline_date):
    """
    Рассчитывает оставшееся время до дедлайна
    Возвращает строку вида "3 дня 5 часов"
    """
    now = datetime.now()
    if deadline_date < now:
        return "ПРОСРОЧЕНО"
    
    delta = deadline_date - now
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    
    if days > 0:
        return f"{days} дней {hours} часов"
    elif hours > 0:
        return f"{hours} часов {minutes} минут"
    else:
        return f"{minutes} минут"

# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /start
    Регистрирует пользователя и показывает главное меню
    """
    user = update.effective_user
    
    logger.info(f"Пользователь {user.id} ({user.username}) запускает бота")
    
    try:
        # Регистрируем пользователя в базе данных
        db_user = db.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        if db_user:
            logger.info(f"Пользователь {user.id} успешно зарегистрирован, группа: {db_user.group_name}")
            
            welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот для отслеживания учебных дедлайнов. Помогаю не пропустить важные задания!

📌 **Что я умею:**
• Добавлять личные и групповые дедлайны
• Показывать все твои дедлайны
• Отправлять напоминания
• Работать с учебной группой

{"🎓 Твоя группа: " + db_user.group_name if db_user.group_name else "❓ Ты еще не в группе. Используй /setgroup чтобы присоединиться"}

👇 Используй кнопки ниже или команды:
"""
            await update.message.reply_text(
                welcome_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.get_main_keyboard()
            )
        else:
            logger.error(f"Не удалось зарегистрировать пользователя {user.id}")
            await update.message.reply_text(
                "❌ Ошибка при регистрации. Попробуйте еще раз.",
                reply_markup=kb.get_main_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка в start_command для пользователя {user.id}: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при запуске. Попробуйте снова или обратитесь к разработчику.",
            reply_markup=kb.get_main_keyboard()
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команда /help
    Показывает справку по использованию бота
    """
    help_text = """
📚 **Справка по использованию бота:**

**Основные команды:**
/start - Начать работу с ботом
/help - Показать эту справку
/setgroup - Установить/сменить группу
/cancel - Отменить текущее действие

**📝 Работа с дедлайнами:**
• Нажми "Добавить дедлайн" и выбери тип
• Для личных дедлайнов выбери приоритет
• Для групповых - категорию (ДЗ, зачеты, проекты, документы)

**👥 Групповые дедлайны:**
• Видны всем участникам группы
• Можно отмечать как "важные для всех"
• Получаешь уведомления о дедлайнах твоей группы

**⏰ Напоминания:**
Я буду присылать напоминания:
• За неделю до дедлайна
• За день до дедлайна

**📅 Формат даты:**
При добавлении дедлайна указывай дату в формате:
`ГГГГ-ММ-ДД ЧЧ:ММ`
Например: `2024-12-31 23:59`
"""
    await update.message.reply_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_main_keyboard()
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /cancel
    Отменяет текущее действие и возвращает в главное меню
    """
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=kb.get_main_keyboard()
    )
    
    # Очищаем данные пользователя
    if context.user_data:
        context.user_data.clear()
    
    return ConversationHandler.END

async def setgroup_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик команды /setgroup
    Начинает процесс установки группы
    """
    await update.message.reply_text(
        "Введи название твоей учебной группы:\n"
        "Например: 424, 524, АНГ-32\n\n"
        "Или нажми /cancel чтобы отменить.",
        reply_markup=kb.get_cancel_keyboard()
    )
    
    return SET_GROUP

async def debug_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для отладки - показывает текущее время
    """
    # Получаем текущее время в разных часовых поясах
    moscow_tz = pytz.timezone('Europe/Moscow')
    utc_now = datetime.now(pytz.UTC)
    moscow_now = utc_now.astimezone(moscow_tz)
    
    # Также получаем данные о пользователе и его дедлайнах
    user_id = update.effective_user.id
    user = db.get_user_by_telegram_id(user_id)
    
    # Получаем дедлайны для отладки
    personal_deadlines = db.get_personal_deadlines(user_id)
    group_deadlines = db.get_user_group_deadlines(user_id)
    
    # Формируем сообщение
    message = (
        f"🔧 **Информация для отладки**\n\n"
        f"⏰ **Время:**\n"
        f"• UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"• Москва: {moscow_now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"👤 **Пользователь:**\n"
        f"• ID: {user_id}\n"
        f"• Имя: {user.first_name if user else 'не найден'}\n"
        f"• Группа: {user.group_name if user and user.group_name else 'не установлена'}\n\n"
        f"📋 **Статистика дедлайнов:**\n"
        f"• Личные: {len(personal_deadlines)}\n"
        f"• Групповые: {len(group_deadlines)}\n\n"
        f"⚙️ **Рекомендации:**\n"
        f"• Убедитесь, что время в базе данных указано в UTC\n"
        f"• Формат даты для добавления: ГГГГ-ММ-ДД ЧЧ:ММ\n"
        f"• Пример: 2024-12-31 23:59\n\n"
        f"📊 **Ближайший дедлайн:**\n"
    )
    
    # Добавляем информацию о ближайшем дедлайне
    all_deadlines = []
    if personal_deadlines:
        all_deadlines.extend(personal_deadlines)
    if group_deadlines:
        all_deadlines.extend(group_deadlines)
    
    if all_deadlines:
        # Сортируем по дате
        all_deadlines.sort(key=lambda x: x.deadline)
        nearest = all_deadlines[0]
        time_left = calculate_time_left(nearest.deadline)
        message += f"• {nearest.subject}: {time_left} ({nearest.deadline.strftime('%Y-%m-%d %H:%M')})"
    else:
        message += "• Нет активных дедлайнов"
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_main_keyboard()
    )

async def debug_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для отладки напоминаний
    """
    from datetime import datetime
    import pytz
    
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)
    
    # Получаем дедлайны пользователя
    user_id = update.effective_user.id
    personal_deadlines = db.get_personal_deadlines(user_id)
    group_deadlines = db.get_user_group_deadlines(user_id)
    
    message = f"🕰️ **Отладка напоминаний**\n\n"
    message += f"Текущее время (Москва): {now.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    message += f"📝 **Личные дедлайны:** {len(personal_deadlines)}\n"
    for i, dl in enumerate(personal_deadlines[:3], 1):
        dl_dt = pytz.UTC.localize(dl.deadline).astimezone(moscow_tz)
        time_left = dl_dt - now
        message += f"{i}. {dl.subject}: {dl_dt.strftime('%d.%m.%Y %H:%M')} (через {int(time_left.total_seconds()/3600)}ч.)\n"
    
    message += f"\n👥 **Групповые дедлайны:** {len(group_deadlines)}\n"
    for i, dl in enumerate(group_deadlines[:3], 1):
        dl_dt = pytz.UTC.localize(dl.deadline).astimezone(moscow_tz)
        time_left = dl_dt - now
        message += f"{i}. {dl.subject}: {dl_dt.strftime('%d.%m.%Y %H:%M')} (через {int(time_left.total_seconds()/3600)}ч.)\n"
    
    message += "\n⚠️ Проверьте, что время дедлайнов указано правильно!"
    
    await update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

async def test_notification_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Тестовая команда для проверки уведомлений
    """
    user_id = update.effective_user.id
    
    try:
        # Проверяем, что бот может отправить сообщение
        await update.message.reply_text(
            "🔧 **Тестирование системы уведомлений**\n\n"
            "1. Проверяем соединение... ✅\n"
            "2. Отправляем тестовое сообщение..."
        )
        
        # Отправляем тестовое уведомление
        from datetime import datetime, timedelta
        from reminders import DeadlineReminder
        
        # Создаем тестовый дедлайн (в памяти)
        class TestDeadline:
            def __init__(self):
                self.id = 999
                self.subject = "Тестовый предмет"
                self.task = "Тестовое задание для проверки уведомлений"
                self.priority = "Высокий"
                self.deadline = datetime.now() + timedelta(hours=1)
        
        # Создаем менеджер напоминаний
        reminder = DeadlineReminder(context.bot)
        
        # Отправляем тестовое уведомление
        test_deadline = TestDeadline()
        await reminder.send_personal_reminder(
            user_id, test_deadline, "час", timedelta(hours=1)
        )
        
        await update.message.reply_text(
            "✅ Тестовое уведомление отправлено!\n\n"
            "Если вы его получили - система работает.\n"
            "Если нет, проверьте:\n"
            "1. Бот не заблокирован\n"
            "2. У вас включены уведомления от бота\n"
            "3. В логах нет ошибок при отправке"
        )
        
    except Exception as e:
        logger.error(f"Ошибка в тестовой команде: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при тестировании:\n{e}"
        )

async def create_test_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Создает тестовый дедлайн для проверки напоминаний
    """
    user_id = update.effective_user.id
    
    # Создаем дедлайн на 16 минут вперед (для теста за час)
    test_time = datetime.now() + timedelta(minutes=16)
    
    deadline_id = db.add_personal_deadline(
        user_id,
        "ТЕСТОВЫЙ ДЕДЛАЙН",
        "Проверка системы напоминаний",
        test_time,
        "Высокий"
    )
    
    if deadline_id:
        await update.message.reply_text(
            f"✅ Тестовый дедлайн создан!\n\n"
            f"📚 Предмет: ТЕСТОВЫЙ ДЕДЛАЙН\n"
            f"📋 Задание: Проверка системы напоминаний\n"
            f"⏰ Время: {test_time.strftime('%d.%m.%Y %H:%M')}\n\n"
            f"Напоминание должно прийти через 1 минуту (за 15 минут до дедлайна).\n"
            f"Используйте /debug_reminders для отладки.",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Ошибка создания тестового дедлайна")

async def setgroup_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик ввода названия группы
    """
    group_name = update.message.text.strip()
    
    # Проверяем длину названия группы
    if len(group_name) < 2 or len(group_name) > 50:
        await update.message.reply_text(
            "Название группы должно быть от 2 до 50 символов.\n"
            "Попробуй еще раз или нажми /cancel чтобы отменить."
        )
        return SET_GROUP
    
    # Устанавливаем группу пользователя
    user_id = update.effective_user.id
    if db.set_user_group(user_id, group_name):
        await update.message.reply_text(
            f"✅ Отлично! Теперь ты в группе *{group_name}*\n"
            f"Теперь ты будешь видеть все дедлайны этой группы.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при установке группы. Попробуй еще раз.",
            reply_markup=kb.get_main_keyboard()
        )
    
    return ConversationHandler.END

# ========== ОБРАБОТЧИКИ ГЛАВНОГО МЕНЮ ==========

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик нажатий кнопок главного меню
    """
    text = update.message.text
    
    if text == "📝 Добавить дедлайн":
        await update.message.reply_text(
            "Выбери тип дедлайна:",
            reply_markup=kb.get_deadline_type_keyboard()
        )
    
    elif text == "👤 Личный дедлайн":
        # Начинаем процесс добавления личного дедлайна
        await start_add_personal_deadline(update, context)
    
    elif text == "👥 Групповой дедлайн":
        # Начинаем процесс добавления группового дедлайна
        await start_add_group_deadline(update, context)
    
    elif text == "📋 Мои дедлайны":
        await show_personal_deadlines_menu(update, context)
    
    elif text == "👥 Групповые дедлайны":
        await show_group_deadlines_menu(update, context)
    
    elif text == "🔔 Напоминания":
        await show_reminders_menu(update, context)
    
    elif text == "📅 Ближайшие дедлайны":
        await show_upcoming_deadlines(update, context)
    
    elif text == "🔕 Отключить напоминания":
        await disable_reminders(update, context)
    
    elif text == "⚙️ Настройки":
        await update.message.reply_text(
            "Настройки бота:",
            reply_markup=kb.get_settings_keyboard()
        )
    
    elif text == "🔔 Настройки уведомлений":
        await show_notification_settings(update, context)
    
    elif text == "ℹ️ Помощь":
        await help_command(update, context)
    
    elif text == "✏️ Изменить группу":
        await setgroup_command(update, context)
    
    elif text == "⬅️ Назад":
        await update.message.reply_text(
            "Возвращаюсь в главное меню:",
            reply_markup=kb.get_main_keyboard()
        )
    
    elif text == "❌ Отмена":
        await cancel_command(update, context)
        return

# ========== ПОКАЗ ДЕДЛАЙНОВ ==========

async def show_personal_deadlines_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню личных дедлайнов
    """
    user_id = update.effective_user.id
    deadlines = db.get_personal_deadlines(user_id)
    
    if deadlines:
        # Группируем дедлайны по статусу
        active = [d for d in deadlines if not d.is_completed]
        completed = [d for d in deadlines if d.is_completed]
        
        message = f"📋 **Твои личные дедлайны:**\n\n"
        message += f"📊 Статистика:\n"
        message += f"• Активных: {len(active)}\n"
        message += f"• Выполненных: {len(completed)}\n\n"
        
        if active:
            message += "⏳ **Ближайшие дедлайны:**\n"
            for i, deadline in enumerate(active[:3], 1):
                time_left = calculate_time_left(deadline.deadline)
                message += f"{i}. {deadline.subject} - {time_left}\n"
        
        # Создаем инлайн-клавиатуру для просмотра
        keyboard = kb.get_deadlines_list_keyboard(active, "personal")
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            "📭 У тебя пока нет личных дедлайнов.\n"
            "Нажми 'Добавить дедлайн' чтобы создать первый!",
            reply_markup=kb.get_main_keyboard()
        )

async def show_group_deadlines_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает меню групповых дедлайнов
    """
    user_id = update.effective_user.id
    deadlines = db.get_user_group_deadlines(user_id)
    
    if deadlines:
        # Группируем по категориям
        categories = {}
        for deadline in deadlines:
            if deadline.category not in categories:
                categories[deadline.category] = []
            categories[deadline.category].append(deadline)
        
        message = "👥 **Дедлайны твоей группы:**\n\n"
        
        for category, cat_deadlines in categories.items():
            message += f"📚 **{category}:** {len(cat_deadlines)}\n"
        
        message += "\n👇 Выбери дедлайн для просмотра:"
        
        # Создаем инлайн-клавиатуру для просмотра
        keyboard = kb.get_deadlines_list_keyboard(deadlines, "group")
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
    else:
        user = db.get_user_by_telegram_id(user_id)
        if user and user.group_name:
            await update.message.reply_text(
                f"📭 В группе *{user.group_name}* пока нет дедлайнов.\n"
                "Будь первым, кто добавит дедлайн!",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Ты еще не в группе.\n"
                "Используй /setgroup чтобы присоединиться к группе.",
                reply_markup=kb.get_main_keyboard()
            )

# ========== ДОБАВЛЕНИЕ ЛИЧНОГО ДЕДЛАЙНА ==========

async def start_add_personal_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс добавления личного дедлайна
    """
    await update.message.reply_text(
        "📝 **Добавление личного дедлайна**\n\n"
        "Введи название предмета:\n"
        "Например: 'Математический анализ', 'Программирование'",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_cancel_keyboard()
    )
    
    return PERSONAL_SUBJECT

async def get_personal_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает название предмета для личного дедлайна
    """
    subject = update.message.text.strip()
    
    if len(subject) < 2 or len(subject) > 100:
        await update.message.reply_text(
            "Название предмета должно быть от 2 до 100 символов.\n"
            "Попробуй еще раз:"
        )
        return PERSONAL_SUBJECT
    
    context.user_data['personal_subject'] = subject
    
    await update.message.reply_text(
        "📋 Теперь опиши задание:\n"
        "Например: 'Решить задачи 1-5', 'Написать реферат'",
        reply_markup=kb.get_back_keyboard()
    )
    
    return PERSONAL_TASK

async def get_personal_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает описание задания для личного дедлайна
    """
    task = update.message.text.strip()
    
    if len(task) < 2 or len(task) > 500:
        await update.message.reply_text(
            "Описание задания должно быть от 2 до 500 символов.\n"
            "Попробуй еще раз:"
        )
        return PERSONAL_TASK
    
    context.user_data['personal_task'] = task
    
    await update.message.reply_text(
        "📅 Теперь введи дату и время дедлайна:\n"
        "Формат: *ГГГГ-ММ-ДД ЧЧ:ММ*\n"
        "Например: *2024-12-31 23:59*\n\n"
        "⚠️ Дата должна быть в будущем!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_back_keyboard()
    )
    
    return PERSONAL_DATE

async def get_personal_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает дату дедлайна для личного дедлайна
    """
    from utils.time_utils import TimeManager
    
    try:
        # Разделяем дату и время
        input_text = update.message.text.strip()
        if ' ' in input_text:
            date_str, time_str = input_text.split(' ', 1)
        else:
            date_str = input_text
            time_str = "23:59"
        
        # Парсим с помощью TimeManager
        deadline_moscow = TimeManager.parse_user_input(date_str, time_str)
        
        # Проверяем, что дата в будущем
        if deadline_moscow <= TimeManager.now():
            await update.message.reply_text(
                "❌ Дата должна быть в будущем!\n"
                "Введи дату еще раз:"
            )
            return PERSONAL_DATE
        
        context.user_data['personal_date'] = deadline_moscow
        
        await update.message.reply_text(
            "🏷️ Выбери приоритет дедлайна:",
            reply_markup=kb.get_priority_keyboard()
        )
        
        return PERSONAL_PRIORITY
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Используй формат: *ГГГГ-ММ-ДД ЧЧ:ММ*\n"
            "Например: *2024-12-31 23:59*\n"
            "Или просто *2024-12-31* (будет установлено 23:59)\n"
            "Попробуй еще раз:",
            parse_mode=ParseMode.MARKDOWN
        )
        return PERSONAL_DATE

async def get_personal_priority(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает приоритет и сохраняет личный дедлайн
    """
    priority_text = update.message.text
    priority_map = {
        "🔴 Высокий": "Высокий",
        "🟡 Средний": "Средний",
        "🟢 Низкий": "Низкий"
    }
    
    if priority_text not in priority_map:
        await update.message.reply_text(
            "Пожалуйста, выбери приоритет из предложенных кнопок:",
            reply_markup=kb.get_priority_keyboard()
        )
        return PERSONAL_PRIORITY
    
    priority = priority_map[priority_text]
    
    # Получаем данные из контекста
    subject = context.user_data.get('personal_subject')
    task = context.user_data.get('personal_task')
    deadline_date = context.user_data.get('personal_date')
    
    # Сохраняем дедлайн в базу данных
    user_id = update.effective_user.id
    deadline_id = db.add_personal_deadline(user_id, subject, task, deadline_date, priority)
    
    if deadline_id:
        formatted_date = deadline_date.strftime("%d.%m.%Y в %H:%M")
        
        await update.message.reply_text(
            f"✅ **Личный дедлайн добавлен!**\n\n"
            f"📚 Предмет: {subject}\n"
            f"📋 Задание: {task}\n"
            f"🏷️ Приоритет: {priority}\n"
            f"⏰ Дедлайн: {formatted_date}\n\n"
            f"Я напомню тебе о нем заранее!",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при сохранении дедлайна. Попробуй еще раз.",
            reply_markup=kb.get_main_keyboard()
        )
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

# ========== ДОБАВЛЕНИЕ ГРУППОВОГО ДЕДЛАЙНА ==========

async def start_add_group_deadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Начинает процесс добавления группового дедлайна
    """
    user_id = update.effective_user.id
    user = db.get_user_by_telegram_id(user_id)
    
    if not user or not user.group_name:
        await update.message.reply_text(
            "❌ Ты еще не в группе.\n"
            "Сначала присоединись к группе через /setgroup",
            reply_markup=kb.get_main_keyboard()
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        f"👥 **Добавление группового дедлайна**\n"
        f"Группа: *{user.group_name}*\n\n"
        "Введи название предмета:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_cancel_keyboard()
    )
    
    return GROUP_SUBJECT

async def get_group_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает название предмета для группового дедлайна
    """
    subject = update.message.text.strip()
    
    if len(subject) < 2 or len(subject) > 100:
        await update.message.reply_text(
            "Название предмета должно быть от 2 до 100 символов.\n"
            "Попробуй еще раз:"
        )
        return GROUP_SUBJECT
    
    context.user_data['group_subject'] = subject
    
    await update.message.reply_text(
        "📋 Теперь опиши задание для группы:\n"
        "Например: 'Сделать презентацию', 'Подготовиться к экзамену'",
        reply_markup=kb.get_back_keyboard()
    )
    
    return GROUP_TASK

async def get_group_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает описание задания для группового дедлайна
    """
    task = update.message.text.strip()
    
    if len(task) < 2 or len(task) > 500:
        await update.message.reply_text(
            "Описание задания должно быть от 2 до 500 символов.\n"
            "Попробуй еще раз:"
        )
        return GROUP_TASK
    
    context.user_data['group_task'] = task
    
    await update.message.reply_text(
        "📅 Теперь введи дату и время дедлайна:\n"
        "Формат: *ГГГГ-ММ-ДД ЧЧ:ММ*\n"
        "Например: *2024-12-31 23:59*\n\n"
        "⚠️ Дата должна быть в будущем!",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_back_keyboard()
    )
    
    return GROUP_DATE

async def get_group_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Получает дату дедлайна для группового дедлайна"""
    from utils.time_utils import TimeManager
    
    try:
        input_text = update.message.text.strip()
        if ' ' in input_text:
            date_str, time_str = input_text.split(' ', 1)
        else:
            date_str = input_text
            time_str = "23:59"
        
        deadline_moscow = TimeManager.parse_user_input(date_str, time_str)
        
        if deadline_moscow <= TimeManager.now():
            await update.message.reply_text(
                "❌ Дата должна быть в будущем!\n"
                "Введи дату еще раз:"
            )
            return GROUP_DATE
        
        context.user_data['group_date'] = deadline_moscow
        
        await update.message.reply_text(
            "📚 Выбери категорию дедлайна:",
            reply_markup=kb.get_category_keyboard()
        )
        
        return GROUP_CATEGORY
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {str(e)}\n\n"
            "Используй формат: *ГГГГ-ММ-ДД ЧЧ:ММ*\n"
            "Например: *2024-12-31 23:59*\n"
            "Или просто *2024-12-31*\n"
            "Попробуй еще раз:",
            parse_mode=ParseMode.MARKDOWN
        )
        return GROUP_DATE

async def get_group_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает категорию для группового дедлайна
    """
    category_text = update.message.text
    
    # Проверяем, что выбранная категория есть в нашем списке
    valid_categories = list(kb.CATEGORIES.values())
    if category_text not in valid_categories:
        await update.message.reply_text(
            "Пожалуйста, выбери категорию из предложенных кнопок:",
            reply_markup=kb.get_category_keyboard()
        )
        return GROUP_CATEGORY
    
    # Преобразуем отображаемое имя в ключ для базы
    category_key = kb.get_category_key_from_display(category_text)
    context.user_data['group_category'] = category_key
    
    await update.message.reply_text(
        "⚠️ Это важный дедлайн для всей группы?\n"
        "Если да - все участники группы получат уведомление.",
        reply_markup=kb.get_importance_keyboard()
    )
    
    return GROUP_IMPORTANCE

async def get_group_importance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Получает важность дедлайна и сохраняет групповой дедлайн
    """
    importance_text = update.message.text
    
    if importance_text == "✅ Да, для всех":
        is_important = True
    elif importance_text == "➡️ Нет, просто добавить":
        is_important = False
    else:
        await update.message.reply_text(
            "Пожалуйста, выбери вариант из предложенных кнопок:",
            reply_markup=kb.get_importance_keyboard()
        )
        return GROUP_IMPORTANCE
    
    # Получаем данные из контекста
    subject = context.user_data.get('group_subject')
    task = context.user_data.get('group_task')
    deadline_date = context.user_data.get('group_date')
    category_key = context.user_data.get('group_category')
    
    # Получаем информацию о пользователе и группе
    user_id = update.effective_user.id
    user = db.get_user_by_telegram_id(user_id)
    
    if not user or not user.group_name:
        await update.message.reply_text(
            "❌ Ошибка: не удалось определить твою группу.",
            reply_markup=kb.get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Сохраняем дедлайн в базу данных
    deadline_id = db.add_group_deadline(
        user_id, subject, task, deadline_date, 
        user.group_name, category_key, is_important
    )
    
    if deadline_id:
        formatted_date = deadline_date.strftime("%d.%m.%Y в %H:%M")
        category_display = kb.get_category_display_name(category_key)
        
        message = f"✅ **Групповой дедлайн добавлен!**\n\n"
        message += f"👥 Группа: {user.group_name}\n"
        message += f"📚 Предмет: {subject}\n"
        message += f"📋 Задание: {task}\n"
        message += f"📚 Категория: {category_display}\n"
        message += f"⏰ Дедлайн: {formatted_date}\n"
        
        if is_important:
            message += f"⚠️ Важный для всех участников\n\n"
        else:
            message += f"\n"
            
        message += f"Все участники группы увидят этот дедлайн!"
        
        await update.message.reply_text(
            message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb.get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Ошибка при сохранении дедлайна. Попробуй еще раз.",
            reply_markup=kb.get_main_keyboard()
        )
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    return ConversationHandler.END

# ========== НАСТРОЙКА УВЕДОМЛЕНИЙ ==============

async def show_notification_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает настройки уведомлений
    """
    user_id = update.effective_user.id
    user = db.get_user_by_telegram_id(user_id)
    
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return

    # Получаем текущие настройки пользователя
    settings = {
        "notify_week": user.notify_week,
        "notify_day": user.notify_day,
    }
    
    await update.message.reply_text(
        "🔔 **Настройки уведомлений:**\n\n"
        "Выбери, за сколько времени присылать напоминания:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_notification_settings_keyboard(settings)
    )

async def handle_notification_settings(query, data, user_id):
    """
    Обработчик настроек уведомлений
    """
    session = db.Session()
    try:
        user = session.query(db.User).filter(db.User.telegram_id == user_id).first()
        
        if not user:
            await query.answer("Пользователь не найден", show_alert=True)
            return
        
        if data == "toggle_week":
            user.notify_week = not user.notify_week
            session.commit()
            await query.answer(f"Напоминания за неделю: {'включены' if user.notify_week else 'выключены'}", show_alert=False)
        
        elif data == "toggle_day":
            user.notify_day = not user.notify_day
            session.commit()
            await query.answer(f"Напоминания за день: {'включены' if user.notify_day else 'выключены'}", show_alert=False)
        
        elif data == "enable_all":
            user.notify_week = True
            user.notify_day = True
            session.commit()
            await query.answer("Все напоминания включены!", show_alert=True)
        
        elif data == "disable_all":
            user.notify_week = False
            user.notify_day = False
            session.commit()
            await query.answer("Все напоминания выключены!", show_alert=True)
        
        elif data == "save_notifications":
            await query.answer("✅ Настройки сохранены!", show_alert=True)
            await query.delete_message()
            return
        
        elif data == "back_to_settings":
            await query.edit_message_text(
                "Возвращаюсь в настройки:",
                reply_markup=kb.get_settings_keyboard()
            )
            return
        
        # Обновляем клавиатуру с новыми состояниями
        settings = {
            "notify_week": user.notify_week,
            "notify_day": user.notify_day
        }
        keyboard = kb.get_notification_settings_keyboard(settings)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке настроек уведомлений: {e}")
        await query.answer("❌ Ошибка при сохранении настроек", show_alert=True)
    
    finally:
        session.close()

async def show_reminders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает главное меню напоминаний
    """
    user = update.effective_user
    menu_text = f"""
🔔 **Управление напоминаниями**

Привет, {user.first_name}! Здесь ты можешь управлять своими напоминаниями.

📋 **Доступные функции:**

• 📅 **Ближайшие дедлайны** - покажет дедлайны, о которых я буду напоминать
• 🔕 **Отключить напоминания** - временно отключить все уведомления

💡 **Совет:** Я автоматически напоминаю за неделю, день и час до каждого дедлайна.
    """
    
    await update.message.reply_text(
        menu_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_reminders_menu_keyboard()
    )

async def show_upcoming_deadlines(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показывает ближайшие дедлайны (на этой неделе и сегодня)
    """
    user_id = update.effective_user.id
    
    # Получаем все дедлайны пользователя
    personal_deadlines = db.get_personal_deadlines(user_id)
    group_deadlines = db.get_user_group_deadlines(user_id)
    
    now = datetime.now()
    week_later = now + timedelta(days=7)
    
    # Фильтруем дедлайны на этой неделе
    personal_week = [d for d in personal_deadlines if d.deadline <= week_later]
    group_week = [d for d in group_deadlines if d.deadline <= week_later]
    
    # Формируем сообщение
    message = "📅 **Ближайшие дедлайны:**\n\n"
    
    if personal_week or group_week:
        # Личные дедлайны
        if personal_week:
            message += "👤 **Твои личные дедлайны:**\n"
            for deadline in personal_week[:3]:  # Показываем первые 3
                days_left = (deadline.deadline - now).days
                hours_left = (deadline.deadline - now).seconds // 3600
                
                if days_left > 0:
                    time_left = f"{days_left} дней"
                else:
                    time_left = f"{hours_left} часов"
                
                message += f"• {deadline.subject} - через {time_left}\n"
        
        # Групповые дедлайны
        if group_week:
            message += "\n👥 **Групповые дедлайны:**\n"
            for deadline in group_week[:3]:  # Показываем первые 3
                days_left = (deadline.deadline - now).days
                hours_left = (deadline.deadline - now).seconds // 3600
                
                if days_left > 0:
                    time_left = f"{days_left} дней"
                else:
                    time_left = f"{hours_left} часов"
                
                message += f"• {deadline.subject} - через {time_left}\n"
        
        if len(personal_week) > 3 or len(group_week) > 3:
            message += f"\n📊 И еще {(len(personal_week)-3 if len(personal_week)>3 else 0) + (len(group_week)-3 if len(group_week)>3 else 0)} дедлайнов..."
    else:
        message += "🎉 Ура! На этой неделе у тебя нет дедлайнов!\n\nОтличное время, чтобы отдохнуть или заняться чем-то интересным! 😊"
    
    message += "\n\n👇 Ты можешь установить дополнительные напоминания для любого дедлайна."
    
    await update.message.reply_text(
        message,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb.get_main_keyboard()
    )

async def disable_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Отключает все напоминания пользователя
    """
    user_id = update.effective_user.id
    
    session = db.Session()
    try:
        user = session.query(db.User).filter(db.User.telegram_id == user_id).first()
        if user:
            user.notify_week = False
            user.notify_day = False
            user.notify_hour = False
            session.commit()
            
            await update.message.reply_text(
                "🔕 **Напоминания отключены**\n\n"
                "Все автоматические напоминания временно отключены.\n"
                "Ты не будешь получать уведомления о дедлайнах.\n\n"
                "Чтобы включить обратно, зайди в 'Настройки' → 'Настройки уведомлений'.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb.get_main_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Пользователь не найден.",
                reply_markup=kb.get_main_keyboard()
            )
    
    except Exception as e:
        logger.error(f"Ошибка при отключении напоминаний: {e}")
        await update.message.reply_text(
            "❌ Ошибка при отключении напоминаний.",
            reply_markup=kb.get_main_keyboard()
        )
    
    finally:
        session.close()

# ========== ОБРАБОТЧИКИ ИНЛАЙН-КНОПОК ==========

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Основной обработчик callback-запросов от инлайн-кнопок
    """
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    logger.info(f"Callback от пользователя {user_id}: {data}")
    
    # Закрытие клавиатуры
    if data == "close" or data == "close_list":
        await query.delete_message()
        return
    
    # Отмена действий
    if data in ["cancel_delete", "cancel_complete", "cancel_category", "cancel_priority"]:
        await query.edit_message_text(
            "Действие отменено.",
            reply_markup=None
        )
        return
    
    # Настройки уведомлений
    elif data in ["toggle_week", "toggle_day", "toggle_hour", "enable_all", "disable_all", "save_notifications", "back_to_settings"]:
        await handle_notification_settings(query, data, user_id)
        return
    
    # Просмотр дедлайна
    elif data.startswith("view_"):
        parts = data.split("_")
        if len(parts) >= 3:
            deadline_type = parts[1]
            deadline_id = int(parts[2])
            await show_deadline_details(query, deadline_id, deadline_type)
        return
    
    # Удаление дедлайна
    elif data.startswith("delete_"):
        parts = data.split("_")
        if len(parts) >= 3:
            deadline_type = parts[1]
            deadline_id = int(parts[2])
            
            await query.edit_message_text(
                "❓ Ты уверен, что хочешь удалить этот дедлайн?",
                reply_markup=kb.get_confirm_delete_keyboard(deadline_id, deadline_type)
            )
        return
    
    # Подтверждение удаления
    elif data.startswith("confirm_delete_"):
        parts = data.split("_")
        if len(parts) >= 4:
            deadline_type = parts[2]
            deadline_id = int(parts[3])
            
            if deadline_type == "personal":
                success = db.delete_personal_deadline(deadline_id, user_id)
            else:
                success = db.delete_group_deadline(deadline_id, user_id)
            
            if success:
                await query.edit_message_text(
                    "✅ Дедлайн успешно удален!",
                    reply_markup=None
                )
            else:
                await query.edit_message_text(
                    "❌ Не удалось удалить дедлайн.\n"
                    "Возможно, он уже был удален или у тебя нет прав.",
                    reply_markup=None
                )
        return
    
    # Отметка как выполненного
    elif data.startswith("complete_personal_"):
        deadline_id = int(data.split("_")[2])
        
        await query.edit_message_text(
            "❓ Ты выполнил это задание?",
            reply_markup=kb.get_confirm_complete_keyboard(deadline_id)
        )
        return
    
    # Подтверждение выполнения
    elif data.startswith("confirm_complete_"):
        deadline_id = int(data.split("_")[2])
        
        if db.mark_personal_deadline_completed(deadline_id, user_id):
            await query.edit_message_text(
                "✅ Задание отмечено как выполненное!",
                reply_markup=None
            )
        else:
            await query.edit_message_text(
                "❌ Не удалось отметить задание как выполненное.",
                reply_markup=None
            )
        return
    
    # Подписка на групповой дедлайн
    elif data.startswith("subscribe_"):
        deadline_id = int(data.split("_")[1])
        
        if db.subscribe_to_group_deadline(user_id, deadline_id):
            await query.answer("✅ Ты подписан на уведомления об этом дедлайне!", show_alert=True)
        else:
            await query.answer("❌ Ты уже подписан на этот дедлайн!", show_alert=True)
        return
    
    # Пагинация
    elif data.startswith("page_"):
        parts = data.split("_")
        if len(parts) >= 3:
            deadline_type = parts[1]
            page = int(parts[2])
            
            if deadline_type == "personal":
                deadlines = db.get_personal_deadlines(user_id)
            else:
                deadlines = db.get_user_group_deadlines(user_id)
            
            keyboard = kb.get_deadlines_list_keyboard(deadlines, deadline_type, page)
            await query.edit_message_reply_markup(reply_markup=keyboard)
        return
    
    # Если не обработано ни одно условие
    logger.warning(f"Неизвестный callback: {data}")
    await query.answer("❌ Неизвестная команда", show_alert=True)

async def show_deadline_details(query, deadline_id, deadline_type):
    """
    Показывает подробную информацию о дедлайне
    """
    if deadline_type == "personal":
        # Получаем личный дедлайн
        session = db.Session()
        try:
            deadline = session.query(db.Deadline).filter(db.Deadline.id == deadline_id).first()
            if deadline:
                message = format_deadline_message(deadline, "personal")
                keyboard = kb.get_deadline_actions_keyboard(deadline_id, "personal")
                
                await query.edit_message_text(
                    message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text(
                    "❌ Дедлайн не найден.",
                    reply_markup=None
                )
        finally:
            session.close()
    
    elif deadline_type == "group":
        # Получаем групповой дедлайн
        session = db.Session()
        try:
            deadline = session.query(db.GroupDeadline).filter(db.GroupDeadline.id == deadline_id).first()
            if deadline:
                message = format_deadline_message(deadline, "group")
                keyboard = kb.get_deadline_actions_keyboard(deadline_id, "group")
                
                await query.edit_message_text(
                    message,
                    parse_mode=ParseMode.MARKDOWN,
                    reply_markup=keyboard
                )
            else:
                await query.edit_message_text(
                    "❌ Дедлайн не найден.",
                    reply_markup=None
                )
        finally:
            session.close()

# ========== ОБРАБОТЧИК ОШИБОК ==========

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обработчик ошибок бота
    """
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    
    # Отправляем сообщение об ошибке пользователю
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Произошла ошибка. Пожалуйста, попробуйте еще раз или обратитесь к разработчику.",
            reply_markup=kb.get_main_keyboard()
        )

# ========== ОСНОВНАЯ ФУНКЦИЯ ==========

def main():
    """
    Основная функция запуска бота
    """
    # Создаем приложение
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # Настраиваем систему напоминаний
    from reminders import DeadlineReminder
    
    reminder_manager = DeadlineReminder(application.bot)
    
    job_queue = application.job_queue
    
    # ПРОСТОЙ callback без оберток
    async def check_reminders_job(context):
        try:
            logger.info("⏰ Запуск периодической проверки напоминаний...")
            await reminder_manager.check_and_send_reminders()
        except Exception as e:
            logger.error(f"❌ Ошибка в задании проверки напоминаний: {e}")
    
    # Запускаем проверку каждую минуту
    job_queue.run_repeating(
        callback=check_reminders_job,
        interval=21600,  # 60 секунд = 1 минута
        first=10       # Первый запуск через 10 секунд
    )
    
    logger.info("✅ Планировщик напоминаний запущен (интервал: 6 часов)")
    
    
    # ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("debug_reminders", debug_reminders))

    # ConversationHandler для установки группы
    group_conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("setgroup", setgroup_command),
            MessageHandler(filters.Regex('^✏️ Изменить группу$'), setgroup_command)
        ],
        states={
            SET_GROUP: [MessageHandler(filters.TEXT & ~filters.Regex('^❌ Отмена$'), setgroup_input)]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            MessageHandler(filters.Regex('^❌ Отмена$'), cancel_command)
        ]
    )
    application.add_handler(group_conv_handler)
    
    # ConversationHandler для добавления личного дедлайна
    personal_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^👤 Личный дедлайн$'), start_add_personal_deadline)
        ],
        states={
            PERSONAL_SUBJECT: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex('^(❌ Отмена|⬅️ Назад)$') & ~filters.COMMAND, 
                    get_personal_subject
                )
            ],
            PERSONAL_TASK: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex('^(❌ Отмена|⬅️ Назад)$') & ~filters.COMMAND, 
                    get_personal_task
                )
            ],
            PERSONAL_DATE: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex('^(❌ Отмена|⬅️ Назад)$') & ~filters.COMMAND, 
                    get_personal_date
                )
            ],
            PERSONAL_PRIORITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_personal_priority)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            MessageHandler(filters.Regex('^(❌ Отмена|⬅️ Назад)$'), cancel_command)
        ]
    )
    application.add_handler(personal_conv_handler)
    
    # ConversationHandler для добавления группового дедлайна
    group_deadline_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^👥 Групповой дедлайн$'), start_add_group_deadline)
        ],
        states={
            GROUP_SUBJECT: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex('^(❌ Отмена|⬅️ Назад)$') & ~filters.COMMAND, 
                    get_group_subject
                )
            ],
            GROUP_TASK: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex('^(❌ Отмена|⬅️ Назад)$') & ~filters.COMMAND, 
                    get_group_task
                )
            ],
            GROUP_DATE: [
                MessageHandler(
                    filters.TEXT & ~filters.Regex('^(❌ Отмена|⬅️ Назад)$') & ~filters.COMMAND, 
                    get_group_date
                )
            ],
            GROUP_CATEGORY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_category)
            ],
            GROUP_IMPORTANCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_group_importance)
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_command),
            MessageHandler(filters.Regex('^(❌ Отмена|⬅️ Назад)$'), cancel_command)
        ]
    )
    application.add_handler(group_deadline_conv_handler)


    
    # Обработчик кнопок главного меню
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
    )
    
    # Обработчик инлайн-кнопок
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # ========== ЗАПУСК БОТА ==========
    
    logger.info("Бот запускается...")
    
    # Запускаем бота в режиме polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

# ========== ТОЧКА ВХОДА ==========

import os

if __name__ == "__main__":
    # Для локального тестирования
    if os.environ.get('PYTHONANYWHERE'):
        # Для продакшена - просто запускаем
        application.run_polling()
    else:
        # Локально - с логированием
        print("🚀 Бот запускается локально...")
        main()
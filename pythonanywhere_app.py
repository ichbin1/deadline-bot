"""
pythonanywhere_app.py - Версия бота для PythonAnywhere с вебхуками
"""

import logging
import os
import sys
from flask import Flask, request, jsonify
import asyncio
import threading
import time

# Настройка пути для импортов
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Создаем Flask приложение
app = Flask(__name__)

# Переменные для хранения глобальных объектов
bot_application = None
bot_thread = None
reminder_manager = None

def init_bot_application():
    """
    Инициализирует приложение бота
    Возвращает Application объект
    """
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        ConversationHandler,
        filters,
        ContextTypes
    )
    from telegram import Update
    from telegram.constants import ParseMode
    import config
    import database as db
    import keyboards as kb
    import reminders
    
    # Создаем приложение
    application = Application.builder().token(config.BOT_TOKEN).build()
    
    # ========== ИМПОРТ ФУНКЦИЙ ИЗ MAIN.PY ==========
    from main import (
        # Команды
        start_command,
        help_command,
        cancel_command,
        debug_command,
        debug_reminders,
        test_notification_command,
        
        # Обработчики меню
        handle_main_menu,
        
        # Дедлайны
        show_personal_deadlines_menu,
        show_group_deadlines_menu,
        
        # Добавление дедлайнов (личные)
        start_add_personal_deadline,
        get_personal_subject,
        get_personal_task,
        get_personal_date,
        get_personal_priority,
        
        # Добавление дедлайнов (групповые)
        start_add_group_deadline,
        get_group_subject,
        get_group_task,
        get_group_date,
        get_group_category,
        get_group_importance,
        
        # Группа
        setgroup_command,
        setgroup_input,
        
        # Напоминания
        show_reminders_menu,
        show_upcoming_deadlines,
        disable_reminders,
        show_notification_settings,
        
        # Инлайн-кнопки
        handle_callback_query,
        
        # Ошибки
        error_handler,
        
        # Константы состояний
        PERSONAL_SUBJECT, PERSONAL_TASK, PERSONAL_DATE, PERSONAL_PRIORITY,
        GROUP_SUBJECT, GROUP_TASK, GROUP_DATE, GROUP_CATEGORY, GROUP_IMPORTANCE,
        SET_GROUP
    )
    
    # ========== РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ ==========
    
    # Обработчики команд
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("cancel", cancel_command))
    application.add_handler(CommandHandler("debug", debug_command))
    application.add_handler(CommandHandler("debug_reminders", debug_reminders))
    application.add_handler(CommandHandler("test_notification", test_notification_command))
    
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
    
    logger.info("✅ Приложение бота создано и настроено для PythonAnywhere")
    return application

def init_reminders():
    """
    Инициализирует систему напоминаний
    """
    import reminders
    global bot_application
    
    if not bot_application:
        logger.error("❌ Приложение бота не инициализировано")
        return None
    
    reminder = reminders.DeadlineReminder(bot_application.bot)
    logger.info("✅ Менеджер напоминаний инициализирован")
    return reminder

async def run_reminder_check():
    """
    Запускает проверку напоминаний
    """
    global reminder_manager
    
    if not reminder_manager:
        logger.error("❌ Менеджер напоминаний не инициализирован")
        return
    
    while True:
        try:
            await reminder_manager.check_and_send_reminders()
            # Ждем 1 час перед следующей проверкой
            await asyncio.sleep(3600)
        except Exception as e:
            logger.error(f"❌ Ошибка в проверке напоминаний: {e}")
            await asyncio.sleep(300)  # Ждем 5 минут при ошибке

def run_reminders_in_thread():
    """
    Запускает проверку напоминаний в отдельном потоке
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_reminder_check())

# ========== FLASK РОУТЫ ==========

@app.route('/')
def index():
    """Главная страница"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>🤖 Бот дедлайнов</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .status {
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
            }
            .status.good {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .status.warning {
                background: #fff3cd;
                color: #856404;
                border: 1px solid #ffeaa7;
            }
            .button {
                display: inline-block;
                background: #4CAF50;
                color: white;
                padding: 10px 20px;
                text-decoration: none;
                border-radius: 5px;
                margin: 10px 5px;
                transition: background 0.3s;
            }
            .button:hover {
                background: #45a049;
            }
            .stats {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .stat-card {
                background: #f8f9fa;
                padding: 20px;
                border-radius: 5px;
                text-align: center;
                border-left: 4px solid #4CAF50;
            }
            .stat-number {
                font-size: 24px;
                font-weight: bold;
                color: #4CAF50;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Бот для отслеживания дедлайнов</h1>
            
            <div class="status good">
                ✅ Бот успешно запущен и работает на PythonAnywhere!
            </div>
            
            <h2>📊 Статистика системы</h2>
            <div class="stats">
                <div class="stat-card">
                    <div class="stat-number" id="user-count">...</div>
                    <div>Пользователей</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="deadline-count">...</div>
                    <div>Активных дедлайнов</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number" id="group-count">...</div>
                    <div>Групп</div>
                </div>
            </div>
            
            <h2>🔧 Управление ботом</h2>
            <div>
                <a href="/health" class="button">Проверить здоровье</a>
                <a href="/set_webhook" class="button">Установить вебхук</a>
                <a href="/remove_webhook" class="button">Удалить вебхук</a>
                <a href="/webhook_info" class="button">Информация о вебхуке</a>
                <a href="/test" class="button">Тест бота</a>
            </div>
            
            <h2>📚 Документация</h2>
            <div class="status warning">
                💡 Бот работает через вебхуки. Все обновления приходят на этот сервер.
            </div>
            
            <h3>Полезные ссылки:</h3>
            <ul>
                <li><a href="https://t.me/your_bot" target="_blank">💬 Открыть бота в Telegram</a></li>
                <li><a href="/logs" target="_blank">📋 Посмотреть логи</a></li>
                <li><a href="/database" target="_blank">🗄️ Проверить базу данных</a></li>
            </ul>
            
            <footer style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666;">
                <p>Бот запущен на PythonAnywhere. Время: <span id="current-time"></span></p>
            </footer>
        </div>
        
        <script>
            // Обновляем время
            function updateTime() {
                const now = new Date();
                document.getElementById('current-time').textContent = 
                    now.toLocaleString('ru-RU', { 
                        timeZone: 'Europe/Moscow',
                        dateStyle: 'full',
                        timeStyle: 'long'
                    });
            }
            updateTime();
            setInterval(updateTime, 1000);
            
            // Загружаем статистику
            async function loadStats() {
                try {
                    const response = await fetch('/stats');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        document.getElementById('user-count').textContent = data.users;
                        document.getElementById('deadline-count').textContent = data.deadlines;
                        document.getElementById('group-count').textContent = data.groups;
                    }
                } catch (error) {
                    console.error('Ошибка загрузки статистики:', error);
                }
            }
            
            loadStats();
            // Обновляем статистику каждые 30 секунд
            setInterval(loadStats, 30000);
        </script>
    </body>
    </html>
    """

@app.route('/health')
def health_check():
    """Проверка здоровья системы"""
    try:
        import database as db
        import config
        
        # Проверяем базу данных
        session = db.Session()
        session.execute("SELECT 1")
        session.close()
        
        # Проверяем бота
        bot_status = "running" if bot_application else "not_running"
        reminders_status = "running" if reminder_manager else "not_running"
        
        return jsonify({
            'status': 'healthy',
            'bot': bot_status,
            'reminders': reminders_status,
            'database': 'connected',
            'timestamp': time.time(),
            'server_time': time.strftime('%Y-%m-%d %H:%M:%S'),
            'timezone': 'Europe/Moscow'
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }), 500

@app.route('/set_webhook')
def set_webhook():
    """Установка вебхука"""
    try:
        import config
        from telegram import Bot
        
        bot = Bot(token=config.BOT_TOKEN)
        
        # Получаем URL вебхука из параметров или используем текущий
        webhook_url = request.args.get('url', f'https://{request.host}')
        
        # Устанавливаем вебхук
        success = bot.set_webhook(
            url=f"{webhook_url}/{config.BOT_TOKEN}",
            allowed_updates=["message", "callback_query", "chat_member", "my_chat_member"]
        )
        
        if success:
            logger.info(f"✅ Вебхук установлен на {webhook_url}/{config.BOT_TOKEN}")
            return jsonify({
                'status': 'success',
                'message': f'Вебхук установлен на {webhook_url}',
                'webhook_url': f'{webhook_url}/{config.BOT_TOKEN}'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Не удалось установить вебхук'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Ошибка установки вебхука: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/remove_webhook')
def remove_webhook():
    """Удаление вебхука"""
    try:
        import config
        from telegram import Bot
        
        bot = Bot(token=config.BOT_TOKEN)
        success = bot.delete_webhook()
        
        if success:
            logger.info("✅ Вебхук удален")
            return jsonify({
                'status': 'success',
                'message': 'Вебхук удален'
            })
        else:
            return jsonify({
                'status': 'error',
                'message': 'Не удалось удалить вебхук'
            }), 500
            
    except Exception as e:
        logger.error(f"❌ Ошибка удаления вебхука: {e}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/webhook_info')
def webhook_info():
    """Информация о вебхуке"""
    try:
        import config
        from telegram import Bot
        
        bot = Bot(token=config.BOT_TOKEN)
        info = bot.get_webhook_info()
        
        return jsonify({
            'status': 'success',
            'webhook_info': {
                'url': info.url,
                'has_custom_certificate': info.has_custom_certificate,
                'pending_update_count': info.pending_update_count,
                'last_error_date': info.last_error_date,
                'last_error_message': info.last_error_message,
                'max_connections': info.max_connections,
                'allowed_updates': info.allowed_updates
            }
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route(f'/<token>', methods=['POST'])
async def webhook(token):
    """Обработчик вебхуков"""
    try:
        import config
        from telegram import Update
        
        # Проверяем токен
        if token != config.BOT_TOKEN:
            logger.warning(f"❌ Неверный токен вебхука: {token}")
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 403
        
        # Получаем обновление
        update_data = request.get_json()
        logger.debug(f"📥 Получено обновление: {update_data}")
        
        # Создаем объект Update
        update = Update.de_json(update_data, bot_application.bot)
        
        # Обрабатываем обновление
        await bot_application.process_update(update)
        
        return jsonify({'status': 'success'}), 200
        
    except Exception as e:
        logger.error(f"❌ Ошибка обработки вебхука: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/stats')
def get_stats():
    """Получение статистики"""
    try:
        import database as db
        
        session = db.Session()
        
        # Получаем количество пользователей
        user_count = session.query(db.User).count()
        
        # Получаем количество активных дедлайнов
        from datetime import datetime
        deadline_count = session.query(db.Deadline).filter(
            db.Deadline.is_completed == False,
            db.Deadline.deadline >= datetime.now()
        ).count()
        
        # Получаем количество уникальных групп
        groups = session.query(db.User.group_name).distinct().all()
        group_count = len([g for g in groups if g[0]])
        
        session.close()
        
        return jsonify({
            'status': 'success',
            'users': user_count,
            'deadlines': deadline_count,
            'groups': group_count,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/test')
def test_bot():
    """Тестовая страница"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Тест бота</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
            }
            .test-section {
                margin: 20px 0;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 5px;
            }
            button {
                background: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                cursor: pointer;
                margin: 5px;
            }
            button:hover {
                background: #45a049;
            }
            .result {
                margin: 10px 0;
                padding: 10px;
                border-radius: 5px;
            }
            .success {
                background: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .error {
                background: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
        </style>
    </head>
    <body>
        <h1>🧪 Тестирование бота</h1>
        
        <div class="test-section">
            <h3>1. Проверка здоровья</h3>
            <button onclick="testHealth()">Проверить здоровье</button>
            <div id="health-result" class="result"></div>
        </div>
        
        <div class="test-section">
            <h3>2. Проверка вебхука</h3>
            <button onclick="testWebhook()">Проверить вебхук</button>
            <div id="webhook-result" class="result"></div>
        </div>
        
        <div class="test-section">
            <h3>3. Проверка базы данных</h3>
            <button onclick="testDatabase()">Проверить БД</button>
            <div id="database-result" class="result"></div>
        </div>
        
        <div class="test-section">
            <h3>4. Отправить тестовое сообщение</h3>
            <p>Введите ID чата (ваш Telegram ID):</p>
            <input type="text" id="chat-id" placeholder="123456789">
            <button onclick="sendTestMessage()">Отправить тест</button>
            <div id="message-result" class="result"></div>
        </div>
        
        <script>
            async function testHealth() {
                const resultDiv = document.getElementById('health-result');
                resultDiv.textContent = 'Проверяем...';
                
                try {
                    const response = await fetch('/health');
                    const data = await response.json();
                    
                    if (data.status === 'healthy') {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            ✅ Система здорова<br>
                            Бот: ${data.bot}<br>
                            Напоминания: ${data.reminders}<br>
                            База данных: ${data.database}<br>
                            Время: ${new Date(data.timestamp * 1000).toLocaleString()}
                        `;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.textContent = `❌ Ошибка: ${data.error}`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = `❌ Ошибка сети: ${error}`;
                }
            }
            
            async function testWebhook() {
                const resultDiv = document.getElementById('webhook-result');
                resultDiv.textContent = 'Проверяем...';
                
                try {
                    const response = await fetch('/webhook_info');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            ✅ Вебхук настроен<br>
                            URL: ${data.webhook_info.url || 'Не установлен'}<br>
                            Ожидающих обновлений: ${data.webhook_info.pending_update_count}<br>
                            Последняя ошибка: ${data.webhook_info.last_error_message || 'Нет'}
                        `;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.textContent = `❌ Ошибка: ${data.message}`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = `❌ Ошибка сети: ${error}`;
                }
            }
            
            async function testDatabase() {
                const resultDiv = document.getElementById('database-result');
                resultDiv.textContent = 'Проверяем...';
                
                try {
                    const response = await fetch('/stats');
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        resultDiv.className = 'result success';
                        resultDiv.innerHTML = `
                            ✅ База данных работает<br>
                            Пользователей: ${data.users}<br>
                            Активных дедлайнов: ${data.deadlines}<br>
                            Групп: ${data.groups}
                        `;
                    } else {
                        resultDiv.className = 'result error';
                        resultDiv.textContent = `❌ Ошибка: ${data.message}`;
                    }
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = `❌ Ошибка сети: ${error}`;
                }
            }
            
            async function sendTestMessage() {
                const chatId = document.getElementById('chat-id').value;
                const resultDiv = document.getElementById('message-result');
                
                if (!chatId) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = '❌ Введите ID чата';
                    return;
                }
                
                resultDiv.textContent = 'Отправляем...';
                
                try {
                    // Здесь можно добавить отправку тестового сообщения
                    // через API бота
                    resultDiv.className = 'result success';
                    resultDiv.textContent = '✅ Функция в разработке. Используйте команду /test в боте.';
                } catch (error) {
                    resultDiv.className = 'result error';
                    resultDiv.textContent = `❌ Ошибка: ${error}`;
                }
            }
        </script>
    </body>
    </html>
    """

@app.route('/logs')
def show_logs():
    """Показ логов"""
    try:
        import io
        import datetime
        
        # Читаем логи из файла или буфера
        log_content = []
        
        # Пытаемся прочитать файл логов
        log_file = 'bot.log'
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                log_content = f.readlines()[-100:]  # Последние 100 строк
        else:
            # Или используем буфер логов
            import logging
            buffer = io.StringIO()
            for handler in logging.getLogger().handlers:
                if hasattr(handler, 'stream'):
                    # Копируем логи из буфера
                    pass
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Логи бота</title>
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                .log {{ background: #f5f5f5; padding: 10px; border-radius: 5px; }}
                .timestamp {{ color: #666; }}
                .info {{ color: #007bff; }}
                .error {{ color: #dc3545; }}
                .warning {{ color: #ffc107; }}
            </style>
        </head>
        <body>
            <h2>📋 Логи бота (последние 100 строк)</h2>
            <div class="log">
                <pre>{''.join(log_content[-100:]) if log_content else 'Логи не найдены'}</pre>
            </div>
            <p><a href="/">← Назад</a></p>
        </body>
        </html>
        """
    except Exception as e:
        return f"Ошибка при чтении логов: {e}"

@app.route('/database')
def database_info():
    """Информация о базе данных"""
    try:
        import database as db
        import sqlite3
        
        db_path = 'deadlines.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Получаем информацию о таблицах
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        table_info = []
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            table_info.append((table_name, count))
        
        conn.close()
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>База данных</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #4CAF50; color: white; }}
                tr:nth-child(even) {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h2>🗄️ База данных бота</h2>
            <p>Файл: {db_path}</p>
            
            <h3>Таблицы:</h3>
            <table>
                <tr>
                    <th>Таблица</th>
                    <th>Записей</th>
                    <th>Размер</th>
                </tr>
                {"".join([f'<tr><td>{name}</td><td>{count}</td><td>-</td></tr>' for name, count in table_info])}
            </table>
            
            <p><a href="/">← Назад</a></p>
        </body>
        </html>
        """
    except Exception as e:
        return f"Ошибка при доступе к базе данных: {e}"

# ========== ИНИЦИАЛИЗАЦИЯ ПРИ ЗАПУСКЕ ==========

def init_app():
    """Инициализация приложения при запуске"""
    global bot_application, reminder_manager, bot_thread
    
    try:
        logger.info("🚀 Инициализация бота для PythonAnywhere...")
        
        # Инициализируем приложение бота
        bot_application = init_bot_application()
        
        # Инициализируем менеджер напоминаний
        reminder_manager = init_reminders()
        
        # Запускаем напоминания в отдельном потоке
        if reminder_manager:
            bot_thread = threading.Thread(target=run_reminders_in_thread, daemon=True)
            bot_thread.start()
            logger.info("✅ Поток напоминаний запущен")
        
        # Инициализируем планировщик задач в самом приложении бота
        if bot_application and bot_application.job_queue:
            # Создаем задачу для проверки напоминаний каждые 6 часов
            from reminders import DeadlineReminder
            
            async def check_reminders(context):
                if reminder_manager:
                    await reminder_manager.check_and_send_reminders()
            
            bot_application.job_queue.run_repeating(
                check_reminders,
                interval=21600,  # 6 часов
                first=30         # Первый запуск через 30 секунд
            )
            logger.info("✅ Планировщик задач инициализирован")
        
        logger.info("✅ Бот успешно инициализирован для PythonAnywhere")
        
        # Автоматически устанавливаем вебхук
        try:
            import config
            from telegram import Bot
            
            bot = Bot(token=config.BOT_TOKEN)
            
            # Получаем текущий хост
            current_host = f"https://{os.environ.get('PYTHONANYWHERE_SITE', '')}"
            if not current_host or current_host == "https://":
                # Если не на PythonAnywhere, используем localhost для тестов
                current_host = "http://localhost:5000"
            
            webhook_url = f"{current_host}/{config.BOT_TOKEN}"
            bot.set_webhook(webhook_url)
            logger.info(f"✅ Вебхук автоматически установлен на {webhook_url}")
            
        except Exception as e:
            logger.warning(f"⚠️ Не удалось автоматически установить вебхук: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка инициализации бота: {e}", exc_info=True)
        return False

# Инициализируем приложение при импорте
if not bot_application:
    init_app()

# WSGI совместимость
application = app

if __name__ == '__main__':
    # Локальный запуск для тестирования
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
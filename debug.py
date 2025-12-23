"""
debug.py - Утилиты для отладки бота
"""

from utils.time_utils import TimeManager

logger = logging.getLogger(__name__)

def check_all_deadlines():
    """
    Проверяет все дедлайны в базе и выводит информацию
    """
    session = db.Session()
    
    print("=" * 80)
    print("ПРОВЕРКА ВСЕХ ДЕДЛАЙНОВ В БАЗЕ ДАННЫХ")
    print("=" * 80)
    
    now = TimeManager.now()
    
    # Личные дедлайны
    personal_deadlines = session.query(db.Deadline).all()
    print(f"\n📝 ЛИЧНЫЕ ДЕДЛАЙНЫ: {len(personal_deadlines)}")
    print("-" * 40)
    
    for dl in personal_deadlines:
        dl_dt = pytz.UTC.localize(dl.deadline).astimezone(moscow_tz)
        time_left = dl_dt - now
        hours_left = time_left.total_seconds() / 3600
        
        user = session.query(db.User).filter(db.User.id == dl.user_id).first()
        username = user.username if user else "Unknown"
        
        print(f"ID: {dl.id}")
        print(f"  Пользователь: {username} (ID: {user.telegram_id if user else 'N/A'})")
        print(f"  Предмет: {dl.subject}")
        print(f"  Задание: {dl.task}")
        print(f"  Время дедлайна: {dl_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Осталось часов: {hours_left:.1f}")
        print(f"  Выполнен: {'✅' if dl.is_completed else '❌'}")
        print(f"  Напоминания: неделя={dl.reminded_week}, день={dl.reminded_day}, час={dl.reminded_hour}")
        print()
    
    # Групповые дедлайны
    group_deadlines = session.query(db.GroupDeadline).all()
    print(f"\n👥 ГРУППОВЫЕ ДЕДЛАЙНЫ: {len(group_deadlines)}")
    print("-" * 40)
    
    for dl in group_deadlines:
        dl_dt = pytz.UTC.localize(dl.deadline).astimezone(moscow_tz)
        time_left = dl_dt - now
        hours_left = time_left.total_seconds() / 3600
        
        user = session.query(db.User).filter(db.User.id == dl.creator_id).first()
        username = user.username if user else "Unknown"
        
        print(f"ID: {dl.id}")
        print(f"  Создатель: {username} (ID: {user.telegram_id if user else 'N/A'})")
        print(f"  Группа: {dl.group_name}")
        print(f"  Предмет: {dl.subject}")
        print(f"  Задание: {dl.task}")
        print(f"  Категория: {dl.category}")
        print(f"  Время дедлайна: {dl_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Осталось часов: {hours_left:.1f}")
        print(f"  Важный: {'✅' if dl.is_important else '❌'}")
        print(f"  Напоминания: неделя={dl.reminded_week}, день={dl.reminded_day}, час={dl.reminded_hour}")
        print()
    
    # Пользователи
    users = session.query(db.User).all()
    print(f"\n👤 ПОЛЬЗОВАТЕЛИ: {len(users)}")
    print("-" * 40)
    
    for user in users:
        print(f"ID: {user.id}")
        print(f"  Telegram ID: {user.telegram_id}")
        print(f"  Имя: {user.first_name} {user.last_name or ''}")
        print(f"  Username: @{user.username or 'N/A'}")
        print(f"  Группа: {user.group_name or 'N/A'}")
        print(f"  Админ: {'✅' if user.is_admin else '❌'}")
        print()
    
    session.close()
    
    print("=" * 80)
    print(f"Текущее время (Москва): {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

def add_test_deadline(telegram_id=111111, hours_from_now=1):
    """
    Добавляет тестовый дедлайн для проверки
    """
    from datetime import datetime
    import pytz
    
    moscow_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_tz)
    deadline_time = now + timedelta(hours=hours_from_now)
    
    # Убираем часовой пояс для сохранения в базу
    deadline_naive = deadline_time.replace(tzinfo=None)
    
    deadline_id = db.add_personal_deadline(
        telegram_id=telegram_id,
        subject="ТЕСТОВЫЙ ДЕДЛАЙН",
        task="Это тестовый дедлайн для проверки уведомлений",
        deadline=deadline_naive,
        priority="Высокий"
    )
    
    print(f"✅ Добавлен тестовый дедлайн:")
    print(f"   ID: {deadline_id}")
    print(f"   Время: {deadline_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Через часов: {hours_from_now}")
    print(f"   Напоминание должно прийти через: {hours_from_now-1} часов (за час)")
    
    return deadline_id

if __name__ == "__main__":
    # Настройка логирования
    logging.basicConfig(level=logging.INFO)
    
    print("🔧 ЗАПУСК УТИЛИТЫ ОТЛАДКИ")
    print()
    
    # Проверяем все дедлайны
    check_all_deadlines()
    
    # Добавляем тестовый дедлайн (раскомментируйте при необходимости)
    # add_test_deadline(telegram_id=111111, hours_from_now=1.1)  # 1 час 6 минут
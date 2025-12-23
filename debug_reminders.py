"""
debug_reminders.py - Отладка системы напоминаний
"""

from utils.time_utils import TimeManager

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

now = TimeManager.now()

def test_time_calculation():
    """Тест вычисления времени"""
    print("=" * 80)
    print("ТЕСТ ВЫЧИСЛЕНИЯ ВРЕМЕНИ")
    print("=" * 80)
    
    session = db.Session()
    
    # Получаем первый личный дедлайн
    deadline = session.query(db.Deadline).first()
    if deadline:
        print(f"Дедлайн ID: {deadline.id}")
        print(f"Предмет: {deadline.subject}")
        print(f"Время дедлайна: {deadline.deadline}")
        print(f"Тип времени: {type(deadline.deadline)}")
        print(f"tzinfo: {deadline.deadline.tzinfo}")
        
        # Текущее время
        now_moscow = datetime.now(MOSCOW_TZ)
        print(f"\nТекущее время (Москва): {now_moscow}")
        print(f"Тип: {type(now_moscow)}")
        print(f"tzinfo: {now_moscow.tzinfo}")
        
        # Пытаемся преобразовать время дедлайна
        try:
            if deadline.deadline.tzinfo is None:
                print("\nВремя дедлайна НАИВНОЕ (без часового пояса)")
                # Вариант 1: Предполагаем, что в UTC
                deadline_utc = pytz.UTC.localize(deadline.deadline)
                deadline_moscow = deadline_utc.astimezone(MOSCOW_TZ)
                print(f"Преобразовано в UTC: {deadline_utc}")
                print(f"Преобразовано в Москву: {deadline_moscow}")
                
                # Вычисляем разницу
                time_left = deadline_moscow - now_moscow
                print(f"\nРазница: {time_left}")
                print(f"Часов осталось: {time_left.total_seconds() / 3600:.1f}")
            else:
                print("\nВремя дедлайна УЖЕ С ЧАСОВЫМ ПОЯСОМ")
                deadline_moscow = deadline.deadline.astimezone(MOSCOW_TZ)
                time_left = deadline_moscow - now_moscow
                print(f"Разница: {time_left}")
                
        except Exception as e:
            print(f"\n❌ Ошибка: {e}")
    
    session.close()

def check_all_deadline_times():
    """Проверяем время всех дедлайнов"""
    print("\n" + "=" * 80)
    print("ПРОВЕРКА ВСЕХ ДЕДЛАЙНОВ")
    print("=" * 80)
    
    session = db.Session()
    
    now_moscow = datetime.now(MOSCOW_TZ)
    print(f"Текущее время (Москва): {now_moscow.strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Личные дедлайны
    personal_deadlines = session.query(db.Deadline).all()
    print(f"Личные дедлайны ({len(personal_deadlines)}):")
    for dl in personal_deadlines:
        try:
            if dl.deadline.tzinfo is None:
                dl_moscow = pytz.UTC.localize(dl.deadline).astimezone(MOSCOW_TZ)
            else:
                dl_moscow = dl.deadline.astimezone(MOSCOW_TZ)
            
            time_left = dl_moscow - now_moscow
            hours_left = time_left.total_seconds() / 3600
            
            print(f"  ID {dl.id}: {dl.subject}")
            print(f"    Время дедлайна: {dl.deadline}")
            print(f"    Москва: {dl_moscow.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Осталось часов: {hours_left:.1f}")
            print(f"    Напоминания: W={dl.reminded_week}, D={dl.reminded_day}, H={dl.reminded_hour}")
            print()
            
        except Exception as e:
            print(f"  ❌ Ошибка с дедлайном {dl.id}: {e}")
    
    session.close()

def simulate_reminder_check():
    """Имитирует проверку напоминаний"""
    print("\n" + "=" * 80)
    print("СИМУЛЯЦИЯ ПРОВЕРКИ НАПОМИНАНИЙ")
    print("=" * 80)
    
    session = db.Session()
    now_moscow = datetime.now(MOSCOW_TZ)
    
    # Проверяем личные дедлайны
    deadlines = session.query(db.Deadline).filter(
        db.Deadline.is_completed == False
    ).all()
    
    print(f"Найдено {len(deadlines)} активных дедлайнов")
    print("-" * 40)
    
    for dl in deadlines:
        try:
            # Преобразуем время дедлайна
            if dl.deadline.tzinfo is None:
                dl_moscow = pytz.UTC.localize(dl.deadline).astimezone(MOSCOW_TZ)
            else:
                dl_moscow = dl.deadline.astimezone(MOSCOW_TZ)
            
            time_left = dl_moscow - now_moscow
            
            print(f"Дедлайн {dl.id}: {dl.subject}")
            print(f"  Время: {dl_moscow.strftime('%Y-%m-%d %H:%M')}")
            print(f"  Осталось: {time_left}")
            
            # Проверяем условия напоминаний
            reminders = []
            
            if timedelta(days=6, hours=23) < time_left <= timedelta(days=7):
                reminders.append("За неделю ✅")
            else:
                reminders.append("За неделю ❌")
                
            if timedelta(hours=23) < time_left <= timedelta(days=1):
                reminders.append("За день ✅")
            else:
                reminders.append("За день ❌")
                
            if timedelta(minutes=59) < time_left <= timedelta(hours=1):
                reminders.append("За час ✅")
            else:
                reminders.append("За час ❌")
            
            print(f"  Проверка: {', '.join(reminders)}")
            
            # Выводим конкретные диапазоны
            print(f"  Детально:")
            print(f"    Для 'за неделю': нужно от {timedelta(days=6, hours=23)} до {timedelta(days=7)}")
            print(f"    Для 'за день': нужно от {timedelta(hours=23)} до {timedelta(days=1)}")
            print(f"    Для 'за час': нужно от {timedelta(minutes=59)} до {timedelta(hours=1)}")
            print(f"    Текущая разница: {time_left}")
            print()
            
        except Exception as e:
            print(f"❌ Ошибка с дедлайном {dl.id}: {e}")
    
    session.close()

if __name__ == "__main__":
    print("🔍 ЗАПУСК ОТЛАДКИ СИСТЕМЫ НАПОМИНАНИЙ")
    print()
    
    test_time_calculation()
    check_all_deadline_times()
    simulate_reminder_check()
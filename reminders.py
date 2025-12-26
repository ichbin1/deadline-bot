"""
reminders.py - Упрощенная система напоминаний
"""

import logging
from datetime import timedelta
from utils.time_utils import TimeManager
import database as db

logger = logging.getLogger(__name__)

class DeadlineReminder:
    """Класс для управления напоминаниями о дедлайнах"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("Инициализирован менеджер напоминаний")
    
    async def check_and_send_reminders(self):
        """Основная функция проверки и отправки напоминаний"""
        logger.info("🔔 Запуск проверки напоминаний...")
        
        # 1. Проверяем личные дедлайны
        await self.check_personal_deadlines()
        
        # 2. Проверяем групповые дедлайны
        await self.check_group_deadlines()
        
        logger.info("✅ Проверка напоминаний завершена")
    
    async def check_personal_deadlines(self):
    """Проверяет личные дедлайны и отправляет напоминания"""
    try:
        session = db.Session()
        
        # Личные дедлайны, которые еще не выполнены
        deadlines = session.query(db.Deadline).filter(
            db.Deadline.is_completed == False
        ).all()
        
        logger.info(f"🔍 Найдено {len(deadlines)} активных личных дедлайнов")
        
        for deadline in deadlines:
            user = session.query(db.User).filter(db.User.id == deadline.user_id).first()
            if not user:
                continue
            
            # Используем TimeManager для проверки напоминаний
            if TimeManager.is_in_reminder_window(deadline.deadline, "week"):
                if user.notify_week and not deadline.reminded_week:
                    await self.send_personal_reminder(user.telegram_id, deadline, "неделю")
                    deadline.reminded_week = True
                    session.commit()
            
            elif TimeManager.is_in_reminder_window(deadline.deadline, "day"):
                if user.notify_day and not deadline.reminded_day:
                    await self.send_personal_reminder(user.telegram_id, deadline, "день")
                    deadline.reminded_day = True
                    session.commit()
            
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка при проверке личных дедлайнов: {e}", exc_info=True)

async def check_group_deadlines(self):
    """Проверяет групповые дедлайны и отправляет напоминания"""
    try:
        session = db.Session()
        
        deadlines = session.query(db.GroupDeadline).all()
        logger.info(f"Найдено {len(deadlines)} групповых дедлайнов")
        
        for deadline in deadlines:
            users = session.query(db.User).filter(
                db.User.group_name == deadline.group_name
            ).all()
            
            if not users:
                continue
            
            # Проверяем каждое напоминание только один раз для дедлайна
            for reminder_type in ["week", "day"]:  # Убрали "hour"
                if TimeManager.is_in_reminder_window(deadline.deadline, reminder_type):
                    # Получаем соответствующее поле флага
                    flag_field = f"reminded_{reminder_type}"
                    
                    # Проверяем, не отправляли ли уже это напоминание
                    if not getattr(deadline, flag_field):
                        # Отправляем всем пользователям группы
                        for user in users:
                            if getattr(user, f"notify_{reminder_type}"):
                                await self.send_group_reminder(user.telegram_id, deadline, reminder_type)
                        
                        # Обновляем флаг
                        setattr(deadline, flag_field, True)
                        session.commit()
                        break  # Переходим к следующему дедлайну
        
        session.close()
        
    except Exception as e:
        logger.error(f"Ошибка при проверке групповых дедлайнов: {e}", exc_info=True)

def _format_reminder_message(self, deadline, deadline_moscow, time_left, time_unit, is_personal):
    """Форматирует сообщение напоминания"""
    # Определяем срочность
    urgency_map = {
        "день": ("⚠️", "Завтра дедлайн!"),
        "неделю": ("🔔", "Напоминание")
    }
    
    emoji, urgency = urgency_map.get(time_unit, ("🔔", "Напоминание"))
    time_left_str = TimeManager.format_time_left(time_left)
    
    if is_personal:
        message = f"""{emoji} **{urgency}**

До твоего дедлайна осталось **{time_left_str}**!

📝 **Личный дедлайн**
📚 {deadline.subject}
📋 {deadline.task}
🏷️ Приоритет: {deadline.priority}
⏰ Дедлайн: {TimeManager.format_for_display(deadline_moscow)}

Не забудь выполнить задание вовремя! 💪
"""
    else:
        importance = "⚠️ **ВАЖНЫЙ ДЛЯ ВСЕЙ ГРУППЫ**\n" if deadline.is_important else ""
        message = f"""{emoji} **{urgency}**
{importance}
До группового дедлайна осталось **{time_left_str}**!

👥 **Групповой дедлайн**
📚 {deadline.subject}
📋 {deadline.task}
📚 Категория: {deadline.category}
⏰ Дедлайн: {TimeManager.format_for_display(deadline_moscow)}
👥 Группа: {deadline.group_name}

Не забудьте скоординироваться с группой! 👨‍👩‍👧‍👦
"""
    return message

    async def send_personal_reminder(self, user_id, deadline, time_unit):
        """Отправляет напоминание о личном дедлайне"""
        try:
            deadline_moscow = TimeManager.from_db_to_moscow(deadline.deadline)
            time_left = deadline_moscow - TimeManager.now()
            
            message = self._format_reminder_message(
                deadline, deadline_moscow, time_left, time_unit, is_personal=True
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Отправлено напоминание пользователю {user_id} о дедлайне {deadline.id}")
            
        except Exception as e:
            logger.error(f"❌ Не удалось отправить напоминание пользователю {user_id}: {e}")
    
    async def send_group_reminder(self, user_id, deadline, time_unit):
        """Отправляет напоминание о групповом дедлайне"""
        try:
            deadline_moscow = TimeManager.from_db_to_moscow(deadline.deadline)
            time_left = deadline_moscow - TimeManager.now()
            
            message = self._format_reminder_message(
                deadline, deadline_moscow, time_left, time_unit, is_personal=False
            )
            
            await self.bot.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ Отправлено групповое напоминание пользователю {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Не удалось отправить групповое напоминание пользователю {user_id}: {e}")

    @staticmethod
    def format_time_left(time_left: timedelta) -> str:
        """
        Форматирует оставшееся время в читаемый вид
        """
        total_seconds = int(time_left.total_seconds())
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        if days > 0:
            return f"{days} дней {hours} часов"
        elif hours > 0:
            return f"{hours} часов {minutes} минут"
        else:
            return f"{minutes} минут"

# ========== УТИЛИТЫ ==========

    async def setup_reminder_job(application):
        """
        Настраивает периодическую задачу для проверки напоминаний
        """
        from telegram.ext import JobQueue
        
        # Создаем экземпляр менеджера напоминаний
        reminder = DeadlineReminder(application.bot)
        
        # Запускаем задачу каждые 6 часов (21600 секунд)
        job_queue = application.job_queue
        job_queue.run_repeating(
            callback=reminder.check_and_send_reminders,
            interval=21600,  # 6 часов в секундах
            first=10         # Первый запуск через 10 секунд
        )
        
        logger.info("✅ Планировщик напоминаний запущен (интервал: 6 часов)")
        
        return reminder

# ========== ТЕСТОВЫЕ ФУНКЦИИ ==========

def test_reminder_logic():
    """
    Тестирует логику напоминаний с новыми окнами
    """
    print("🧪 Тестирование логики напоминаний с окнами")
    print("=" * 60)
    
    from datetime import datetime, timedelta
    
    # Текущее время
    now = datetime.now()
    
    # Тестовые временные точки
    test_times = [
        ("Через 7 дней ровно", now + timedelta(days=7)),
        ("Через 7 дней - 30 секунд", now + timedelta(days=7) - timedelta(seconds=30)),
        ("Через 7 дней + 30 секунд", now + timedelta(days=7) + timedelta(seconds=30)),
        ("Через 1 день ровно", now + timedelta(days=1)),
        ("Через 1 день - 30 секунд", now + timedelta(days=1) - timedelta(seconds=30)),
        ("Через 1 день + 30 секунд", now + timedelta(days=1) + timedelta(seconds=30)),
        ("Через 1 час ровно", now + timedelta(hours=1)),
        ("Через 1 час - 30 секунд", now + timedelta(hours=1) - timedelta(seconds=30)),
        ("Через 1 час + 30 секунд", now + timedelta(hours=1) + timedelta(seconds=30)),
    ]
    
    window = timedelta(minutes=1)
    
    for name, test_time in test_times:
        time_left = test_time - now
        
        week_target = timedelta(days=7)
        day_target = timedelta(days=1)
        hour_target = timedelta(hours=1)
        
        week_ok = (week_target - window) <= time_left <= (week_target + window)
        day_ok = (day_target - window) <= time_left <= (day_target + window)
        hour_ok = (hour_target - window) <= time_left <= (hour_target + window)
        
        print(f"{name}:")
        print(f"  Осталось: {time_left}")
        print(f"  За неделю: {'✅' if week_ok else '❌'}")
        print(f"  За день: {'✅' if day_ok else '❌'}")
        print(f"  За час: {'✅' if hour_ok else '❌'}")
        print()
    
    print("=" * 60)
    print("✅ Тестирование завершено!")
    print("=" * 60)

if __name__ == "__main__":
    test_reminder_logic()
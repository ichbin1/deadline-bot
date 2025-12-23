"""
utils/time_utils.py - Утилиты для работы с временем и часовыми поясами
"""

from datetime import datetime, timedelta
from typing import Optional, Union
import pytz
import logging

logger = logging.getLogger(__name__)

# Константы часовых поясов
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
UTC_TZ = pytz.UTC

class TimeManager:
    """Класс для управления временем и часовыми поясами"""
    
    @staticmethod
    def now() -> datetime:
        """Текущее время в московском часовом поясе"""
        return datetime.now(MOSCOW_TZ)
    
    @staticmethod
    def now_utc() -> datetime:
        """Текущее время в UTC"""
        return datetime.now(UTC_TZ)
    
    @staticmethod
    def parse_user_input(date_str: str, time_str: str = "23:59") -> datetime:
        """
        Парсит ввод пользователя в московское время
        
        Args:
            date_str: Дата в формате "YYYY-MM-DD" или "DD.MM.YYYY"
            time_str: Время в формате "HH:MM" (по умолчанию 23:59)
        
        Returns:
            datetime в московском часовом поясе
        """
        try:
            # Пробуем разные форматы даты
            for date_format in ["%Y-%m-%d", "%d.%m.%Y", "%d.%m.%y"]:
                try:
                    date_obj = datetime.strptime(date_str, date_format)
                    break
                except ValueError:
                    continue
            else:
                raise ValueError(f"Неверный формат даты: {date_str}")
            
            # Парсим время
            time_obj = datetime.strptime(time_str, "%H:%M")
            
            # Комбинируем дату и время
            naive_dt = datetime.combine(date_obj.date(), time_obj.time())
            
            # Локализуем в московское время
            return MOSCOW_TZ.localize(naive_dt)
            
        except Exception as e:
            logger.error(f"Ошибка парсинга времени: {e}")
            raise ValueError(f"Неверный формат времени. Используйте: ГГГГ-ММ-ДД ЧЧ:ММ")
    
    @staticmethod
    def to_utc_for_db(moscow_dt: datetime) -> datetime:
        """
        Конвертирует московское время в UTC для сохранения в БД
        
        Args:
            moscow_dt: datetime в московском часовом поясе
        
        Returns:
            datetime в UTC (наивный, без часового пояса)
        """
        if moscow_dt.tzinfo is None:
            # Если время наивное, считаем что это московское
            moscow_dt = MOSCOW_TZ.localize(moscow_dt)
        
        utc_dt = moscow_dt.astimezone(UTC_TZ)
        # Возвращаем наивное время (убираем часовой пояс для SQLite)
        return utc_dt.replace(tzinfo=None)
    
    @staticmethod
    def from_db_to_moscow(naive_dt: datetime) -> datetime:
        """
        Конвертирует наивное время из БД (предположительно UTC) в московское
        
        Args:
            naive_dt: datetime из БД (без часового пояса)
        
        Returns:
            datetime в московском часовом поясе
        """
        # Предполагаем, что время в БД хранится в UTC
        utc_dt = UTC_TZ.localize(naive_dt)
        return utc_dt.astimezone(MOSCOW_TZ)
    
    @staticmethod
    def format_for_display(dt: datetime, include_seconds: bool = False) -> str:
        """
        Форматирует время для отображения пользователю
        
        Args:
            dt: datetime для форматирования
            include_seconds: Включать ли секунды
        
        Returns:
            Строка в формате "дд.мм.гггг чч:мм"
        """
        if dt.tzinfo is None:
            # Если время наивное, конвертируем в московское
            dt = TimeManager.from_db_to_moscow(dt)
        
        format_str = "%d.%m.%Y %H:%M"
        if include_seconds:
            format_str = "%d.%m.%Y %H:%M:%S"
        
        return dt.strftime(format_str)
    
    @staticmethod
    def format_time_left(time_left: timedelta) -> str:
        """
        Форматирует оставшееся время в читаемый вид
        
        Args:
            time_left: timedelta
        
        Returns:
            Строка вида "2 дня 5 часов" или "3 часа 15 минут"
        """
        total_seconds = int(time_left.total_seconds())
        if total_seconds < 0:
            return "ПРОСРОЧЕНО"
        
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        minutes = (total_seconds % 3600) // 60
        
        if days > 0:
            return f"{days} дней {hours} часов"
        elif hours > 0:
            return f"{hours} часов {minutes} минут"
        else:
            return f"{minutes} минут"
    
    @staticmethod
    def is_in_reminder_window(deadline_dt: datetime, reminder_type: str, window_minutes: int = 5) -> bool:
        """
        Проверяет, находится ли дедлайн в окне напоминания
        
        Args:
            deadline_dt: Время дедлайна
            reminder_type: "week", "day" или "hour"
            window_minutes: Окно в минутах
        
        Returns:
            True если нужно отправить напоминание
        """
        now = TimeManager.now()
        
        # Приводим оба времени к московскому поясу
        if deadline_dt.tzinfo is None:
            deadline_dt = TimeManager.from_db_to_moscow(deadline_dt)
        
        time_left = deadline_dt - now
        
        # Определяем целевое время для напоминания
        if reminder_type == "week":
            target = timedelta(days=7)
        elif reminder_type == "day":
            target = timedelta(days=1)
        elif reminder_type == "hour":
            target = timedelta(hours=1)
        else:
            return False
        
        window = timedelta(minutes=window_minutes)
        
        # Проверяем двустороннее окно
        return (target - window) <= time_left <= (target + window)
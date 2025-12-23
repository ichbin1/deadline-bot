"""
database.py - База данных для бота дедлайнов с поддержкой групповых и личных задач
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from utils.time_utils import TimeManager
from datetime import datetime
import logging
import pytz

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()

class User(Base):
    """
    Таблица пользователей
    Хранит информацию о пользователях бота
    """
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)  # ID в Telegram
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    group_name = Column(String, nullable=True)  # Название группы
    is_admin = Column(Boolean, default=False)  # Администратор группы
    created_at = Column(DateTime, default=datetime.now)
    notify_week = Column(Boolean, default=True)
    notify_day = Column(Boolean, default=True)
    notify_hour = Column(Boolean, default=True)
    
    # Связи с другими таблицами
    deadlines = relationship("Deadline", back_populates="user")
    group_deadlines = relationship("GroupDeadline", back_populates="creator")

class Deadline(Base):
    """
    Таблица личных дедлайнов
    """
    __tablename__ = 'personal_deadlines'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject = Column(String, nullable=False)
    task = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    priority = Column(String, default="Средний")  # Высокий, Средний, Низкий
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Флаги напоминаний
    reminded_week = Column(Boolean, default=False)
    reminded_day = Column(Boolean, default=False)
    reminded_hour = Column(Boolean, default=False)
    
    # Связь с пользователем
    user = relationship("User", back_populates="deadlines")
    
    def __repr__(self):
        return f"Личный дедлайн: {self.subject} - {self.task}"

    @property
    def deadline_moscow(self):
        """Получить время дедлайна в московском часовом поясе"""
        return TimeManager.from_db_to_moscow(self.deadline)
    
    @property
    def time_left(self):
        """Оставшееся время до дедлайна"""
        from utils.time_utils import TimeManager
        deadline_moscow = self.deadline_moscow
        return deadline_moscow - TimeManager.now()

class GroupDeadline(Base):
    """
    Таблица общих дедлайнов для группы
    """
    __tablename__ = 'group_deadlines'
    
    id = Column(Integer, primary_key=True)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    subject = Column(String, nullable=False)
    task = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    group_name = Column(String, nullable=False, default="Общая группа")
    category = Column(String, default="Учеба")  # Категория: Учеба, Работа, Проект и т.д.
    is_important = Column(Boolean, default=False)  # Важный дедлайн для всех
    created_at = Column(DateTime, default=datetime.now)
    
    # Флаги напоминаний
    reminded_week = Column(Boolean, default=False)
    reminded_day = Column(Boolean, default=False)
    reminded_hour = Column(Boolean, default=False)
    
    # Связь с создателем
    creator = relationship("User", back_populates="group_deadlines")
    
    def __repr__(self):
        return f"Групповой дедлайн: {self.subject} - {self.task}"

    @property
    def deadline_moscow(self):
        """Получить время дедлайна в московском часовом поясе"""
        return TimeManager.from_db_to_moscow(self.deadline)
    
    @property
    def time_left(self):
        """Оставшееся время до дедлайна"""
        from utils.time_utils import TimeManager
        deadline_moscow = self.deadline_moscow
        return deadline_moscow - TimeManager.now()

class UserGroupDeadline(Base):
    """
    Таблица для связи пользователей с групповыми дедлайнами
    (если пользователь отмечает групповой дедлайн как "важный для себя")
    """
    __tablename__ = 'user_group_deadlines'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    group_deadline_id = Column(Integer, ForeignKey('group_deadlines.id'), nullable=False)
    is_subscribed = Column(Boolean, default=True)  # Подписан на напоминания
    created_at = Column(DateTime, default=datetime.now)
    
    # Простой вариант без ForeignKeyConstraint
    __table_args__ = ()
    
    def __repr__(self):
        return f"Подписка пользователя {self.user_id} на дедлайн {self.group_deadline_id}"

# Создаем движок базы данных
engine = create_engine('sqlite:///deadlines.db', echo=False)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# ========== ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ==========

def get_or_create_user(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None):
    """
    Получает пользователя из базы или создает нового
    Возвращает объект User или None при ошибке
    """
    session = Session()
    try:
        # Ищем существующего пользователя
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        
        if user:
            # Обновляем данные, если они изменились
            update_needed = False
            if username and user.username != username:
                user.username = username
                update_needed = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                update_needed = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                update_needed = True
                
            if update_needed:
                session.commit()
                logger.info(f"Обновлены данные пользователя {telegram_id}")
        else:
            # Создаем нового пользователя
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                group_name=None,  # НИКАКОЙ ГРУППЫ ПО УМОЛЧАНИЮ
                created_at=datetime.now()
            )
            session.add(user)
            session.commit()
            logger.info(f"Создан новый пользователь {telegram_id}")
        
        return user
        
    except Exception as e:
        logger.error(f"Ошибка в get_or_create_user для {telegram_id}: {e}")
        session.rollback()
        return None
        
    finally:
        session.close()

def set_user_group(telegram_id, group_name):
    """
    Устанавливает группу для пользователя
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.group_name = group_name
            session.commit()
            logger.info(f"Пользователь {telegram_id} добавлен в группу {group_name}")
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при установке группы: {e}")
        return False
    finally:
        session.close()

def get_user_by_telegram_id(telegram_id):
    """
    Получает пользователя по его Telegram ID
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return user
    finally:
        session.close()

# ========== ФУНКЦИИ ДЛЯ ЛИЧНЫХ ДЕДЛАЙНОВ ==========

def add_personal_deadline(telegram_id, subject, task, deadline, priority="Средний"):
    """
    Добавляет личный дедлайн
    
    Args:
        telegram_id: ID пользователя в Telegram
        subject: Название предмета
        task: Описание задания
        deadline: datetime (ожидается в московском времени)
        priority: Приоритет
        
    Returns:
        ID дедлайна или None при ошибке
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"Пользователь {telegram_id} не найден")
            return None
        
        # Конвертируем московское время в UTC для БД
        if deadline.tzinfo is None:
            # Если время наивное, считаем что это московское
            deadline = TimeManager.to_utc_for_db(deadline)
        else:
            # Если с часовым поясом, конвертируем
            deadline = TimeManager.to_utc_for_db(deadline)
        
        new_deadline = Deadline(
            user_id=user.id,
            subject=subject,
            task=task,
            deadline=deadline,  # Теперь в UTC
            priority=priority
        )
        session.add(new_deadline)
        session.commit()
        logger.info(f"Добавлен личный дедлайн для {telegram_id}: {subject}")
        return new_deadline.id
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при добавлении личного дедлайна: {e}")
        return None
    finally:
        session.close()

def get_personal_deadlines(telegram_id, include_completed=False):
    """
    Получает личные дедлайны пользователя
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return []
        
        query = session.query(Deadline).filter(Deadline.user_id == user.id)
        
        if not include_completed:
            query = query.filter(Deadline.is_completed == False)
        
        deadlines = query.order_by(Deadline.deadline).all()
        return deadlines
    finally:
        session.close()

def mark_personal_deadline_completed(deadline_id, telegram_id):
    """
    Отмечает личный дедлайн как выполненный
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        deadline = session.query(Deadline).filter(
            Deadline.id == deadline_id,
            Deadline.user_id == user.id
        ).first()
        
        if deadline:
            deadline.is_completed = True
            session.commit()
            logger.info(f"Дедлайн {deadline_id} отмечен как выполненный")
            return True
        return False
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при отметке дедлайна: {e}")
        return False
    finally:
        session.close()

# ========== ФУНКЦИИ ДЛЯ ГРУППОВЫХ ДЕДЛАЙНОВ ==========

def add_group_deadline(creator_telegram_id, subject, task, deadline, group_name, category="homework", is_important=False):
    """
    Добавляет групповой дедлайн
    
    Args:
        creator_telegram_id: ID создателя в Telegram
        subject: Название предмета
        task: Описание задания
        deadline: datetime (ожидается в московском времени)
        group_name: Название группы
        category: Категория
        is_important: Важный ли дедлайн
        
    Returns:
        ID дедлайна или None при ошибке
    """
    session = Session()
    try:
        creator = session.query(User).filter(User.telegram_id == creator_telegram_id).first()
        if not creator:
            logger.error(f"Создатель {creator_telegram_id} не найден")
            return None
        
        # Конвертируем московское время в UTC для БД
        deadline_utc = TimeManager.to_utc_for_db(deadline)
        
        new_deadline = GroupDeadline(
            creator_id=creator.id,
            subject=subject,
            task=task,
            deadline=deadline_utc,  # Теперь в UTC
            group_name=group_name,
            category=category,
            is_important=is_important
        )
        session.add(new_deadline)
        session.commit()
        logger.info(f"Добавлен групповой дедлайн: {subject} для группы {group_name}")
        return new_deadline.id
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при добавлении группового дедлайна: {e}")
        return None
    finally:
        session.close()

def get_group_deadlines(group_name=None, category=None):
    """
    Получает групповые дедлайны
    """
    session = Session()
    try:
        query = session.query(GroupDeadline)
        
        if group_name:
            query = query.filter(GroupDeadline.group_name == group_name)
        
        if category:
            query = query.filter(GroupDeadline.category == category)
        
        # Не показываем прошедшие дедлайны
        query = query.filter(GroupDeadline.deadline >= datetime.now())
        
        deadlines = query.order_by(GroupDeadline.deadline).all()
        return deadlines
    finally:
        session.close()

def get_user_group_deadlines(telegram_id):
    """
    Получает групповые дедлайны для конкретного пользователя
    (дедлайны его группы)
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user or not user.group_name:
            return []
        
        deadlines = session.query(GroupDeadline).filter(
            GroupDeadline.group_name == user.group_name,
            GroupDeadline.deadline >= datetime.now()
        ).order_by(GroupDeadline.deadline).all()
        
        return deadlines
    finally:
        session.close()

def subscribe_to_group_deadline(telegram_id, group_deadline_id):
    """
    Подписывает пользователя на групповой дедлайн
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        # Проверяем, не подписан ли уже
        existing = session.query(UserGroupDeadline).filter(
            UserGroupDeadline.user_id == user.id,
            UserGroupDeadline.group_deadline_id == group_deadline_id
        ).first()
        
        if existing:
            return False  # Уже подписан
        
        subscription = UserGroupDeadline(
            user_id=user.id,
            group_deadline_id=group_deadline_id,
            is_subscribed=True
        )
        session.add(subscription)
        session.commit()
        logger.info(f"Пользователь {telegram_id} подписался на групповой дедлайн {group_deadline_id}")
        return True
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при подписке: {e}")
        return False
    finally:
        session.close()

# ========== ОБЩИЕ ФУНКЦИИ ==========

def get_all_upcoming_deadlines():
    """
    Получает все предстоящие дедлайны (личные и групповые)
    """
    personal = []
    group = []
    
    session = Session()
    try:
        # Личные дедлайны (не выполненные)
        personal = session.query(Deadline).filter(
            Deadline.is_completed == False,
            Deadline.deadline >= datetime.now()
        ).order_by(Deadline.deadline).all()
        
        # Групповые дедлайны
        group = session.query(GroupDeadline).filter(
            GroupDeadline.deadline >= datetime.now()
        ).order_by(GroupDeadline.deadline).all()
        
    finally:
        session.close()
    
    return personal, group

def delete_personal_deadline(deadline_id, telegram_id):
    """
    Удаляет личный дедлайн
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        deadline = session.query(Deadline).filter(
            Deadline.id == deadline_id,
            Deadline.user_id == user.id
        ).first()
        
        if deadline:
            session.delete(deadline)
            session.commit()
            logger.info(f"Удален личный дедлайн {deadline_id}")
            return True
        return False
        
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при удалении личного дедлайна: {e}")
        return False
    finally:
        session.close()

def delete_group_deadline(deadline_id, telegram_id):
    """
    Удаляет групповой дедлайн (только создатель может удалить)
    """
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            return False
        
        deadline = session.query(GroupDeadline).filter(
            GroupDeadline.id == deadline_id,
            GroupDeadline.creator_id == user.id
        ).first()
        
        if deadline:
            session.delete(deadline)
            session.commit()
            logger.info(f"Удален групповой дедлайн {deadline_id}")
            return True
        return False
        
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при удалении группового дедлайна: {e}")
        return False
    finally:
        session.close()

# ========== ТЕСТОВЫЕ ФУНКЦИИ ==========

def test_database():
    """
    Тестирование базы данных
    """
    print("=" * 60)
    print("Тестирование базы данных с групповыми дедлайнами")
    print("=" * 60)
    
    # Создаем тестовых пользователей
    user1 = get_or_create_user(111111, "student1", "Иван", "Иванов")
    user2 = get_or_create_user(222222, "student2", "Мария", "Петрова")
    
    if user1 and user2:
        print("✅ Созданы тестовые пользователи")
        
        # Устанавливаем группу
        set_user_group(111111, "ИТ-101")
        set_user_group(222222, "ИТ-101")
        print("✅ Пользователи добавлены в группу ИТ-101")
        
        # Добавляем личные дедлайны
        personal_id1 = add_personal_deadline(
            111111, "Математика", "Домашняя работа 5", 
            datetime.now().replace(hour=23, minute=59), "Высокий"
        )
        personal_id2 = add_personal_deadline(
            222222, "Физика", "Лабораторная 3", 
            datetime.now().replace(hour=23, minute=59), "Средний"
        )
        
        if personal_id1 and personal_id2:
            print("✅ Добавлены личные дедлайны")
        
        # Добавляем групповые дедлайны
        group_id1 = add_group_deadline(
            111111, "Общий проект", "Сделать презентацию", 
            datetime.now().replace(hour=23, minute=59), "ИТ-101", "Проект", True
        )
        group_id2 = add_group_deadline(
            111111, "Экзамен", "Подготовка к экзамену", 
            datetime.now().replace(hour=23, minute=59), "ИТ-101", "Учеба", True
        )
        
        if group_id1 and group_id2:
            print("✅ Добавлены групповые дедлайны")
        
        # Получаем дедлайны
        personal_deadlines = get_personal_deadlines(111111)
        group_deadlines = get_group_deadlines("ИТ-101")
        
        print(f"📋 Личных дедлайнов у пользователя 111111: {len(personal_deadlines)}")
        print(f"👥 Групповых дедлайнов в ИТ-101: {len(group_deadlines)}")
        
        # Очистка тестовых данных
        delete_personal_deadline(personal_id1, 111111)
        delete_personal_deadline(personal_id2, 222222)
        delete_group_deadline(group_id1, 111111)
        delete_group_deadline(group_id2, 111111)
        print("✅ Тестовые данные удалены")
    
    print("=" * 60)
    print("Тестирование завершено!")
    print("=" * 60)

    log_current_time()

def log_current_time():
    """Логирует текущее время для отладки"""
    import pytz
    from datetime import datetime
    moscow_tz = pytz.timezone('Europe/Moscow')
    utc_now = datetime.now(pytz.UTC)
    moscow_now = utc_now.astimezone(moscow_tz)
    logger.info(f"Текущее время UTC: {utc_now.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Текущее время Москва: {moscow_now.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    test_database()
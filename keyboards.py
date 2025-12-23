"""
keyboards.py - Все клавиатуры для бота дедлайнов
"""

from telegram import (
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

# ========== КОНСТАНТЫ КАТЕГОРИЙ ==========

# Список категорий для групповых дедлайнов (ваша учебная группа)
CATEGORIES = {
    "homework": "📝 Домашняя работа",
    "test": "📄 Зачеты", 
    "project": "📋 Проекты",
    "document": "📑 Документы"
}

# Список приоритетов для личных дедлайнов
PRIORITIES = {
    "high": "🔴 Высокий",
    "medium": "🟡 Средний", 
    "low": "🟢 Низкий"
}

# ========== ОСНОВНЫЕ КЛАВИАТУРЫ (ReplyKeyboardMarkup) ==========

def get_main_keyboard():
    """
    Главное меню бота
    """
    keyboard = [
        ["📝 Добавить дедлайн", "📋 Мои дедлайны"],
        ["👥 Групповые дедлайны", "🔔 Напоминания"],
        ["⚙️ Настройки", "ℹ️ Помощь"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)

def get_settings_keyboard():
    """
    Клавиатура настроек
    """
    keyboard = [
        ["✏️ Изменить группу", "🔔 Настройки уведомлений"],
        ["👤 Профиль", "⬅️ Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_cancel_keyboard():
    """
    Клавиатура с кнопкой отмены
    """
    keyboard = [["❌ Отмена"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_back_keyboard():
    """
    Клавиатура с кнопкой назад
    """
    keyboard = [["⬅️ Назад"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

# ========== КЛАВИАТУРЫ ДЛЯ ДОБАВЛЕНИЯ ДЕДЛАЙНОВ ==========

def get_deadline_type_keyboard():
    """
    Выбор типа дедлайна (личный/групповой)
    """
    keyboard = [
        ["👤 Личный дедлайн", "👥 Групповой дедлайн"],
        ["❌ Отмена"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_priority_keyboard():
    """
    Выбор приоритета для личного дедлайна
    """
    keyboard = [
        [PRIORITIES["high"], PRIORITIES["medium"]],
        [PRIORITIES["low"], "❌ Отмена"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_category_keyboard():
    """
    Выбор категории для группового дедлайна
    (Обновлено под нужды учебной группы)
    """
    keyboard = [
        [CATEGORIES["homework"], CATEGORIES["test"]],
        [CATEGORIES["project"], CATEGORIES["document"]],
        ["❌ Отмена"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_importance_keyboard():
    """
    Выбор важности группового дедлайна
    """
    keyboard = [
        ["✅ Да, для всех", "➡️ Нет, просто добавить"],
        ["❌ Отмена"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== ИНЛАЙН КЛАВИАТУРЫ (InlineKeyboardMarkup) ==========

def get_deadline_actions_keyboard(deadline_id, deadline_type="personal"):
    """
    Клавиатура действий с дедлайном
    deadline_type: "personal" или "group"
    """
    keyboard = []
    
    if deadline_type == "personal":
        keyboard.append([
            InlineKeyboardButton("✅ Выполнено", callback_data=f"complete_personal_{deadline_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_personal_{deadline_id}")
        ])
    else:  # group
        keyboard.append([
            InlineKeyboardButton("🔔 Подписаться", callback_data=f"subscribe_{deadline_id}"),
            InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_group_{deadline_id}")
        ])
    
    keyboard.append([InlineKeyboardButton("✏️ Изменить", callback_data=f"edit_{deadline_type}_{deadline_id}")])
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
    
    return InlineKeyboardMarkup(keyboard)

def get_confirm_delete_keyboard(deadline_id, deadline_type="personal"):
    """
    Клавиатура подтверждения удаления
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{deadline_type}_{deadline_id}"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_delete")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_confirm_complete_keyboard(deadline_id):
    """
    Клавиатура подтверждения выполнения
    """
    keyboard = [
        [
            InlineKeyboardButton("✅ Да, выполнил", callback_data=f"confirm_complete_{deadline_id}"),
            InlineKeyboardButton("❌ Нет, отменить", callback_data="cancel_complete")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_deadlines_list_keyboard(deadlines, deadline_type="personal", page=0, page_size=5):
    """
    Клавиатура со списком дедлайнов для навигации
    """
    keyboard = []
    
    # Вычисляем индексы для текущей страницы
    start_idx = page * page_size
    end_idx = start_idx + page_size
    current_deadlines = deadlines[start_idx:end_idx]
    
    # Добавляем кнопки с дедлайнами
    for deadline in current_deadlines:
        # Создаем текст кнопки (обрезаем, если слишком длинный)
        button_text = f"{deadline.subject}: {deadline.task[:20]}..."
        if len(button_text) > 30:
            button_text = button_text[:27] + "..."
        
        callback_data = f"view_{deadline_type}_{deadline.id}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
    
    # Добавляем кнопки навигации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{deadline_type}_{page-1}"))
    
    if end_idx < len(deadlines):
        nav_buttons.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{deadline_type}_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка закрытия
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close_list")])
    
    return InlineKeyboardMarkup(keyboard)

def get_group_selection_keyboard(groups):
    """
    Клавиатура для выбора группы из списка
    """
    keyboard = []
    
    # Добавляем кнопки с группами (максимум 2 в ряд)
    row = []
    for i, group in enumerate(groups):
        row.append(InlineKeyboardButton(group, callback_data=f"select_group_{group}"))
        if len(row) == 2 or i == len(groups) - 1:
            keyboard.append(row)
            row = []
    
    # Кнопка создания новой группы
    keyboard.append([InlineKeyboardButton("➕ Создать новую группу", callback_data="create_new_group")])
    
    return InlineKeyboardMarkup(keyboard)

def get_notification_settings_keyboard(current_settings):
    """
    Клавиатура настроек уведомлений
    current_settings - словарь с текущими настройками
    """
    # Получаем текущие значения или значения по умолчанию
    week = "✅" if current_settings.get("notify_week", True) else "❌"
    day = "✅" if current_settings.get("notify_day", True) else "❌"
    hour = "✅" if current_settings.get("notify_hour", True) else "❌"
    
    keyboard = [
        [
            InlineKeyboardButton(f"{week} За неделю", callback_data="toggle_week"),
            InlineKeyboardButton(f"{day} За день", callback_data="toggle_day")
        ],
        [
            InlineKeyboardButton(f"{hour} За час", callback_data="toggle_hour"),
            InlineKeyboardButton("✅ Все", callback_data="enable_all")
        ],
        [
            InlineKeyboardButton("❌ Никакие", callback_data="disable_all"),
            InlineKeyboardButton("💾 Сохранить", callback_data="save_notifications")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data="back_to_settings")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_edit_deadline_keyboard(deadline_id, deadline_type="personal"):
    """
    Клавиатура для редактирования дедлайна
    """
    keyboard = [
        [
            InlineKeyboardButton("✏️ Предмет", callback_data=f"edit_subject_{deadline_type}_{deadline_id}"),
            InlineKeyboardButton("📝 Задание", callback_data=f"edit_task_{deadline_type}_{deadline_id}")
        ],
        [
            InlineKeyboardButton("📅 Дата", callback_data=f"edit_date_{deadline_type}_{deadline_id}"),
            InlineKeyboardButton("🏷️ Приоритет" if deadline_type == "personal" else "📚 Категория", 
                               callback_data=f"edit_{'priority' if deadline_type == 'personal' else 'category'}_{deadline_type}_{deadline_id}")
        ],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"back_to_view_{deadline_type}_{deadline_id}")]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def get_category_selection_keyboard():
    """
    Инлайн клавиатура для выбора категории (для редактирования)
    """
    keyboard = []
    
    # Создаем кнопки для каждой категории
    for key, value in CATEGORIES.items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f"select_category_{key}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_category")])
    
    return InlineKeyboardMarkup(keyboard)

def get_priority_selection_keyboard():
    """
    Инлайн клавиатура для выбора приоритета (для редактирования)
    """
    keyboard = []
    
    # Создаем кнопки для каждого приоритета
    for key, value in PRIORITIES.items():
        keyboard.append([InlineKeyboardButton(value, callback_data=f"select_priority_{key}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_priority")])
    
    return InlineKeyboardMarkup(keyboard)

# ========== УТИЛИТЫ ==========

def remove_keyboard():
    """
    Убирает клавиатуру
    """
    return ReplyKeyboardRemove()

def get_yes_no_keyboard():
    """
    Простая клавиатура Да/Нет
    """
    keyboard = [["✅ Да", "❌ Нет"]]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_category_display_name(category_key):
    """
    Получить отображаемое имя категории по ключу
    """
    return CATEGORIES.get(category_key, "📝 Домашняя работа")

def get_priority_display_name(priority_key):
    """
    Получить отображаемое имя приоритета по ключу
    """
    return PRIORITIES.get(priority_key, "🟡 Средний")

def get_category_key_from_display(display_name):
    """
    Получить ключ категории по отображаемому имени
    """
    for key, value in CATEGORIES.items():
        if value == display_name:
            return key
    return "homework"  # значение по умолчанию

def get_priority_key_from_display(display_name):
    """
    Получить ключ приоритета по отображаемому имени
    """
    for key, value in PRIORITIES.items():
        if value == display_name:
            return key
    return "medium"  # значение по умолчанию

# ========== ТЕСТОВЫЕ ФУНКЦИИ ==========

def test_keyboards():
    """
    Тест всех клавиатур
    """
    print("🧪 Тестирование клавиатур с обновленными категориями")
    print("=" * 60)
    
    # Создаем тестовые данные
    class MockDeadline:
        def __init__(self, id, subject, task):
            self.id = id
            self.subject = subject
            self.task = task
    
    test_deadlines = [
        MockDeadline(1, 'Математика', 'Решить задачи 1-10'),
        MockDeadline(2, 'Физика', 'Лабораторная работа 3'),
        MockDeadline(3, 'Программирование', 'Написать код'),
    ]
    
    # Проверка категорий
    print("📋 Доступные категории:")
    for key, value in CATEGORIES.items():
        print(f"  {key}: {value}")
    
    print("\n📊 Доступные приоритеты:")
    for key, value in PRIORITIES.items():
        print(f"  {key}: {value}")
    
    print("\n1. Главное меню:")
    print(get_main_keyboard())
    
    print("\n2. Категории (обновленные):")
    print(get_category_keyboard())
    
    print("\n3. Приоритеты:")
    print(get_priority_keyboard())
    
    print("\n4. Выбор категории (инлайн):")
    print(get_category_selection_keyboard())
    
    print("\n5. Выбор приоритета (инлайн):")
    print(get_priority_selection_keyboard())
    
    # Проверка вспомогательных функций
    print("\n6. Проверка вспомогательных функций:")
    print(f"   Категория 'homework': {get_category_display_name('homework')}")
    print(f"   Приоритет 'high': {get_priority_display_name('high')}")
    
    category_display = CATEGORIES['project']
    print(f"   Обратное преобразование '{category_display}': {get_category_key_from_display(category_display)}")
    
    priority_display = PRIORITIES['low']
    print(f"   Обратное преобразование '{priority_display}': {get_priority_key_from_display(priority_display)}")
    
    print("\n" + "=" * 60)
    print("✅ Все клавиатуры созданы успешно!")
    print("=" * 60)

# ========== КЛАВИАТУРЫ ДЛЯ НАПОМИНАНИЙ ==========

def get_reminders_menu_keyboard():
    """
    Меню управления напоминаниями
    """
    keyboard = [
        ["📅 Ближайшие дедлайны"],
        ["🔕 Отключить напоминания"],
        ["⬅️ Назад"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

if __name__ == "__main__":
    test_keyboards()
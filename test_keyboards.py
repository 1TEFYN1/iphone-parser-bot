from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import test_config


# =====================
# Кнопки категорий (ГЛАВНОЕ МЕНЮ)
# =====================
def categories_keyboard():
    buttons = []
    row = []

    for cat in test_config.CATEGORY_NAMES:
        # Считаем количество для каждой категории
        if cat == "new":
            # Для "Новых" считаем ТОЛЬКО выгодные (is_bargain)
            count = len([
                ad for ad in test_config.ads_data
                if ad.get("status") == "new" and ad.get("is_bargain") == True
            ])
        else:
            # Для остальных считаем всё, что находится в этой папке
            count = len([
                ad for ad in test_config.ads_data
                if ad.get("status") == cat
            ])

        text = f"{test_config.CATEGORY_NAMES[cat]} ({count})"
        row.append(
            InlineKeyboardButton(text=text, callback_data=f"category:{cat}:0")
        )
        if len(row) == 2:
            buttons.append(row)
            row = []

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# =====================
# Кнопки телефонов (СПИСОК)
# =====================
def phones_keyboard(category, page, display_list):
    """
    display_list — это уже отфильтрованный список из handlers.py.
    Формат: [(index_in_db, ad_object), ...]
    """
    start = page * test_config.PAGE_SIZE
    end = start + test_config.PAGE_SIZE
    inline_keyboard = []

    # Берем срез для текущей страницы
    page_items = display_list[start:end]

    for idx_in_db, ad in page_items:
        # Формируем текст кнопки: Модель + Цена + Профит (если есть)
        title = ad.get("title", "Без названия")[:20]
        price = ad.get("price", "---")

        # Если это выгодное предложение, добавим эмодзи профита
        profit_mark = f" (+{ad['estimated_profit']})" if ad.get('is_bargain') else ""
        button_text = f"{title} | {price}{profit_mark}"

        # Используем оригинальный индекс из базы данных для callback
        inline_keyboard.append([
            InlineKeyboardButton(text=button_text, callback_data=f"phone:{idx_in_db}")
        ])

    # ===== Навигация по страницам =====
    total_pages = (len(display_list) - 1) // test_config.PAGE_SIZE + 1
    nav_row = []

    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️", callback_data=f"category:{category}:{page - 1}"))

    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="none"))

    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="➡️", callback_data=f"category:{category}:{page + 1}"))

    if nav_row:
        inline_keyboard.append(nav_row)

    # ===== Кнопка назад =====
    inline_keyboard.append([InlineKeyboardButton(text="🏠 К категориям", callback_data="back_to_categories")])

    return InlineKeyboardMarkup(inline_keyboard=inline_keyboard)


# =====================
# Кнопки в карточке телефона
# =====================
def phone_card_keyboard(idx):
    ad = test_config.ads_data[idx]
    current_cat = ad.get("status", "new")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🛠 В работе", callback_data=f"status:in_work:{idx}"),
            InlineKeyboardButton(text="✅ Куплено", callback_data=f"status:bought:{idx}")
        ],
        [InlineKeyboardButton(text="🗑 Мусор", callback_data=f"status:trash:{idx}")],
        [InlineKeyboardButton(text="⬅️ Назад к списку", callback_data=f"back:{current_cat}")]
    ])
    return kb
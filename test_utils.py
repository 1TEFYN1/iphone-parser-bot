import asyncio
import re
import statistics
from aiogram.types import Message
import test_config


# =====================
# Анимация загрузки
# =====================
async def animate_loading(message: Message):
    dots = [" .", " ..", " ..."]
    i = 0
    while test_config.scanning_lock.locked():
        try:
            await message.edit_text(f"🔍 Ищу выгодные iPhone{dots[i % 3]}")
            i += 1
            await asyncio.sleep(2)
        except Exception:
            break


# =====================
# Проверка чата
# =====================
async def check_chat(message: Message):
    if test_config.ALLOWED_CHAT_ID is not None and message.chat.id != test_config.ALLOWED_CHAT_ID:
        try:
            await message.delete()
        except Exception:
            pass
        return False
    return True


# =====================
# ВАЛЮТНАЯ АНАЛИТИКА
# =====================

def clean_price_to_mdl(price_str):
    """Приводит любую цену (MDL, EUR, USD) к леям для расчетов."""
    if not price_str: return None
    try:
        # Убираем пробелы и лишние символы
        clean_str = re.sub(r'\s+', '', price_str)
        # Извлекаем только цифры
        digits = "".join(re.findall(r'\d+', clean_str))
        if not digits: return None
        value = float(digits)

        # Конвертация на основе символа валюты
        price_upper = price_str.upper()
        if '€' in price_str or 'EUR' in price_upper:
            return value * test_config.EUR_TO_MDL
        if '$' in price_str or 'USD' in price_upper:
            return value * test_config.USD_TO_MDL

        return value  # По умолчанию MDL
    except:
        return None


def mdl_to_usd(amount_mdl):
    """Безопасный перевод из леев в доллары."""
    if not amount_mdl: return 0
    return round(amount_mdl / test_config.USD_TO_MDL)


# =====================
# ОПРЕДЕЛЕНИЕ МОДЕЛИ (С УЧЕТОМ ПАМЯТИ)
# =====================

def detect_model(title, storage=None):
    """
    Определяет модель iPhone и добавляет объем памяти,
    чтобы разделять их в статистике.
    """
    t = title.upper().replace(" ", "")

    models_map = {
        "iPhone 16 Pro Max": ["16PROMAX", "16PM"],
        "iPhone 16 Pro": ["16PRO"],
        "iPhone 16 Plus": ["16PLUS"],
        "iPhone 16": ["IPHONE16", " 16 "],
        "iPhone 15 Pro Max": ["15PROMAX", "15PM"],
        "iPhone 15 Pro": ["15PRO"],
        "iPhone 15 Plus": ["15PLUS"],
        "iPhone 15": ["IPHONE15", " 15 "],
        "iPhone 14 Pro Max": ["14PROMAX", "14PM"],
        "iPhone 14 Pro": ["14PRO"],
        "iPhone 14 Plus": ["14PLUS"],
        "iPhone 14": ["IPHONE14", " 14 "],
        "iPhone 13 Pro Max": ["13PROMAX", "13PM"],
        "iPhone 13 Pro": ["13PRO"],
        "iPhone 13 Mini": ["13MINI"],
        "iPhone 13": ["IPHONE13", " 13 "],
        "iPhone 12 Pro Max": ["12PROMAX", "12PM"],
        "iPhone 12 Pro": ["12PRO"],
        "iPhone 11 Pro Max": ["11PROMAX"],
        "iPhone 11 Pro": ["11PRO"],
        "iPhone 11": ["IPHONE11", " 11 "]
    }

    detected_name = "Other"
    for model_name, keys in models_map.items():
        if any(key in t for key in keys):
            detected_name = model_name
            break

    # Если модель найдена и передана память — склеиваем их в одну уникальную категорию
    if detected_name != "Other" and storage:
        # Чистим строку памяти (удаляем пробелы, приводим к виду 128GB)
        clean_storage = str(storage).upper().replace(" ", "")
        return f"{detected_name} {clean_storage}"

    return detected_name


# =====================
# ФИЛЬТРАЦИЯ МУСОРА
# =====================

def is_spam(title):
    """Отсекает магазины, заблокированные устройства и запчасти."""
    title_low = title.lower()

    bad_triggers = [
        "icloud", "id заблокирован", "mdm", "r-sim", "rsim",
        "на запчасти", "piese", "broken", "cracked", "not working",
        "bypass", "разблокирован программно"
    ]

    if any(trigger in title_low for trigger in bad_triggers):
        return True

    if title_low.count('/') > 2 or title_low.count('.') > 3 or title_low.count(',') > 3:
        return True

    for word in test_config.STOP_WORDS:
        if word in title_low:
            return True

    return False


# =====================
# МАТЕМАТИЧЕСКИЙ АНАЛИЗ
# =====================

def get_market_medians(all_ads):
    """Рассчитывает медианную цену для каждой связки Модель+Память."""
    stats = {}

    for ad in all_ads:
        if is_spam(ad['title']):
            continue

        # ВАЖНО: передаем поле storage из данных объявления
        model_key = detect_model(ad['title'], ad.get('storage'))

        if model_key == "Other":
            continue

        price_mdl = clean_price_to_mdl(ad['price'])

        if price_mdl and price_mdl > 2000:
            if model_key not in stats:
                stats[model_key] = []
            stats[model_key].append(price_mdl)

    medians = {}
    for key, prices in stats.items():
        # Т.к. данных по каждой памяти меньше, чем по модели в целом,
        # можно чуть снизить планку MIN_ADS_FOR_STATS в конфиге (например до 5)
        if len(prices) >= test_config.MIN_ADS_FOR_STATS:
            prices.sort()

            trim = max(1, len(prices) // 10)
            clean_prices = prices[trim:-trim] if len(prices) > 5 else prices

            if clean_prices:
                medians[key] = statistics.median(clean_prices)

    return medians
import json
import os
import statistics
import test_config
from test_utils import clean_price_to_mdl, detect_model, mdl_to_usd

# ЖЕСТКИЕ ПОРОГИ (Защита от мусора и запчастей)
# Если цена ниже этой планки, мы даже не смотрим на объявление
SAFE_FLOOR_USD = {
    "iPhone 16 Pro Max": 900, "iPhone 16 Pro": 800, "iPhone 16": 600,
    "iPhone 15 Pro Max": 700, "iPhone 15 Pro": 600, "iPhone 15": 400,
    "iPhone 14 Pro Max": 500, "iPhone 14 Pro": 400, "iPhone 14": 300,
    "iPhone 13 Pro Max": 350, "iPhone 13 Pro": 300, "iPhone 13": 250,
    "iPhone 12 Pro Max": 250, "iPhone 12 Pro": 200, "iPhone 12": 150
}


def get_storage_from_ad(ad):
    """
    Пытается найти объем памяти.
    Если не находит — возвращает None, чтобы объявление было пропущено.
    """
    # 1. Сначала ищем в поле 'storage' (которое заполнит обновленный парсер)
    if 'storage' in ad and ad['storage']:
        s = ad['storage'].upper().replace(" ГБ", "GB").replace(" ", "")
        if "GB" in s or "TB" in s:
            return s

    # 2. Если в поле пусто, ищем ключевые слова в заголовке
    title = ad.get('title', '').upper().replace(" ", "")
    for size in ['64', '128', '256', '512']:
        if f"{size}GB" in title:
            return f"{size}GB"
    if '1TB' in title or '1024GB' in title:
        return "1TB"

    # 3. Если память не найдена — возвращаем None
    return None


def get_cleaned_median(prices):
    """Отсекает 20% краев и берет медиану из центральной выборки"""
    if len(prices) < 5:
        return statistics.median(prices) if prices else 0

    sorted_p = sorted(prices)
    cut = int(len(sorted_p) * 0.2)
    trimmed = sorted_p[cut:-cut]
    return statistics.median(trimmed)


def analyze_real_ads_profit():
    file_path = 'ads.json'
    if not os.path.exists(file_path):
        print("❌ Ошибка: Файл ads.json не найден.")
        return

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            ads = json.load(f)
    except Exception as e:
        print(f"❌ Ошибка при чтении базы: {e}")
        return

    # 1. Собираем данные для рынка (только те, где есть ПАМЯТЬ)
    market_data = {}
    skipped_no_storage = 0

    for ad in ads:
        model = detect_model(ad['title'])
        if model == "Other":
            continue

        storage = get_storage_from_ad(ad)
        if storage is None:
            skipped_no_storage += 1
            continue  # ПРОПУСКАЕМ ОБЪЯВЛЕНИЕ БЕЗ ПАМЯТИ

        full_name = f"{model} {storage}"
        price_mdl = clean_price_to_mdl(ad['price'])

        if price_mdl:
            price_usd = price_mdl / test_config.USD_TO_MDL
            # Базовая проверка на мусор (по модели)
            if price_usd >= SAFE_FLOOR_USD.get(model, 100):
                if full_name not in market_data:
                    market_data[full_name] = []
                market_data[full_name].append(price_mdl)

    # Расчет очищенной медианы (РЫНОК) по каждой модификации
    medians = {}
    for name, prices in market_data.items():
        if len(prices) >= 2:  # Минимум 2 объявления для хоть какой-то статистики
            medians[name] = get_cleaned_median(prices)

    print("\n" + "=" * 115)
    print(f"📈 СТРАТЕГИЯ ЗАКУПКИ (Фильтр по памяти | Курс: {test_config.USD_TO_MDL} MDL)")
    print(f"ℹ️ Пропущено объявлений без указания памяти: {skipped_no_storage}")
    print("=" * 115)

    try:
        budget_limit_usd = float(input(f"💰 Введи свой макс. бюджет в $: "))
        budget_limit_mdl = budget_limit_usd * test_config.USD_TO_MDL
    except:
        return

    # 2. Анализируем выгодные варианты в твоем бюджете
    model_stats = {}
    for ad in ads:
        model = detect_model(ad['title'])
        storage = get_storage_from_ad(ad)

        if storage is None: continue

        full_name = f"{model} {storage}"
        price_mdl = clean_price_to_mdl(ad['price'])

        if full_name in medians and price_mdl:
            if price_mdl <= budget_limit_mdl:
                p_usd = price_mdl / test_config.USD_TO_MDL
                if p_usd < SAFE_FLOOR_USD.get(model, 50): continue

                market_mdl = medians[full_name]
                fast_sell_mdl = market_mdl * test_config.RESELL_DISCOUNT
                profit_mdl = fast_sell_mdl - price_mdl

                if full_name not in model_stats:
                    model_stats[full_name] = {'prices': [], 'profits': []}
                model_stats[full_name]['prices'].append(price_mdl)
                model_stats[full_name]['profits'].append(profit_mdl)

    if not model_stats:
        print(f"\n🤷 В бюджете до {budget_limit_usd}$ ничего не найдено (с учетом указанной памяти).")
        return

    print(f"\n✅ Результаты (отсортировано по прибыли):")
    print("-" * 115)
    header = f"{'Модель и Память':<25} | {'Шт.':<4} | {'Рынок ($)':<10} | {'Быстрая Пр. ($)':<16} | {'Твой Закуп ($)':<14} | {'Профит'}"
    print(header)
    print("-" * 115)

    # Сортировка по среднему профиту
    sorted_items = sorted(model_stats.items(),
                          key=lambda x: statistics.mean(x[1]['profits']),
                          reverse=True)

    for full_name, data in sorted_items:
        market_usd = mdl_to_usd(medians[full_name])
        fast_sell_usd = mdl_to_usd(medians[full_name] * test_config.RESELL_DISCOUNT)
        avg_buy_usd = mdl_to_usd(statistics.mean(data['prices']))
        avg_prof_usd = mdl_to_usd(statistics.mean(data['profits']))

        sign = "+" if avg_prof_usd > 0 else ""
        print(
            f"{full_name:<25} | {len(data['prices']):<4} | {market_usd:<10}$ | {fast_sell_usd:<16}$ | {avg_buy_usd:<14}$ | {sign}{avg_prof_usd}$")

    print("-" * 115)
    print("💡 РЫНОК — медиана для КОНКРЕТНОЙ памяти.")
    print("💡 ТВОЙ ЗАКУП — средняя цена подходящих объявлений в базе.")


if __name__ == "__main__":
    # Обновляем курс перед запуском
    test_config.USD_TO_MDL = test_config.get_current_usd_rate()
    analyze_real_ads_profit()
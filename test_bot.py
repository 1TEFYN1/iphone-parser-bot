import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

import test_config
from test_handlers import register_handlers
from test_storage import load_ads, save_ads
from test_scanner import scan_for_new_ads
from test_utils import get_market_medians, detect_model, clean_price_to_mdl, mdl_to_usd

# Настройка логирования
logging.basicConfig(level=logging.WARNING)

bot = Bot(
    token=test_config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Регистрируем обработчики кнопок и команд
register_handlers(dp)


async def auto_monitoring():
    """Фоновая задача: расчет прибыли в USD и MDL с защитой базы."""
    while True:
        print("\n--- Запуск автоматического сканирования (USD + MDL) ---")

        # 0. ОБНОВЛЕНИЕ КУРСОВ (USD и EUR к MDL)
        try:
            from test_config import get_current_eur_rate, get_current_usd_rate
            test_config.EUR_TO_MDL = get_current_eur_rate()
            test_config.USD_TO_MDL = get_current_usd_rate()
        except Exception as e:
            print(f"⚠️ Ошибка обновления курсов: {e}")

        async with test_config.scanning_lock:
            try:
                # 1. Загружаем текущую базу данных
                current_db = load_ads()
                db_size = len(current_db)

                # 2. Получаем новые объявления
                new_items = await asyncio.to_thread(scan_for_new_ads, current_db)

                if new_items:
                    urgent_deals = []
                    market_medians = get_market_medians(current_db)

                    for ad in new_items:
                        ad['status'] = "new"
                        ad['is_bargain'] = False

                        # Режим накопления (анализ выгоды не делаем, пока база < 200)
                        if db_size < 200:
                            continue

                        # ИЗМЕНЕНО: Передаем ad.get('storage'), чтобы модель определилась с памятью
                        model = detect_model(ad['title'], ad.get('storage'))
                        price_mdl = clean_price_to_mdl(ad['price'])

                        # АНАЛИЗ ВЫГОДЫ
                        if model != "Other" and model in market_medians and price_mdl:
                            median_mdl = market_medians[model]

                            # Считаем порог перепродажи в леях
                            resell_target_mdl = median_mdl * test_config.RESELL_DISCOUNT
                            profit_mdl = resell_target_mdl - price_mdl

                            # Конвертируем профит в USD
                            profit_usd = mdl_to_usd(profit_mdl)

                            if profit_usd >= test_config.MIN_PROFIT_USD:
                                ad['is_bargain'] = True
                                ad['p_mdl'] = int(price_mdl)
                                ad['p_usd'] = mdl_to_usd(price_mdl)
                                ad['profit_mdl'] = int(profit_mdl)
                                ad['profit_usd'] = profit_usd
                                ad['m_mdl'] = int(median_mdl)
                                ad['m_usd'] = mdl_to_usd(median_mdl)
                                ad['model_tag'] = model  # Здесь уже будет название с памятью, напр. "iPhone 13 128GB"
                                urgent_deals.append(ad)

                    # 4. Обновляем и сохраняем базу
                    test_config.ads_data = new_items + current_db
                    save_ads(test_config.ads_data)

                    # 5. ЛОГИКА УВЕДОМЛЕНИЙ
                    if db_size < 200:
                        print(f"📥 Накопление: {len(test_config.ads_data)}/200. Анализ отключен.")
                    elif urgent_deals:
                        for deal in urgent_deals:
                            text = (
                                f"🔥 <b>ВЫГОДНАЯ СДЕЛКА!</b>\n\n"
                                f"📱 Модель: <b>{deal['model_tag']}</b>\n"
                                f"💵 Цена: <b>{deal['p_usd']} $</b> ({deal['p_mdl']} MDL)\n"
                                f"📈 Профит: <b>~{deal['profit_usd']} $</b> ({deal['profit_mdl']} MDL)\n"
                                f"📊 Средний рынок: {deal['m_usd']} $ ({deal['m_mdl']} MDL)\n"
                                f"💱 Курс USD: {test_config.USD_TO_MDL} MDL\n\n"
                                f"🔗 <a href='{deal['link']}'>ОТКРЫТЬ НА 999.MD</a>"
                            )
                            await bot.send_message(test_config.ALLOWED_CHAT_ID, text)
                        print(f"✅ Найдено выгодных: {len(urgent_deals)}")
                    else:
                        print(f"🧐 В этом цикле выгоды нет (База: {len(test_config.ads_data)})")

                else:
                    test_config.ads_data = current_db
                    print("😴 Новых объявлений на 999.md нет.")

            except Exception as e:
                print(f"❌ Ошибка мониторинга: {e}")

        # Пауза между проверками (3 минуты)
        await asyncio.sleep(180)


async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="menu", description="📱 Витрина выгодных"),
        BotCommand(command="start", description="🚀 Запуск бота"),
    ]
    await bot.set_my_commands(commands)


async def main():
    test_config.ads_data = load_ads()
    print(f"🚀 Бот запущен! База: {len(test_config.ads_data)} объявлений.")
    await setup_bot_commands(bot)
    asyncio.create_task(auto_monitoring())
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Бот выключен.")
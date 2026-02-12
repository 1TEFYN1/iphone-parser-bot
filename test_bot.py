import asyncio
import logging
import os
from aiohttp import web
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

# Инициализация бота
bot = Bot(
    token=test_config.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()

# Регистрируем обработчики кнопок и команд
register_handlers(dp)

# =====================
# МИНИ-СЕРВЕР ДЛЯ RENDER
# =====================
async def handle_health_check(request):
    """Отвечает 'OK' на запросы Render, чтобы сервис не засыпал."""
    return web.Response(text="Bot is alive!", status=200)

async def start_web_server():
    """Запускает веб-сервер на порту 10000 (стандарт Render)."""
    app = web.Application()
    app.router.add_get('/', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render передает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"🌐 Мини-сервер запущен на порту {port}")

# =====================
# ФОНОВЫЙ МОНИТОРИНГ
# =====================
async def auto_monitoring():
    """Фоновая задача: расчет прибыли с учетом модели и памяти."""
    while True:
        print("\n--- Запуск автоматического сканирования (Модель + Память) ---")

        # Обновление курсов валют
        try:
            from test_config import get_current_eur_rate, get_current_usd_rate
            test_config.EUR_TO_MDL = get_current_eur_rate()
            test_config.USD_TO_MDL = get_current_usd_rate()
        except Exception as e:
            print(f"⚠️ Ошибка обновления курсов: {e}")

        async with test_config.scanning_lock:
            try:
                current_db = load_ads()
                db_size = len(current_db)

                # Получаем новые объявления через Selenium
                new_items = await asyncio.to_thread(scan_for_new_ads, current_db)

                if new_items:
                    urgent_deals = []
                    # Теперь медиана считается для связок "Модель + Память"
                    market_medians = get_market_medians(current_db)

                    for ad in new_items:
                        ad['status'] = "new"
                        ad['is_bargain'] = False

                        # Режим накопления
                        if db_size < 200:
                            continue

                        # Определяем модель С УЧЕТОМ памяти
                        model_key = detect_model(ad['title'], ad.get('storage'))
                        price_mdl = clean_price_to_mdl(ad['price'])

                        # Анализ выгоды
                        if model_key != "Other" and model_key in market_medians and price_mdl:
                            median_mdl = market_medians[model_key]

                            resell_target_mdl = median_mdl * test_config.RESELL_DISCOUNT
                            profit_mdl = resell_target_mdl - price_mdl
                            profit_usd = mdl_to_usd(profit_mdl)

                            if profit_usd >= test_config.MIN_PROFIT_USD:
                                ad['is_bargain'] = True
                                ad['p_mdl'] = int(price_mdl)
                                ad['p_usd'] = mdl_to_usd(price_mdl)
                                ad['profit_mdl'] = int(profit_mdl)
                                ad['profit_usd'] = profit_usd
                                ad['m_mdl'] = int(median_mdl)
                                ad['m_usd'] = mdl_to_usd(median_mdl)
                                ad['model_tag'] = model_key
                                urgent_deals.append(ad)

                    # Обновляем базу
                    test_config.ads_data = new_items + current_db
                    save_ads(test_config.ads_data)

                    # Рассылка уведомлений
                    if db_size < 200:
                        print(f"📥 Накопление базы: {len(test_config.ads_data)}/200")
                    elif urgent_deals:
                        for deal in urgent_deals:
                            text = (
                                f"🔥 <b>ВЫГОДНАЯ СДЕЛКА!</b>\n\n"
                                f"📱 Модель: <b>{deal['model_tag']}</b>\n"
                                f"💵 Цена: <b>{deal['p_usd']} $</b> ({deal['p_mdl']} MDL)\n"
                                f"📈 Профит: <b>~{deal['profit_usd']} $</b> ({deal['profit_mdl']} MDL)\n"
                                f"📊 Средний рынок: {deal['m_usd']} $ ({deal['m_mdl']} MDL)\n"
                                f"🔗 <a href='{deal['link']}'>ОТКРЫТЬ НА 999.MD</a>"
                            )
                            await bot.send_message(test_config.ALLOWED_CHAT_ID, text)
                        print(f"✅ Отправлено уведомлений: {len(urgent_deals)}")
                    else:
                        print(f"🧐 Выгоды не найдено (База: {len(test_config.ads_data)})")

                else:
                    test_config.ads_data = current_db
                    print("😴 Новых объявлений нет.")

            except Exception as e:
                print(f"❌ Ошибка в цикле мониторинга: {e}")

        await asyncio.sleep(180) # 3 минуты паузы

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="menu", description="📱 Витрина выгодных"),
        BotCommand(command="start", description="🚀 Запуск бота"),
    ]
    await bot.set_my_commands(commands)

async def main():
    test_config.ads_data = load_ads()
    print(f"🚀 Бот запускается. База: {len(test_config.ads_data)}")
    
    await setup_bot_commands(bot)
    
    # 1. Запускаем веб-сервер для Render (в фоне)
    asyncio.create_task(start_web_server())
    
    # 2. Запускаем мониторинг (в фоне)
    asyncio.create_task(auto_monitoring())
    
    # 3. Запускаем опрос Telegram
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Бот выключен.")

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import test_config
from test_utils import check_chat
from test_keyboards import categories_keyboard, phones_keyboard, phone_card_keyboard
from test_storage import save_ads


def register_handlers(dp: Dispatcher):
    # ===== Функция-фильтр для Telegram =====
    def get_display_list(category):
        """Возвращает список объявлений, отфильтрованных по выгоде."""
        # Находим все объявления нужной категории
        category_ads = [
            (i, ad) for i, ad in enumerate(test_config.ads_data)
            if ad.get('status') == category
        ]

        if category == "new":
            # Показываем только те, что помечены как выгодные (is_bargain)
            bargains = [item for item in category_ads if item[1].get('is_bargain') == True]
            # Сортируем: сначала те, где профит в $ выше
            return sorted(bargains, key=lambda x: x[1].get('profit_usd', 0), reverse=True)

        elif category == "trash":
            # В мусоре показываем последние 50, чтобы не перегружать бота
            return category_ads[-50:]

        else:
            # Для "В работе" и "Куплено"
            return category_ads

    # ===== Команда /start или /menu =====
    @dp.message(Command(commands=["start", "menu"]))
    async def menu_cmd(message: Message):
        if not await check_chat(message):
            return
        try:
            await message.delete()
        except Exception:
            pass

        await message.answer(
            "📱 <b>Мониторинг iPhone (USD/MDL)</b>\n\nВыберите категорию для просмотра выгодных сделок:",
            reply_markup=categories_keyboard(),
            parse_mode="HTML"
        )

    # ===== Обработка Callback =====
    @dp.callback_query()
    async def handle_callback(query: CallbackQuery):
        try:
            parts = query.data.split(":")
            cmd = parts[0]

            # 🏠 Возврат в меню
            if cmd == "back_to_categories":
                await query.message.edit_text(
                    "📱 <b>Главное меню:</b>",
                    reply_markup=categories_keyboard(),
                    parse_mode="HTML"
                )
                await query.answer()

            # 📂 Просмотр списка категории
            elif cmd == "category":
                if len(parts) < 3: return
                category, page = parts[1], int(parts[2])

                display_list = get_display_list(category)

                if not display_list:
                    await query.answer(f"📭 В категории {test_config.CATEGORY_NAMES.get(category)} пока пусто",
                                       show_alert=True)
                    return

                await query.message.edit_text(
                    f"📱 <b>{test_config.CATEGORY_NAMES.get(category)} ({len(display_list)}):</b>",
                    reply_markup=phones_keyboard(category, page, display_list),
                    parse_mode="HTML"
                )
                await query.answer()

            # 📄 Карточка конкретного телефона
            elif cmd == "phone":
                if len(parts) < 2: return
                idx = int(parts[1])

                if 0 <= idx < len(test_config.ads_data):
                    ad = test_config.ads_data[idx]

                    # Собираем данные (двойная валюта)
                    p_usd = ad.get('p_usd', '??')
                    p_mdl = ad.get('p_mdl', '??')

                    if ad.get('is_bargain'):
                        profit_info = (
                            f"📈 Профит: <b>~{ad.get('profit_usd')} $</b> ({ad.get('profit_mdl')} MDL)\n"
                            f"📊 Рынок: <b>{ad.get('m_usd')} $</b> ({ad.get('m_mdl')} MDL)\n"
                        )
                    else:
                        profit_info = "📊 <i>Стандартное предложение (не для перепродажи)</i>\n"

                    text = (f"📱 <b>{ad['title']}</b>\n\n"
                            f"💰 Цена: <b>{p_usd} $</b> ({p_mdl} MDL)\n"
                            f"{profit_info}\n"
                            f"🔗 <a href='{ad['link']}'>ОТКРЫТЬ НА 999.MD</a>")

                    await query.message.edit_text(
                        text,
                        reply_markup=phone_card_keyboard(idx),
                        parse_mode="HTML",
                        disable_web_page_preview=False
                    )
                else:
                    await query.answer("⚠️ Объявление не найдено", show_alert=True)
                await query.answer()

            # 🔄 Смена статуса (В работе / Мусор / Куплено)
            elif cmd == "status":
                if len(parts) < 3: return
                new_status, idx = parts[1], int(parts[2])

                if 0 <= idx < len(test_config.ads_data):
                    test_config.ads_data[idx]["status"] = new_status
                    save_ads(test_config.ads_data)
                    await query.answer(f"✅ Перенесено в {test_config.CATEGORY_NAMES.get(new_status)}")

                    # Возвращаемся в меню, чтобы обновить счетчики
                    await query.message.edit_text(
                        "📱 <b>Главное меню:</b>",
                        reply_markup=categories_keyboard(),
                        parse_mode="HTML"
                    )
                return

            # ⬅️ Назад к списку из карточки
            elif cmd == "back":
                if len(parts) < 2: return
                category = parts[1]
                display_list = get_display_list(category)
                await query.message.edit_text(
                    f"📱 <b>{test_config.CATEGORY_NAMES.get(category)}:</b>",
                    reply_markup=phones_keyboard(category, 0, display_list),
                    parse_mode="HTML"
                )
                await query.answer()

            elif cmd in ["ignore", "none"]:
                await query.answer()

        except Exception as e:
            if "message is not modified" not in str(e):
                print(f"Ошибка Callback: {e}")
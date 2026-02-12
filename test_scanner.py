import time
import re
from test_driver import create_driver
from test_config import URL, MAX_ADS, SCROLL_PAUSE, AD_PAGE_WAIT, STOP_WORDS, MAX_AGE_HOURS
from test_link_sniffer import collect_ad_links
from test_ad_parser import parse_ad

def scan_for_new_ads(existing_ads):
    # --- 0. ОЧИСТКА БАЗЫ (удаление старее 3 недель) ---
    current_time = time.time()
    cleaned_existing = [
        ad for ad in existing_ads
        if (current_time - ad.get('added_at', current_time)) / 3600 < MAX_AGE_HOURS
    ]
    existing_ads.clear()
    existing_ads.extend(cleaned_existing)

    known_links = {ad['link'] for ad in existing_ads}
    driver = create_driver(headless=True)
    new_found = []

    try:
        print(f"📡 Сбор свежих ссылок... (Актуально: {len(existing_ads)})")
        # Собираем ссылки (теперь это список простых строк/кортежей, они не "протухают")
        links = collect_ad_links(driver, URL, MAX_ADS, SCROLL_PAUSE)

        if not links:
            print("📭 На странице не найдено подходящих объявлений.")
            return []

        for title, link in links:
            # Очистка и фильтр СТОП-СЛОВ
            clean_title = title.lower().strip()
            if any(word in clean_title for word in STOP_WORDS):
                continue

            if link not in known_links:
                print(f"🔗 Анализ: {title[:40]}...")
                
                price = "Нет цены"
                storage = None

                try:
                    # Устанавливаем таймаут именно на загрузку страницы объявления
                    driver.set_page_load_timeout(25)
                    res = parse_ad(driver, link, AD_PAGE_WAIT)
                    
                    # Безопасная распаковка результата парсера
                    if isinstance(res, tuple):
                        price, storage = res
                    else:
                        price = res
                except Exception as e:
                    # Если страница виснет, пробуем принудительно остановить и прочитать что успело
                    print(f"⚠️ Долгая загрузка, пытаемся извлечь данные...")
                    try:
                        driver.execute_script("window.stop();")
                        res = parse_ad(driver, link, 1)
                        if isinstance(res, tuple):
                            price, storage = res
                        else:
                            price = res
                    except:
                        pass

                # --- РЕЗЕРВНЫЙ ПОИСК ПАМЯТИ В ЗАГОЛОВКЕ ---
                if not storage:
                    match = re.search(r'(\d{2,4})\s*(gb|гб|tb|тб)', clean_title)
                    if match:
                        storage = f"{match.group(1)} {match.group(2).upper()}"

                # Фильтр подозрительно низких цен
                trash_values = ["1 €", "111 €", "100 €", "10 €", "1 MDL", "Нет цены", "111 MDL"]
                if any(trash in price for trash in trash_values):
                    print(f"🗑 Пропущено (рекламная цена): {price}")
                    continue

                new_ad = {
                    "title": title.strip(),
                    "price": price,
                    "storage": storage,
                    "link": link,
                    "status": "new",
                    "added_at": current_time,
                    "is_bargain": False
                }

                new_found.append(new_ad)
                status_icon = "✅" if storage else "❓"
                print(f"{status_icon} Найдено: {price} | Память: {storage or 'Не определена'}")

                # Короткая пауза, чтобы 999.md не считал нас агрессивным ботом
                time.sleep(1.5)

    except Exception as e:
        print(f"❌ Критическая ошибка сканера: {e}")
    finally:
        if driver:
            driver.quit()

    return new_found

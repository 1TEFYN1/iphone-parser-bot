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
        links = collect_ad_links(driver, URL, MAX_ADS, SCROLL_PAUSE)

        for title, link in links:
            if any(word in title.lower() for word in STOP_WORDS):
                continue

            if link not in known_links:
                print(f"🔗 Анализ объявления: {title}")
                try:
                    driver.set_page_load_timeout(20)
                    # Вызываем обновленный парсер
                    res = parse_ad(driver, link, AD_PAGE_WAIT)
                    price, storage = res if isinstance(res, tuple) else (res, None)

                except Exception:
                    driver.execute_script("window.stop();")
                    print(f"⚠️ Долгая загрузка {link}, вытягиваем данные...")
                    res = parse_ad(driver, link, 1)
                    price, storage = res if isinstance(res, tuple) else (res, None)

                # --- РЕЗЕРВНЫЙ ПОИСК ПАМЯТИ В ЗАГОЛОВКЕ ---
                if not storage:
                    # Ищет: 64gb, 128 гб, 512 gb, 1tb, 1 тб
                    match = re.search(r'(\d{2,4})\s*(gb|гб|tb|тб)', title.lower())
                    if match:
                        storage = f"{match.group(1)} {match.group(2).upper()}"

                # Фильтр подозрительно низких цен (реклама/обман)
                trash_values = ["1 €", "111 €", "100 €", "10 €", "1 MDL", "Нет цены"]
                if any(trash in price for trash in trash_values):
                    print(f"🗑 Пропущено (рекламная цена): {price}")
                    continue

                new_ad = {
                    "title": title,
                    "price": price,
                    "storage": storage,
                    "link": link,
                    "status": "new",
                    "added_at": current_time,
                    "is_bargain": False
                }

                new_found.append(new_ad)

                status_icon = "✅" if storage else "❓"
                print(f"{status_icon} Найдено: {price} | Память: {storage or 'Не указана'}")

                # Пауза между заходами внутрь, чтобы не словить бан
                time.sleep(2)

    except Exception as e:
        print(f"❌ Критическая ошибка сканера: {e}")
    finally:
        driver.quit()

    return new_found
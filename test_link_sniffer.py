from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
import time

def collect_ad_links(driver, url, max_ads, scroll_pause):
    print(f"🌐 Открываем страницу: {url}")
    driver.get(url)
    time.sleep(5)  # Даем время на начальную загрузку скриптов

    ad_links = []
    seen_links = set()
    
    # Попытки скролла
    max_scrolls = 5 
    current_scroll = 0

    while len(ad_links) < max_ads and current_scroll < max_scrolls:
        # 1. Каждый раз ищем элементы заново после скролла, чтобы избежать StaleElement
        try:
            # Используем твой селектор обертки
            items = driver.find_elements(By.CSS_SELECTOR, "div.AdPhoto_wrapper__gAOIH")
        except Exception as e:
            print(f"⚠️ Ошибка при поиске элементов: {e}")
            break

        for item in items:
            try:
                # 2. Ищем ссылку внутри обертки
                link_el = item.find_element(By.CSS_SELECTOR, "a.AdPhoto_info__link__OwhY6")
                
                # Сразу вытягиваем текст и атрибут (это обычные строки, они не "протухают")
                title = link_el.text.strip()
                link = link_el.get_attribute("href")

                # Проверяем, что ссылка валидна и мы её еще не видели
                if title and link and "clickToken" not in link and link not in seen_links:
                    ad_links.append((title, link))
                    seen_links.add(link)
                    # print(f"📍 Найдено: {title[:30]}...")

                if len(ad_links) >= max_ads:
                    break

            except (NoSuchElementException, StaleElementReferenceException):
                # Если элемент исчез или изменился пока мы его читали — просто пропускаем
                continue

        if len(ad_links) < max_ads:
            # 3. Скроллим вниз для подгрузки новых объявлений
            driver.execute_script("window.scrollBy(0, 800);")
            time.sleep(scroll_pause)
            current_scroll += 1
        else:
            break

    print(f"✅ Всего собрано уникальных ссылок: {len(ad_links)}")
    return ad_links

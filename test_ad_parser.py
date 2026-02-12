from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time


def parse_ad(driver, link, wait_time):
    """
    Заходит внутрь объявления и вытягивает цену и память.
    """
    try:
        driver.get(link)
    except Exception as e:
        print(f"❌ Ошибка при загрузке страницы: {e}")
        return "Ошибка", None

    # Даем странице время на выполнение JS-скриптов
    time.sleep(wait_time)

    # Прокручиваем немного вниз, чтобы спровоцировать загрузку блока характеристик
    driver.execute_script("window.scrollBy(0, 400);")
    time.sleep(0.5)

    # 1. Извлекаем цену
    try:
        price_el = driver.find_element(By.CSS_SELECTOR, "span.styles_sidebar__main__DaXQC")
        price = price_el.text.strip()
    except NoSuchElementException:
        price = "Нет цены"

    # 2. Извлекаем память (универсальный XPath по тексту)
    storage = None
    try:
        # Ищем элемент, содержащий текст "Встроенная память", и берем ссылку-значение
        # Этот XPath ищет по всей ветке li, где есть упоминание памяти
        xpath_query = "//li[contains(., 'Встроенная память')]//a[@class='styles_group__value__XN7OI']"

        storage_el = WebDriverWait(driver, 4).until(
            EC.presence_of_element_located((By.XPATH, xpath_query))
        )
        storage = storage_el.text.strip()
    except (NoSuchElementException, TimeoutException):
        # Запасной вариант: поиск любого 'a' внутри li с текстом 'Встроенная память'
        try:
            storage = driver.find_element(By.XPATH, "//li[contains(span, 'Встроенная память')]//a").text.strip()
        except:
            storage = None

    return price, storage
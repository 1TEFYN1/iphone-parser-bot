from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def create_driver(headless=True):
    options = Options()

    # 1. ОСНОВНОЙ РЕЖИМ
    if headless:
        options.add_argument("--headless=new")

    # 2. ЭКСТРЕМАЛЬНАЯ ЭКОНОМИЯ ПАМЯТИ (Для Render 512MB)
    options.add_argument("--disable-dev-shm-usage") # Использовать /tmp вместо памяти
    options.add_argument("--no-sandbox")            # Нужно для Docker
    options.add_argument("--disable-gpu")           # Отключаем графику
    options.add_argument("--memory-pressure-off")   # Игнорировать нехватку памяти
    options.add_argument("--disable-extensions")    # Отключаем расширения
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-setuid-sandbox")
    
    # 3. МАСКИРОВКА ПОД РЕАЛЬНОГО ПОЛЬЗОВАТЕЛЯ
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 4. ОТКЛЮЧЕНИЕ ВСЕГО ЛИШНЕГО (Картинки, звуки, реклама)
    options.page_load_strategy = 'eager' # Грузим только текст и DOM
    prefs = {
        "profile.managed_default_content_settings.images": 2,     # Нет картинок
        "profile.default_content_setting_values.notifications": 2, # Нет пушей
        "profile.managed_default_content_settings.stylesheets": 2, # Нет стилей (дизайн нам не важен)
        "profile.managed_default_content_settings.fonts": 2,       # Нет шрифтов
        "profile.managed_default_content_settings.plugins": 2,     # Нет плагинов
        "profile.managed_default_content_settings.popups": 2,      # Нет поп-апов
    }
    options.add_experimental_option("prefs", prefs)

    # Установка через webdriver-manager (удобно для сервера)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Скрипт против детекта Selenium
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    # Жесткие лимиты на ожидание
    driver.set_page_load_timeout(25)
    driver.set_script_timeout(15)

    return driver

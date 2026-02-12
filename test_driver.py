from selenium import webdriver
from selenium.webdriver.chrome.options import Options


def create_driver(headless=True):
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    # 1. МАСКИРОВКА: Устанавливаем реальный User-Agent, чтобы сайт не видел бота
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    # 2. АНТИ-ДЕТЕКТ: Убираем признаки автоматизации
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 3. СТРАТЕГИЯ ЗАГРУЗКИ: 'eager' (текст без картинок)
    options.page_load_strategy = 'eager'
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2  # Отключаем пуши
    })

    # Стандартные настройки для стабильности
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # Защита от зависания в фоне
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-backgrounding-occluded-windows")

    driver = webdriver.Chrome(options=options)

    # Убираем программный признак webdriver из браузера (финальный штрих маскировки)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    driver.set_page_load_timeout(30)

    return driver
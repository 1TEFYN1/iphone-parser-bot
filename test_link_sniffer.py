from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

def collect_ad_links(driver, url, max_ads, scroll_pause):
    driver.get(url)
    time.sleep(5)

    ad_links = []
    seen = set()

    while len(ad_links) < max_ads:
        items = driver.find_elements(By.CSS_SELECTOR, "div.AdPhoto_wrapper__gAOIH")

        for item in items:
            try:
                link_el = item.find_element(By.CSS_SELECTOR, "a.AdPhoto_info__link__OwhY6")
                title = link_el.text.strip()
                link = link_el.get_attribute("href")

                if title and "clickToken" not in link and link not in seen:
                    ad_links.append((title, link))
                    seen.add(link)

                if len(ad_links) >= max_ads:
                    break

            except NoSuchElementException:
                continue

        driver.execute_script("window.scrollBy(0, 500);")
        time.sleep(scroll_pause)

    return ad_links

import requests
import time
import random
import logging
from bs4 import BeautifulSoup
from abc import ABC, abstractmethod
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

#log setup to file
logging.basicConfig(
    filename='scraper_errors.log',
    level=logging.ERROR,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class BaseScraper(ABC):
    def __init__(self, base_url, vendor_name):
        self.base_url = base_url
        self.vendor_name = vendor_name
        self.driver = None 
        
        #Identifies as a student project but looks like a normal browser
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/119.0.0.0 Safari/537.36 "
                          "(compatible; MarketPulseStudentProject/1.0)"
        }

    def _get_chrome_options(self):
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--log-level=3")
        options.add_experimental_option('excludeSwitches', ['enable-logging'])
        options.add_argument(f"user-agent={self.headers['User-Agent']}")
        #Block images/CSS to speed up loading
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        return options

    def setup_driver(self):
        """Initializes the browser ONCE to be reused."""
        if not self.driver:
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=self._get_chrome_options())

    def close_driver(self):
        """Closes the browser when the batch is finished."""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def _polite_delay(self):
        """Random delay (2-5s) to act like a human user."""
        time.sleep(random.uniform(2.0, 5.0))

    # Downloads the content of a page (for BeautifulSoup scrapers)
    def fetch_page(self, url):
        self._polite_delay()
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return BeautifulSoup(response.text, 'html.parser')
        except Exception as e:
            error_msg = f"❌ Error fetching {url}: {e}"
            print(error_msg)
            logging.error(error_msg)
            return None

    # Base logic implemented by each scraper
    @abstractmethod
    def scrape_product(self, product_url: str) -> dict | None:
        pass

    @abstractmethod
    def scrape_category(self, category_url: str) -> list[str]:
        """
        Visits a category page (e.g., 'All Laptops') and returns a list of product URLs found on it.
        """
        pass
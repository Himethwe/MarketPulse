from src.scrapers.base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re

class NanotekScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://www.nanotek.lk", vendor_name="Nanotek")

    def scrape_category(self, category_url: str) -> list[str]:
        """Scrapes all product URLs from a Nanotek category page."""
        self.setup_driver()
        if not self.driver: return []

        print(f"🔎 Scanning Category: {category_url}")
        try:
            self._polite_delay()
            self.driver.get(category_url)
            
            # Wait for products to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
            
            # Find all links on the page
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            product_urls = set()

            for link in all_links:
                href = link.get_attribute("href")
                # Nanotek product links always contain '/product/'
                if href and "/product/" in href:
                    product_urls.add(href)
            
            unique_urls = list(product_urls)
            print(f"   -> Found {len(unique_urls)} products.")
            return unique_urls

        except Exception as e:
            print(f"❌ Error scanning category: {e}")
            return []    

    def scrape_product(self, product_url: str) -> dict | None:
        self.setup_driver() 
        if not self.driver: return None

        try:
            self._polite_delay()
            self.driver.get(product_url)
            wait = WebDriverWait(self.driver, 10)
            
            #Name Extraction
            #Get ALL h1 elements
            h1s = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "h1")))
            
            #Pick the first one that is NOT "0" and is long enough to be a product name
            name = "Unknown Product"
            for h in h1s:
                text = h.text.strip()
                # If text is longer than 3 chars and isn't a digit (like "0"), it's the title
                if len(text) > 3 and not text.isdigit():
                    name = text
                    break

            try:
                price_element = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(@class, 'price') or contains(text(), 'Rs.')]")
                ))
                price_text = price_element.text
                first_price_found = price_text.split('\n')[0]
                clean_price = float(re.sub(r'[^\d.]', '', first_price_found))
            except Exception:
                print(f"⚠️ Price parsing failed for {product_url}")
                return None

            page_content = self.driver.page_source.lower()
            stock_status = "in stock" in page_content and "out of stock" not in page_content

            return {
                "name": name,
                "price": clean_price,
                "vendor": self.vendor_name,
                "is_in_stock": stock_status,
                "url": product_url
            }

        except Exception as e:
            print(f"❌ Selenium Error for {product_url}: {e}")
            return None
        

#Testing section
if __name__ == "__main__":
    test_category = "https://www.nanotek.lk/category/laptop-bags-accessories" 
    
    scraper = NanotekScraper()
    print("\n--- Testing Discovery Mode (Category Scan) ---")
    
    try:
        # 1. Ask scraper to find links
        found_links = scraper.scrape_category(test_category)
        
        print(f"\n✅ Discovery Complete. Found {len(found_links)} products.")
        print("--- First 5 Links Found ---")
        for i, link in enumerate(found_links[:5], 1):
            print(f"   {i}. {link}")

    finally:
        scraper.close_driver()
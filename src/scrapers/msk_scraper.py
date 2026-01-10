from src.scrapers.base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

class MSKScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://mskcomputers.lk", vendor_name="MSK Computers")


    def scrape_category(self, category_url: str) -> list[str]:
        """Scrapes all product URLs from an MSK category page."""
        self.setup_driver()
        if not self.driver: return []

        print(f"🔎 Scanning Category: {category_url}")
        try:
            self._polite_delay()
            self.driver.get(category_url)
            wait = WebDriverWait(self.driver, 15)
            
            #Wait for content
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
            
            #Scroll down to trigger lazy-loaded elements
            self.driver.execute_script("window.scrollTo(0, 1000);")
            time.sleep(3)

            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            product_urls = set()

            for link in all_links:
                href = link.get_attribute("href")
                if not href: continue
                
                # Check if it belongs to MSK
                if self.base_url in href:
                    # CLEANER LOGIC: Path Depth Check
                    #Remove the base URL to get just the path
                    #removes leading/trailing slashes so splitting works correctly
                    path = href.replace(self.base_url, "").strip("/")
                    
                    #Split by '/' to count segments
                    segments = [s for s in path.split('/') if s]
                    
                    # Logic:
                    # - Reject if "categories" is in the path (it's a shelf, not a product)
                    # - Reject if it only has 1 segment (e.g., "e-services", "contact", "cart")
                    # - Accept if it has 2 or more segments (e.g., "web-cam/logitech-c270")
                    if "categories" not in path and len(segments) >= 2:
                        product_urls.add(href)
            
            unique_urls = list(product_urls)
            print(f"   -> Found {len(unique_urls)} products.")
            return unique_urls
            
        except Exception as e:
            print(f"❌ Error scanning category: {e}")
            return []    


    def scrape_product(self, product_url: str) -> dict | None:
        self.setup_driver()
        
        if not self.driver:
            return None
        
        try:
            #Ethical Delay
            self._polite_delay()

            #Use self.driver
            self.driver.get(product_url)
            wait = WebDriverWait(self.driver, 15)
            
            time.sleep(4) 

            #Extract Name
            try:
                name_elem = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "main h1")))
                name = name_elem.text.strip()
            except:
                name = "Unknown Product"

            #Extract Price
            price = None
            price_elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'LKR')]")
            
            for elem in price_elements:
                text = elem.get_attribute("textContent") or ""
                classes = elem.get_attribute("class") or ""
                
                if "SAVE" in text.upper() or "line-through" in classes:
                    continue
                
                clean_price_str = re.sub(r'[^\d.]', '', text)
                if clean_price_str:
                    try:
                        val = float(clean_price_str)
                        if val > 1000: 
                            price = val
                            break
                    except ValueError:
                        continue

            #Extract Stock Status
            is_in_stock = False
            try:
                stock_indicator = self.driver.find_element(By.CSS_SELECTOR, "span.text-green-400")
                if "IN STOCK" in stock_indicator.text.upper():
                    is_in_stock = True
            except:
                try:
                    stock_div = self.driver.find_element(By.XPATH, "//*[contains(text(), 'In Stock')]")
                    if stock_div: is_in_stock = True
                except:
                    pass


            return {
                "name": name,
                "price": price,
                "vendor": self.vendor_name,
                "is_in_stock": is_in_stock,
                "url": product_url
            }

        except Exception as e:
            print(f"❌ MSK Error: {e}")
            return None
        

#Testing block
if __name__ == "__main__":
    test_category = "https://mskcomputers.lk/categories/web-cam"
    
    scraper = MSKScraper()
    print("\n--- Testing MSK Discovery Mode ---")
    
    try:
        found_links = scraper.scrape_category(test_category)
        
        print(f"\n✅ Discovery Complete. Found {len(found_links)} products.")
        print("--- First 5 Links Found ---")
        for i, link in enumerate(found_links[:5], 1):
            print(f"   {i}. {link}")
    finally:
        scraper.close_driver()
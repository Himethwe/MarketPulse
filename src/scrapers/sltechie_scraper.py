from src.scrapers.base_scraper import BaseScraper
from selenium.webdriver.common.by import By
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import re
import time

class SLTechieScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://sltechie.lk", vendor_name="SL Techie")

    def scrape_category(self, category_url: str) -> list[str]:
        """Scrapes all product URLs from an SL Techie category page."""
        self.setup_driver()
        if not self.driver: return []

        print(f"🔎 Scanning Category: {category_url}")
        try:
            self._polite_delay()
            self.driver.get(category_url)
            wait = WebDriverWait(self.driver, 10)
            
            # Wait for any link to appear to confirm page load
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "a")))
            
            all_links = self.driver.find_elements(By.TAG_NAME, "a")
            product_urls = set()

            for link in all_links:
                href = link.get_attribute("href")
                # SL Techie strictly uses /product/ for items
                if href and "/product/" in href:
                    product_urls.add(href)
            
            unique_urls = list(product_urls)
            print(f"   -> Found {len(unique_urls)} products.")
            return unique_urls

        except Exception as e:
            print(f"❌ Error scanning category: {e}")
            return []    

    def scrape_product(self, product_url: str) -> dict | None:
        #Retrieve the shared browser
        self.setup_driver()
        
        if not self.driver:
            return None
        
        try:
            #Ethical Delay
            self._polite_delay()

            #Use self.driver
            self.driver.get(product_url)
            wait = WebDriverWait(self.driver, 20)
            time.sleep(5) 

            #Extract Name
            name = "Unknown Product"
            try:
                name_elem = self.driver.find_element(By.CSS_SELECTOR, "h1.product_title")
                name = name_elem.text.strip()
            except:
                try:
                    h1s = self.driver.find_elements(By.TAG_NAME, "h1")
                    for h in h1s:
                        if len(h.text) > 5:
                            name = h.text.strip()
                            break
                except:
                    pass

            #Extract Price
            price = None
            try:
                all_prices = self.driver.find_elements(By.CSS_SELECTOR, ".woocommerce-Price-amount")
                
                for elem in all_prices:
                    parent_html = elem.find_element(By.XPATH, "..").get_attribute("outerHTML") or ""
                    
                    if "<del" in parent_html or "line-through" in parent_html:
                        continue
                    
                    price_text = elem.get_attribute("textContent") or ""
                    clean_price_str = re.sub(r'[^\d.]', '', price_text)
                    
                    if clean_price_str:
                        val = float(clean_price_str)
                        if val > 1000:
                            price = val
                            break 
            except Exception as e:
                print(f"Price Debug Error: {e}")

            #Extract Stock Status
            is_in_stock = False
            try:
                stock_elem = self.driver.find_element(By.CLASS_NAME, "product-availability")
                if "ONLINE" in stock_elem.text.upper() or "STOCK" in stock_elem.text.upper():
                    is_in_stock = True
            except:
                page_text = self.driver.find_element(By.TAG_NAME, "body").text.upper()
                if "ONLINE EXCLUSIVE" in page_text or "IN STOCK" in page_text:
                    is_in_stock = True

            return {
                "name": name,
                "price": price,
                "vendor": self.vendor_name,
                "is_in_stock": is_in_stock,
                "url": product_url
            }

        except Exception as e:
            print(f"❌ SL Techie Error: {e}")
            return None
        

#Testing block
if __name__ == "__main__":
    test_category = "https://sltechie.lk/product-category/external-storage/"
    
    scraper = SLTechieScraper()
    print("\n--- Testing SL Techie Discovery Mode ---")
    
    try:
        found_links = scraper.scrape_category(test_category)
        
        print(f"\n✅ Discovery Complete. Found {len(found_links)} products.")
        print("--- First 5 Links Found ---")
        for i, link in enumerate(found_links[:5], 1):
            print(f"   {i}. {link}")
    finally:
        scraper.close_driver()
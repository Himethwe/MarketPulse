from src.scrapers.base_scraper import BaseScraper
import re
import logging

class BarclaysScraper(BaseScraper):
    def __init__(self):
        super().__init__(base_url="https://www.barclays.lk", vendor_name="Barclays")


    def scrape_category(self, category_url: str) -> list[str]:
        """Scrapes all product URLs from a Barclays category page."""
        print(f"🔎 Scanning Category: {category_url}")
        
        #use existing fetch page
        soup = self.fetch_page(category_url)
        if not soup: return []

        product_urls = set()
        
        try:
            #get links containing barclays product pattern
            all_links = soup.find_all("a", href=True)

            for link in all_links:
                href = link['href']
                if "itemdesc.asp?ic=" in href:
                    # Handle relative URLs
                    if href.startswith("itemdesc.asp"):
                        full_url = f"{self.base_url}/{href}"
                    # Handle absolute URLs
                    elif href.startswith("http"):
                        full_url = href
                    else:
                        continue
                    
                    product_urls.add(full_url)
            
            unique_urls = list(product_urls)
            print(f"   -> Found {len(unique_urls)} products.")
            return unique_urls

        except Exception as e:
            logging.error(f"❌ Error scanning category: {e}")
            return []    

    def scrape_product(self, product_url: str) -> dict | None:
        # fetch_page auto implement ethical delay
        soup = self.fetch_page(product_url)
        if not soup:
            return None

        try:
            #Get Name
            name_tag = soup.find("div", class_="product-name") or soup.find("h1")
            name = name_tag.get_text(strip=True) if name_tag else "Unknown Product"

            #Get Price
            price = None
            price_tag = soup.select_one(".price-box .price")
            
            if price_tag:
                price_text = price_tag.get_text(strip=True)
                clean_text = price_text.split('\xa0')[0].split(' ')[0]
                clean_price_str = re.sub(r'[^\d.]', '', clean_text)
                
                if clean_price_str:
                    val = float(clean_price_str)
                    if val > 1000:
                        price = val

            #Get Stock Status
            page_text = soup.get_text().lower()
            is_in_stock = "availability: yes" in page_text or "in stock" in page_text

            return {
                "name": name,
                "price": price,
                "vendor": self.vendor_name,
                "is_in_stock": is_in_stock,
                "url": product_url
            }

        except Exception as e:
            logging.error(f"❌ Error parsing Barclays page: {e}")
            return None

#Testing block
if __name__ == "__main__":
    test_category = "https://www.barclays.lk/items.asp?Tp=&iTpStatus=1&Cc=50&CatName=Canon%20Printers"
    
    scraper = BarclaysScraper()
    print("\n--- Testing Barclays Discovery Mode ---")
    
    #Scan the category
    found_links = scraper.scrape_category(test_category)
    
    #Show results
    print(f"\n✅ Discovery Complete. Found {len(found_links)} products.")
    print("--- First 5 Links Found ---")
    for i, link in enumerate(found_links[:5], 1):
        print(f"   {i}. {link}")
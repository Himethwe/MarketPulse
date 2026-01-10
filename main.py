import yaml
from urllib.parse import urlparse
from src.database.db_manager import DatabaseManager
from src.scrapers.nanotek_scraper import NanotekScraper
from src.scrapers.barclays_scraper import BarclaysScraper
from src.scrapers.msk_scraper import MSKScraper
from src.scrapers.sltechie_scraper import SLTechieScraper

#the pages we want to scrape
TARGET_CATEGORIES = [
    #Nanotek
    "https://www.nanotek.lk/category/laptop",
    "https://www.nanotek.lk/category/laptop?page=2",
    "https://www.nanotek.lk/category/laptop?page=3",
    "https://www.nanotek.lk/category/laptop?page=4",
    "https://www.nanotek.lk/category/laptop?page=5",

    #Barclays
    "https://www.barclays.lk/items.asp?Tp=&iTpStatus=1&Cc=257&CatName=Laptop%20/%20Notebook",
    "https://www.barclays.lk/items.asp?Cc=257&ItemMoveby=0&Nbm=LAPA8028&Pbm=LAPA8780&iTpStatus=1&Tp=&sTitle=&FromNav=False",
    "https://www.barclays.lk/items.asp?Cc=257&ItemMoveby=0&Nbm=LAPA6787&Pbm=LAPA0229&iTpStatus=1&Tp=&sTitle=&FromNav=False",
    "https://www.barclays.lk/items.asp?Cc=257&ItemMoveby=0&Nbm=LAPA6333&Pbm=LAPA0011&iTpStatus=1&Tp=&sTitle=&FromNav=False",
    "https://www.barclays.lk/items.asp?Cc=257&ItemMoveby=0&Nbm=LAPA9735&Pbm=LAPDHPO8&iTpStatus=1&Tp=&sTitle=&FromNav=False",

    #Msk_Computers
    "https://www.mskcomputers.lk/categories/brand-new-laptop",
    "https://www.mskcomputers.lk/categories/brand-new-laptop?page=2",
    "https://mskcomputers.lk/categories/brand-new-laptop?page=3",

    #SL_Techie
    "https://sltechie.lk/product-category/laptops/",
    "https://sltechie.lk/product-category/laptops/page/2/",
]

#read markets.yaml to understand the sources
def load_markets():
    try:
        with open("config/markets.yaml", "r") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"⚠️ Warning: Could not load markets.yaml: {e}")
        return {}

#return correct scraper based on url
def get_scraper_for_url(url):
    domain = urlparse(url).netloc.lower()
    
    if "nanotek.lk" in domain:
        return NanotekScraper()
    elif "barclays.lk" in domain:
        return BarclaysScraper()
    elif "mskcomputers.lk" in domain:
        return MSKScraper()
    elif "sltechie.lk" in domain:
        return SLTechieScraper()
    else:
        return None

#sorts url by vendor
#scrapes data
#save to database
def run_pipeline(url_list):
    db = DatabaseManager()
    
    #group urls by vendor
    batches = {}
    
    print("--- 1. Organizing Batch ---")
    for url in url_list:
        scraper = get_scraper_for_url(url)
        if scraper:
            scraper_name = scraper.__class__.__name__
            if scraper_name not in batches:
                batches[scraper_name] = {
                    "instance": scraper,
                    "urls": []
                }
            batches[scraper_name]["urls"].append(url)
        else:
            print(f"⚠️ No scraper found for: {url}")

    #Process each vendor batch
    print(f"--- 2. Starting Execution ({len(batches)} Vendors Found) ---")
    
    for scraper_name, batch_data in batches.items():
        scraper = batch_data["instance"]
        urls = batch_data["urls"]
        
        print(f"\n🔵 Starting {scraper_name} ({len(urls)} items)...")
        
        try: 
            # the scraper classes handle self.setup_driver() internally now.
            
            for i, link in enumerate(urls, 1):
                print(f"   ({i}/{len(urls)}) Scraping: {link}")
                
                #SCRAPE
                data = scraper.scrape_product(link)
                
                #SAVE
                if data:
                    db.save_scraped_data(data)
                else:
                    print(f"   ❌ Failed to scrape data.")
                    
        finally:
            #Close the browser after the batch is done
            if hasattr(scraper, 'close_driver'):
                scraper.close_driver()
                
    print("\n✅ Pipeline Finished.")
    db.close()

#visit category pages
#find link
#scrape and save
def run_harvest_pipeline():
    db = DatabaseManager()
    
    print(f"🚀 Starting MarketPulse Harvest on {len(TARGET_CATEGORIES)} Categories...")

    for category_url in TARGET_CATEGORIES:
        print(f"\n------------------------------------------------")
        print(f"📂 Processing Category: {category_url}")
        
        #Identify Vendor
        scraper = get_scraper_for_url(category_url)
        if not scraper:
            print(f"⚠️ No scraper found for this URL. Skipping.")
            continue

        #DISCOVERY PHASE
        try:
            product_links = scraper.scrape_category(category_url)
            print(f"   -> Found {len(product_links)} products to scrape.")
        except Exception as e:
            print(f"❌ Discovery Failed: {e}")
            if hasattr(scraper, 'close_driver'): scraper.close_driver()
            continue

        #EXTRACTION PHASE
        for i, link in enumerate(product_links, 1): 
            print(f"   PLEASE WAIT... Scraping Item {i}/{len(product_links)}: {link}")
            
            try:
                data = scraper.scrape_product(link)
                if data:
                    db.save_scraped_data(data)
                else:
                    print(f"      ❌ Failed to extract data.")
            except Exception as e:
                print(f"      ❌ Error: {e}")
        
        # Close driver after finishing the category
        if hasattr(scraper, 'close_driver'):
            scraper.close_driver()
            
    print("\n✅ Harvest Complete. Data saved to Database.")
    db.close()    

if __name__ == "__main__":
    run_harvest_pipeline()

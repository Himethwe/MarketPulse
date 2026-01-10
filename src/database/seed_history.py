import random
from datetime import datetime, timedelta
import psycopg2
from src.database.db_manager import DatabaseManager

class HistorySeeder:
    def __init__(self):
        self.db = DatabaseManager()

    def generate_history(self):
        print("⏳ Starting Time Machine... Generating 30 days of history.")
        
        conn = self.db.get_connection()
        cur = conn.cursor()

        # 1. Get all current products
        cur.execute("""
            SELECT DISTINCT ON (product_id, vendor_name) 
                product_id, vendor_name, price, product_url
            FROM market_data
            ORDER BY product_id, vendor_name, scraped_at DESC
        """)
        products = cur.fetchall()
        
        print(f"   Found {len(products)} products to backfill.")

        new_records = 0

        #Loop through each product and create history
        for prod in products:
            p_id, vendor, raw_price, url = prod
            
            current_price = float(raw_price) 
            
            #for 30 days
            for days_ago in range(1, 31):
                date_point = datetime.now() - timedelta(days=days_ago)
                
                change_type = random.choice(['same', 'small_change', 'drop'])
                
                historical_price = current_price
                
                if change_type == 'small_change':
                    percent = random.uniform(0.97, 1.03)
                    historical_price = current_price * percent
                elif change_type == 'drop':
                    historical_price = current_price * 1.05 
                
                historical_price = round(historical_price / 100) * 100

                #insert into database
                try:
                    cur.execute("""
                        INSERT INTO market_data (product_id, vendor_name, price, is_in_stock, product_url, scraped_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        ON CONFLICT (product_id, vendor_name, scraped_at) DO NOTHING
                    """, (p_id, vendor, historical_price, True, url, date_point))
                    new_records += 1
                except Exception as e:
                    print(f"Error: {e}")

        conn.commit()
        conn.close()
        print(f"✅ Time Machine Success! Added {new_records} historical records.")

if __name__ == "__main__":
    seeder = HistorySeeder()
    seeder.generate_history()
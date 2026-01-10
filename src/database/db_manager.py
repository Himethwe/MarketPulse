import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.dbname = os.getenv("DB_NAME", "marketpulse")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD")
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = os.getenv("DB_PORT", "5433") 
        self.conn = None

    #returns raw database connection
    def get_connection(self):
        return psycopg2.connect(
            host=self.host,
            database=self.dbname,
            user=self.user,
            password=self.password,
            port=self.port
        )    

    #connect to database
    def connect(self):
        try:
            if self.conn and not self.conn.closed:
                return self.conn

            self.conn = psycopg2.connect(
                dbname=self.dbname,
                user=self.user,
                password=self.password,
                host=self.host,
                port=self.port
            )
            return self.conn
        except Exception as e:
            print(f"❌ Database Connection Error: {e}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

    #takes scraper data and save to database
    def save_scraped_data(self, data: dict):
        if not data or not data.get('price'):
            return

        conn = self.connect()
        if not conn: return

        try:
            with conn.cursor() as cur:
                scraped_name = data['name'].strip()
                vendor = data['vendor']
                
                cur.execute("""
                    SELECT internal_product_id FROM product_mappings 
                    WHERE external_name_variant = %s AND vendor_name = %s
                """, (scraped_name, vendor))
                
                result = cur.fetchone()

                if result:
                    #A: known product
                    product_id = result[0]
                else:
                    #B: new product
                    #create new entry in products table
                    cur.execute("""
                        INSERT INTO products (name, category, created_at)
                        VALUES (%s, 'Uncategorized', NOW())
                        RETURNING id
                    """, (scraped_name,))
                    
                    new_row = cur.fetchone()
                    if new_row:
                        product_id = new_row[0]
                    else:
                        print(f"❌ Error: Database did not return an ID for {scraped_name}")
                        return 


                    #link to 'product_mappings'
                    cur.execute("""
                        INSERT INTO product_mappings (internal_product_id, external_name_variant, vendor_name)
                        VALUES (%s, %s, %s)
                    """, (product_id, scraped_name, vendor))
                    
                    print(f"🆕 New Product Registered: {scraped_name}")

                #input price history
                cur.execute("""
                    INSERT INTO market_data (product_id, vendor_name, price, is_in_stock, product_url, scraped_at)
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (product_id, vendor_name, scraped_at) DO NOTHING
                """, (product_id, vendor, data['price'], data['is_in_stock'], data['url']))

            conn.commit()
            print(f"✅ Saved: {data['name']} | Rs. {data['price']}")

        except Exception as e:
            conn.rollback()
            print(f"❌ Error Saving Data: {e}")

# Self-test block
if __name__ == "__main__":
    db = DatabaseManager()
    # Simulate a fake scraped item to test the logic
    fake_item = {
        "name": "Test Laptop M3",
        "price": 250000.0,
        "vendor": "TestVendor",
        "is_in_stock": True,
        "url": "http://test.com"
    }
    print("--- Testing Database Logic ---")
    db.save_scraped_data(fake_item)
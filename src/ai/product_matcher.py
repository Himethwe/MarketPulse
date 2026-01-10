import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from src.database.db_manager import DatabaseManager

#get suitable model for laptop names
class ProductMatcher:
    def __init__(self, model_name='all-MiniLM-L6-v2'):
        print("🧠 Loading AI Model... (This happens only once)")
        self.model = SentenceTransformer(model_name)
        self.db = DatabaseManager()

    #get raw product names from mapping table
    def fetch_data(self):
        conn = self.db.get_connection()
        
        query = """
            SELECT 
                internal_product_id, 
                external_name_variant AS name, 
                vendor_name AS vendor 
            FROM product_mappings
        """
        
        try:
            df = pd.read_sql(query, conn)
        except Exception as e:
            print(f"❌ SQL Error: {e}")
            df = pd.DataFrame() # Return empty if fail
        finally:
            conn.close()
            
        return df

    #updates database by linking products with same id
    def link_products(self, primary_id, secondary_id):
        if primary_id == secondary_id:
            return

        conn = self.db.get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE product_mappings
                    SET internal_product_id = %s
                    WHERE internal_product_id = %s
                """, (int(primary_id), int(secondary_id)))
            conn.commit()
            print(f"   └── 💾 MERGED: Product ID {secondary_id} is now linked to ID {primary_id}")
        except Exception as e:
            print(f"❌ Database Update Error: {e}")
        finally:
            conn.close()

    #Core AI logic
    def find_matches(self):
        df = self.fetch_data()
        
        if df.empty:
            print("❌ No data found in database!")
            return

        print(f"📊 Analyzing {len(df)} products...")

        #embeddings
        raw_embeddings = self.model.encode(df['name'].tolist(), convert_to_numpy=True)
        embeddings = np.array(raw_embeddings)

        #calculate similarity
        #compare every product against every other product
        similarity_matrix = cosine_similarity(embeddings)

        #identify matches
        threshold = 0.85  # 85% similarity score
        
        matches_found = []

        for i in range(len(df)):
            for j in range(i + 1, len(df)): # Avoid duplicate pairs
                score = similarity_matrix[i][j]
                
                if score > threshold:
                    prod_a = df.iloc[i]
                    prod_b = df.iloc[j]
                    
                    # Only use when from different vendors
                    if prod_a['vendor'] != prod_b['vendor']:
                        
                        self.link_products(prod_a['internal_product_id'], prod_b['internal_product_id'])

                        matches_found.append({
                            "Product A": f"{prod_a['name']} ({prod_a['vendor']})",
                            "Product B": f"{prod_b['name']} ({prod_b['vendor']})",
                            "Score": f"{score:.2f}"
                        })

        #get results
        print(f"\n✅ Analysis Complete. Found {len(matches_found)} matches.\n")
        for match in matches_found[:10]: #top 10
            print(f"🔗 MATCH FOUND (Confidence: {match['Score']})")
            print(f"   A: {match['Product A']}")
            print(f"   B: {match['Product B']}")
            print("-" * 50)

if __name__ == "__main__":
    matcher = ProductMatcher()
    matcher.find_matches()
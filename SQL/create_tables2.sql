--Master Product List
--stores unique items
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    brand VARCHAR(100),
    category VARCHAR(100),
    model_sku VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

--Market data
--stores daily scraped prices and stock status
CREATE TABLE market_data (
    id SERIAL PRIMARY KEY,
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    vendor_name VARCHAR(100) NOT NULL,
    price DECIMAL(12, 2) NOT NULL,
    currency VARCHAR(10) DEFAULT 'LKR',
    is_in_stock BOOLEAN DEFAULT TRUE,
    product_url TEXT,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(product_id, vendor_name, scraped_at)
);

--AI Mapping Layer
--link product names from different stores with the master product list
CREATE TABLE product_mappings (
    id SERIAL PRIMARY KEY,
    internal_product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
    external_name_variant TEXT NOT NULL,
    vendor_name VARCHAR(100)
);

--Speed up price history search
CREATE INDEX idx_vendor_date ON market_data(vendor_name, scraped_at);

--Verify created tables
SELECT * FROM products
SELECT * FROM market_data
SELECT * FROM product_mappings
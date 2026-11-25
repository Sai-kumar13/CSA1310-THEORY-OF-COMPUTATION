-- ============================================================
-- ADAPTIVE E-COMMERCE SEARCH AND PERSONALIZED RECOMMENDATION
-- Database Setup Script
-- ============================================================

-- Create database
CREATE DATABASE IF NOT EXISTS adaptive_ecommerce_db;
USE adaptive_ecommerce_db;

-- ============================================================
-- TABLE: categories
-- ============================================================
DROP TABLE IF EXISTS user_preferences;
DROP TABLE IF EXISTS user_activity;
DROP TABLE IF EXISTS search_history;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(100) NOT NULL UNIQUE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: products
-- ============================================================
CREATE TABLE products (
    product_id INT AUTO_INCREMENT PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL,
    description TEXT,
    category VARCHAR(100) NOT NULL,
    brand VARCHAR(100),
    price DECIMAL(10, 2) NOT NULL,
    rating DECIMAL(2, 1) DEFAULT 0.0,
    image_url VARCHAR(500) DEFAULT '',
    stock_quantity INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (category) REFERENCES categories(category_name)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: search_history
-- ============================================================
CREATE TABLE search_history (
    search_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    search_query VARCHAR(255) NOT NULL,
    searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: user_activity
-- ============================================================
CREATE TABLE user_activity (
    activity_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    product_id INT NOT NULL,
    activity_type VARCHAR(50) NOT NULL,
    activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: user_preferences
-- ============================================================
CREATE TABLE user_preferences (
    preference_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    category VARCHAR(100) NOT NULL,
    preference_score DECIMAL(5, 2) DEFAULT 0.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_category (user_id, category),
    FOREIGN KEY (category) REFERENCES categories(category_name)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: product_comparisons
-- ============================================================
CREATE TABLE IF NOT EXISTS product_comparisons (
    comparison_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    product_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_compare (user_id, product_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: wishlists
-- ============================================================
CREATE TABLE IF NOT EXISTS wishlists (
    wishlist_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    product_id INT NOT NULL,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_wishlist (user_id, product_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- TABLE: price_alerts
-- ============================================================
CREATE TABLE IF NOT EXISTS price_alerts (
    alert_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL DEFAULT 1,
    product_id INT NOT NULL,
    target_price DECIMAL(10, 2) NOT NULL,
    alert_status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    triggered_at TIMESTAMP NULL,
    UNIQUE KEY unique_user_alert (user_id, product_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

-- ============================================================
-- INSERT CATEGORIES
-- ============================================================
INSERT INTO categories (category_name) VALUES
    ('Smartphones'),
    ('Laptops'),
    ('Headphones'),
    ('Smartwatches'),
    ('Clothing'),
    ('Shoes'),
    ('Home Appliances'),
    ('Accessories');

-- ============================================================
-- INSERT PRODUCTS (34 realistic products with Indian INR pricing)
-- ============================================================

-- ---- Smartphones (5) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('iPhone 15 Pro', 'Apple iPhone 15 Pro with A17 Pro chip, 48MP camera system, titanium design, and USB-C connectivity. Features Dynamic Island and always-on display.', 'Smartphones', 'Apple', 129900.00, 4.8, '/static/images/products/product_1.jpg', 50),
('Samsung Galaxy S24 Ultra', 'Samsung Galaxy S24 Ultra with Snapdragon 8 Gen 3, 200MP camera, S Pen, titanium frame, and Galaxy AI features built in.', 'Smartphones', 'Samsung', 129999.00, 4.7, '/static/images/products/product_2.jpg', 45),
('Google Pixel 8 Pro', 'Google Pixel 8 Pro with Tensor G3, advanced AI photo editing, 7 years of OS updates, and best-in-class computational photography.', 'Smartphones', 'Google', 89999.00, 4.6, '/static/images/products/product_3.jpg', 40),
('OnePlus 12', 'OnePlus 12 flagship with Snapdragon 8 Gen 3, Hasselblad camera system, 100W SUPERVOOC charging, and 2K 120Hz ProXDR display.', 'Smartphones', 'OnePlus', 64999.00, 4.5, '/static/images/products/product_4.jpg', 35),
('Xiaomi 14 Pro', 'Xiaomi 14 Pro with Leica optics, Snapdragon 8 Gen 3, 120W HyperCharge, and stunning LTPO AMOLED display.', 'Smartphones', 'Xiaomi', 59999.00, 4.3, '/static/images/products/product_5.jpg', 30);

-- ---- Laptops (5) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('MacBook Air M3', 'Apple MacBook Air with M3 chip, 15.3-inch Liquid Retina display, 18-hour battery life, fanless design, and 8-core GPU.', 'Laptops', 'Apple', 114900.00, 4.9, '/static/images/products/product_6.jpg', 25),
('Dell XPS 15', 'Dell XPS 15 with 13th Gen Intel Core i7, NVIDIA RTX 4060, 15.6-inch OLED display, and InfinityEdge bezels.', 'Laptops', 'Dell', 149999.00, 4.7, '/static/images/products/product_7.jpg', 20),
('HP Spectre x360', 'HP Spectre x360 2-in-1 convertible with Intel Core Ultra, 14-inch 2.8K OLED touchscreen, stylus support, and gem-cut design.', 'Laptops', 'HP', 134999.00, 4.6, '/static/images/products/product_8.jpg', 18),
('Lenovo ThinkPad X1 Carbon', 'Lenovo ThinkPad X1 Carbon Gen 11 with Intel vPro, 14-inch 2.8K OLED, legendary keyboard, and military-grade durability.', 'Laptops', 'Lenovo', 159999.00, 4.8, '/static/images/products/product_9.jpg', 15),
('ASUS ROG Zephyrus G16', 'ASUS ROG Zephyrus G16 gaming laptop with Intel Core i9, NVIDIA RTX 4090, 16-inch 240Hz display, and ROG Nebula HDR screen.', 'Laptops', 'ASUS', 219999.00, 4.5, '/static/images/products/product_10.jpg', 12);

-- ---- Headphones (4) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('Sony WH-1000XM5', 'Sony WH-1000XM5 wireless noise-cancelling headphones with 30-hour battery, multipoint connection, and industry-leading ANC.', 'Headphones', 'Sony', 29990.00, 4.8, '/static/images/products/product_11.jpg', 60),
('Apple AirPods Max', 'Apple AirPods Max over-ear headphones with H2 chip, adaptive transparency, personalized spatial audio, and USB-C.', 'Headphones', 'Apple', 59900.00, 4.7, '/static/images/products/product_12.jpg', 30),
('Bose QuietComfort Ultra', 'Bose QuietComfort Ultra headphones with CustomTune sound, immersive spatial audio, world-class noise cancellation.', 'Headphones', 'Bose', 35900.00, 4.6, '/static/images/products/product_13.jpg', 40),
('JBL Tune 770NC', 'JBL Tune 770NC wireless headphones with adaptive noise cancelling, JBL Pure Bass, 44-hour battery, and lightweight comfort.', 'Headphones', 'JBL', 6499.00, 4.3, '/static/images/products/product_14.jpg', 70);

-- ---- Smartwatches (4) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('Apple Watch Ultra 2', 'Apple Watch Ultra 2 with S9 chip, precision dual-frequency GPS, 36-hour battery, 3000 nits brightness, and rugged titanium case.', 'Smartwatches', 'Apple', 89900.00, 4.8, '/static/images/products/product_15.jpg', 25),
('Samsung Galaxy Watch 6 Classic', 'Samsung Galaxy Watch 6 Classic with rotating bezel, BioActive sensor, Wear OS, sleep coaching, and sapphire crystal.', 'Smartwatches', 'Samsung', 36999.00, 4.5, '/static/images/products/product_16.jpg', 35),
('Garmin Venu 3', 'Garmin Venu 3 GPS smartwatch with AMOLED display, Body Battery energy monitoring, advanced sleep analysis, and 14-day battery.', 'Smartwatches', 'Garmin', 44990.00, 4.6, '/static/images/products/product_17.jpg', 20),
('Fitbit Sense 2', 'Fitbit Sense 2 health smartwatch with stress management, ECG app, skin temperature sensor, and 6+ day battery life.', 'Smartwatches', 'Fitbit', 19999.00, 4.4, '/static/images/products/product_18.jpg', 40);

-- ---- Clothing (4) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('Nike Dri-FIT Running T-Shirt', 'Nike Dri-FIT moisture-wicking running t-shirt with breathable mesh panels and reflective elements for visibility.', 'Clothing', 'Nike', 1995.00, 4.4, '/static/images/products/product_19.jpg', 100),
('Levi''s 501 Original Jeans', 'Levi''s 501 Original Fit jeans with button fly, iconic straight-leg silhouette, and 100% cotton denim construction.', 'Clothing', 'Levis', 3999.00, 4.5, '/static/images/products/product_20.jpg', 80),
('Adidas Essentials Track Jacket', 'Adidas Essentials 3-Stripes track jacket with recycled materials, full-zip front, and ribbed cuffs and hem.', 'Clothing', 'Adidas', 4299.00, 4.3, '/static/images/products/product_21.jpg', 60),
('Under Armour Storm Hoodie', 'Under Armour Storm Fleece hoodie with water-repellent finish, Armour Fleece fabric, and front kangaroo pocket.', 'Clothing', 'Under Armour', 3499.00, 4.2, '/static/images/products/product_22.jpg', 70);

-- ---- Shoes (4) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('Nike Air Max 270', 'Nike Air Max 270 with the largest Max Air unit yet, mesh upper for breathability, foam midsole, and iconic heel design.', 'Shoes', 'Nike', 13995.00, 4.6, '/static/images/products/product_23.jpg', 55),
('Adidas Ultraboost Light', 'Adidas Ultraboost Light running shoes with LIGHT BOOST midsole, Primeknit+ upper, Continental rubber outsole.', 'Shoes', 'Adidas', 17999.00, 4.7, '/static/images/products/product_24.jpg', 45),
('Puma RS-X Reinvention', 'Puma RS-X Reinvention sneakers with Running System technology, chunky silhouette, mesh and leather upper.', 'Shoes', 'Puma', 8999.00, 4.3, '/static/images/products/product_25.jpg', 50),
('New Balance 574 Core', 'New Balance 574 Core classic lifestyle sneakers with ENCAP midsole technology, suede/mesh upper, and heritage design.', 'Shoes', 'New Balance', 7499.00, 4.4, '/static/images/products/product_26.jpg', 65);

-- ---- Home Appliances (4) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('Dyson V15 Detect Vacuum', 'Dyson V15 Detect cordless vacuum with laser dust detection, piezo sensor, LCD screen showing particle count, and 60-min runtime.', 'Home Appliances', 'Dyson', 62900.00, 4.7, '/static/images/products/product_27.jpg', 20),
('Instant Pot Duo Plus 9-in-1', 'Instant Pot Duo Plus 9-in-1 electric pressure cooker with whisper-quiet steam release, stainless steel inner pot, and 15 programs.', 'Home Appliances', 'Instant Pot', 10999.00, 4.6, '/static/images/products/product_28.jpg', 40),
('Philips Premium Air Fryer XXL', 'Philips Premium Air Fryer XXL with Fat Removal technology, rapid air, digital display, and 3 lb / 7 qt capacity.', 'Home Appliances', 'Philips', 18995.00, 4.5, '/static/images/products/product_29.jpg', 30),
('iRobot Roomba j7+', 'iRobot Roomba j7+ self-emptying robot vacuum with PrecisionVision navigation, obstacle avoidance, and smart mapping.', 'Home Appliances', 'iRobot', 54900.00, 4.4, '/static/images/products/product_30.jpg', 22);

-- ---- Accessories (4) ----
INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity) VALUES
('Anker PowerCore 26800mAh', 'Anker PowerCore 26800 portable charger with PowerIQ, dual USB ports, 26800mAh capacity for multiple full phone charges.', 'Accessories', 'Anker', 4999.00, 4.5, '/static/images/products/product_31.jpg', 80),
('Logitech MX Master 3S', 'Logitech MX Master 3S wireless mouse with 8K DPI tracking, MagSpeed scroll, quiet clicks, and USB-C charging.', 'Accessories', 'Logitech', 8995.00, 4.7, '/static/images/products/product_32.jpg', 50),
('Samsung T7 Shield 1TB SSD', 'Samsung T7 Shield portable SSD with 1050 MB/s read speed, IP65 dust/water resistance, and USB 3.2 Gen 2 interface.', 'Accessories', 'Samsung', 9499.00, 4.6, '/static/images/products/product_33.jpg', 40),
('Belkin 3-in-1 Wireless Charger', 'Belkin BoostCharge Pro 3-in-1 wireless charging pad for iPhone, Apple Watch, and AirPods with MagSafe alignment.', 'Accessories', 'Belkin', 11999.00, 4.4, '/static/images/products/product_34.jpg', 35);

-- ============================================================
-- Initialize default user preferences (empty - will be populated by user activity)
-- ============================================================
INSERT INTO user_preferences (user_id, category, preference_score) VALUES
    (1, 'Smartphones', 0.0),
    (1, 'Laptops', 0.0),
    (1, 'Headphones', 0.0),
    (1, 'Smartwatches', 0.0),
    (1, 'Clothing', 0.0),
    (1, 'Shoes', 0.0),
    (1, 'Home Appliances', 0.0),
    (1, 'Accessories', 0.0);

-- ============================================================
-- Done! Database ready.
-- ============================================================
SELECT 'Database adaptive_ecommerce_db created successfully!' AS status;
SELECT CONCAT(COUNT(*), ' products inserted.') AS products_count FROM products;
SELECT CONCAT(COUNT(*), ' categories inserted.') AS categories_count FROM categories;

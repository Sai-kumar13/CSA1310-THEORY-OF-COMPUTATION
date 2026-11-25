"""
Database Connection Manager
===========================
Provides unified connectivity to MySQL (primary) with automatic fallback
to SQLite when the MySQL service is offline or unreachable.

Guarantees 100% real database operations, persistent history,
and live recommendations in any development environment.
"""

import os
import sqlite3
import mysql.connector


class DatabaseConnection:
    """Wrapper that normalizes MySQL and SQLite connections."""

    def __init__(self, raw_conn, is_sqlite=False):
        self.raw_conn = raw_conn
        self.is_sqlite = is_sqlite

    def cursor(self, dictionary=True):
        if self.is_sqlite:
            self.raw_conn.row_factory = sqlite3.Row if dictionary else None
            return SQLiteCursorWrapper(self.raw_conn.cursor())
        else:
            return self.raw_conn.cursor(dictionary=dictionary)

    def commit(self):
        self.raw_conn.commit()

    def rollback(self):
        self.raw_conn.rollback()

    def close(self):
        self.raw_conn.close()


class SQLiteCursorWrapper:
    """Wraps SQLite cursor to accept %s placeholders and return dict rows."""

    def __init__(self, raw_cursor):
        self.raw_cursor = raw_cursor

    def execute(self, query, params=None):
        # Convert MySQL %s placeholder to SQLite ?
        converted_query = query.replace('%s', '?')
        # Handle MySQL ON DUPLICATE KEY UPDATE in SQLite
        if 'ON DUPLICATE KEY UPDATE' in converted_query:
            # Convert:
            # INSERT INTO user_preferences (user_id, category, preference_score) VALUES (?, ?, 1.0)
            # ON DUPLICATE KEY UPDATE preference_score = preference_score + 1.0
            converted_query = converted_query.replace(
                'ON DUPLICATE KEY UPDATE',
                'ON CONFLICT(user_id, category) DO UPDATE SET'
            )

        if params is not None:
            return self.raw_cursor.execute(converted_query, params)
        return self.raw_cursor.execute(converted_query)

    def fetchone(self):
        row = self.raw_cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def fetchall(self):
        rows = self.raw_cursor.fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.raw_cursor.close()


class DatabaseManager:
    """Manages database connection and handles auto-seeding."""

    _sqlite_initialized = False
    _mysql_available = None

    @classmethod
    def get_connection(cls, db_config):
        """
        Attempts MySQL connection first.
        If MySQL is unavailable, falls back to SQLite.
        """
        if cls._mysql_available is not False:
            try:
                conn = mysql.connector.connect(
                    host=db_config['host'],
                    user=db_config['user'],
                    password=db_config.get('password', ''),
                    database=db_config['database'],
                    port=db_config.get('port', 3306),
                    connect_timeout=1
                )
                cls._mysql_available = True
                return DatabaseConnection(conn, is_sqlite=False)
            except Exception:
                cls._mysql_available = False

        # Fall back to SQLite
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'adaptive_ecommerce.db')
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
        wrapper = DatabaseConnection(conn, is_sqlite=True)

        if not cls._sqlite_initialized:
            cls._init_sqlite(wrapper)
            cls._sqlite_initialized = True

        return wrapper

    @classmethod
    def _init_sqlite(cls, db_conn):
        """Initializes SQLite schema and 34 sample products if tables don't exist."""
        cur = db_conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                category_id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT NOT NULL UNIQUE
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT NOT NULL,
                description TEXT,
                category TEXT NOT NULL,
                brand TEXT,
                price REAL NOT NULL,
                rating REAL DEFAULT 0.0,
                image_url TEXT DEFAULT '',
                stock_quantity INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (category) REFERENCES categories(category_name)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                search_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                search_query TEXT NOT NULL,
                searched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_activity (
                activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                product_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                activity_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                preference_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                category TEXT NOT NULL,
                preference_score REAL DEFAULT 0.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (user_id, category)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS product_comparisons (
                comparison_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                product_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS wishlists (
                wishlist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                product_id INTEGER NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS price_alerts (
                alert_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL DEFAULT 1,
                product_id INTEGER NOT NULL,
                target_price REAL NOT NULL,
                alert_status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                UNIQUE(user_id, product_id),
                FOREIGN KEY (product_id) REFERENCES products(product_id)
            );
        """)

        db_conn.commit()

        # Check if products exist
        cur.execute("SELECT COUNT(*) as cnt FROM products")
        res = cur.fetchone()
        if res and res['cnt'] > 0:
            cur.close()
            return

        # Insert categories
        categories = [
            'Smartphones', 'Laptops', 'Headphones', 'Smartwatches',
            'Clothing', 'Shoes', 'Home Appliances', 'Accessories'
        ]
        for cat in categories:
            cur.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (%s)", (cat,))

        # Insert 34 Sample Products with Indian INR pricing
        sample_products = [
            # Smartphones (5)
            ('iPhone 15 Pro', 'Apple iPhone 15 Pro with A17 Pro chip, 48MP camera system, titanium design, and USB-C connectivity.', 'Smartphones', 'Apple', 129900.00, 4.8, '/static/images/products/product_1.jpg', 50),
            ('Samsung Galaxy S24 Ultra', 'Samsung Galaxy S24 Ultra with Snapdragon 8 Gen 3, 200MP camera, S Pen, titanium frame, and Galaxy AI.', 'Smartphones', 'Samsung', 129999.00, 4.7, '/static/images/products/product_2.jpg', 45),
            ('Google Pixel 8 Pro', 'Google Pixel 8 Pro with Tensor G3, advanced AI photo editing, and 7 years of OS updates.', 'Smartphones', 'Google', 89999.00, 4.6, '/static/images/products/product_3.jpg', 40),
            ('OnePlus 12', 'OnePlus 12 flagship with Snapdragon 8 Gen 3, Hasselblad camera system, and 100W SUPERVOOC charging.', 'Smartphones', 'OnePlus', 64999.00, 4.5, '/static/images/products/product_4.jpg', 35),
            ('Xiaomi 14 Pro', 'Xiaomi 14 Pro with Leica optics, Snapdragon 8 Gen 3, and 120W HyperCharge.', 'Smartphones', 'Xiaomi', 59999.00, 4.3, '/static/images/products/product_5.jpg', 30),

            # Laptops (5)
            ('MacBook Air M3', 'Apple MacBook Air with M3 chip, 15.3-inch Liquid Retina display, 18-hour battery life.', 'Laptops', 'Apple', 114900.00, 4.9, '/static/images/products/product_6.jpg', 25),
            ('Dell XPS 15', 'Dell XPS 15 with 13th Gen Intel Core i7, NVIDIA RTX 4060, 15.6-inch OLED display.', 'Laptops', 'Dell', 149999.00, 4.7, '/static/images/products/product_7.jpg', 20),
            ('HP Spectre x360', 'HP Spectre x360 2-in-1 convertible with Intel Core Ultra, 14-inch 2.8K OLED touchscreen.', 'Laptops', 'HP', 134999.00, 4.6, '/static/images/products/product_8.jpg', 18),
            ('Lenovo ThinkPad X1 Carbon', 'Lenovo ThinkPad X1 Carbon Gen 11 with Intel vPro, legendary keyboard, and durability.', 'Laptops', 'Lenovo', 159999.00, 4.8, '/static/images/products/product_9.jpg', 15),
            ('ASUS ROG Zephyrus G16', 'ASUS ROG Zephyrus G16 gaming laptop with Intel Core i9, NVIDIA RTX 4090, 240Hz display.', 'Laptops', 'ASUS', 219999.00, 4.5, '/static/images/products/product_10.jpg', 12),

            # Headphones (4)
            ('Sony WH-1000XM5', 'Sony WH-1000XM5 wireless noise-cancelling headphones with 30-hour battery, industry-leading ANC.', 'Headphones', 'Sony', 29990.00, 4.8, '/static/images/products/product_11.jpg', 60),
            ('Apple AirPods Max', 'Apple AirPods Max over-ear headphones with H2 chip, personalized spatial audio, and USB-C.', 'Headphones', 'Apple', 59900.00, 4.7, '/static/images/products/product_12.jpg', 30),
            ('Bose QuietComfort Ultra', 'Bose QuietComfort Ultra headphones with CustomTune sound and world-class noise cancellation.', 'Headphones', 'Bose', 35900.00, 4.6, '/static/images/products/product_13.jpg', 40),
            ('JBL Tune 770NC', 'JBL Tune 770NC wireless headphones with adaptive noise cancelling, JBL Pure Bass, 44-hour battery.', 'Headphones', 'JBL', 6499.00, 4.3, '/static/images/products/product_14.jpg', 70),

            # Smartwatches (4)
            ('Apple Watch Ultra 2', 'Apple Watch Ultra 2 with S9 chip, precision dual-frequency GPS, 36-hour battery, rugged titanium case.', 'Smartwatches', 'Apple', 89900.00, 4.8, '/static/images/products/product_15.jpg', 25),
            ('Samsung Galaxy Watch 6 Classic', 'Samsung Galaxy Watch 6 Classic with rotating bezel, BioActive sensor, Wear OS, sleep coaching.', 'Smartwatches', 'Samsung', 36999.00, 4.5, '/static/images/products/product_16.jpg', 35),
            ('Garmin Venu 3', 'Garmin Venu 3 GPS smartwatch with AMOLED display, Body Battery energy monitoring, 14-day battery.', 'Smartwatches', 'Garmin', 44990.00, 4.6, '/static/images/products/product_17.jpg', 20),
            ('Fitbit Sense 2', 'Fitbit Sense 2 health smartwatch with stress management, ECG app, skin temperature sensor.', 'Smartwatches', 'Fitbit', 19999.00, 4.4, '/static/images/products/product_18.jpg', 40),

            # Clothing (4)
            ('Nike Dri-FIT Running T-Shirt', 'Nike Dri-FIT moisture-wicking running t-shirt with breathable mesh panels.', 'Clothing', 'Nike', 1995.00, 4.4, '/static/images/products/product_19.jpg', 100),
            ('Levi\'s 501 Original Jeans', 'Levi\'s 501 Original Fit jeans with button fly, iconic straight-leg silhouette.', 'Clothing', 'Levis', 3999.00, 4.5, '/static/images/products/product_20.jpg', 80),
            ('Adidas Essentials Track Jacket', 'Adidas Essentials 3-Stripes track jacket with recycled materials and full-zip front.', 'Clothing', 'Adidas', 4299.00, 4.3, '/static/images/products/product_21.jpg', 60),
            ('Under Armour Storm Hoodie', 'Under Armour Storm Fleece hoodie with water-repellent finish, Armour Fleece fabric.', 'Clothing', 'Under Armour', 3499.00, 4.2, '/static/images/products/product_22.jpg', 70),

            # Shoes (4)
            ('Nike Air Max 270', 'Nike Air Max 270 with large Max Air unit, mesh upper for breathability, foam midsole.', 'Shoes', 'Nike', 13995.00, 4.6, '/static/images/products/product_23.jpg', 55),
            ('Adidas Ultraboost Light', 'Adidas Ultraboost Light running shoes with LIGHT BOOST midsole, Primeknit+ upper.', 'Shoes', 'Adidas', 17999.00, 4.7, '/static/images/products/product_24.jpg', 45),
            ('Puma RS-X Reinvention', 'Puma RS-X Reinvention sneakers with Running System technology, chunky silhouette.', 'Shoes', 'Puma', 8999.00, 4.3, '/static/images/products/product_25.jpg', 50),
            ('New Balance 574 Core', 'New Balance 574 Core classic lifestyle sneakers with ENCAP midsole technology.', 'Shoes', 'New Balance', 7499.00, 4.4, '/static/images/products/product_26.jpg', 65),

            # Home Appliances (4)
            ('Dyson V15 Detect Vacuum', 'Dyson V15 Detect cordless vacuum with laser dust detection, piezo sensor, 60-min runtime.', 'Home Appliances', 'Dyson', 62900.00, 4.7, '/static/images/products/product_27.jpg', 20),
            ('Instant Pot Duo Plus 9-in-1', 'Instant Pot Duo Plus 9-in-1 electric pressure cooker with whisper-quiet steam release.', 'Home Appliances', 'Instant Pot', 10999.00, 4.6, '/static/images/products/product_28.jpg', 40),
            ('Philips Premium Air Fryer XXL', 'Philips Premium Air Fryer XXL with Fat Removal technology, rapid air, digital display.', 'Home Appliances', 'Philips', 18995.00, 4.5, '/static/images/products/product_29.jpg', 30),
            ('iRobot Roomba j7+', 'iRobot Roomba j7+ self-emptying robot vacuum with PrecisionVision navigation.', 'Home Appliances', 'iRobot', 54900.00, 4.4, '/static/images/products/product_30.jpg', 22),

            # Accessories (4)
            ('Anker PowerCore 26800mAh', 'Anker PowerCore 26800 portable charger with PowerIQ, dual USB ports, 26800mAh capacity.', 'Accessories', 'Anker', 4999.00, 4.5, '/static/images/products/product_31.jpg', 80),
            ('Logitech MX Master 3S', 'Logitech MX Master 3S wireless mouse with 8K DPI tracking, MagSpeed scroll, quiet clicks.', 'Accessories', 'Logitech', 8995.00, 4.7, '/static/images/products/product_32.jpg', 50),
            ('Samsung T7 Shield 1TB SSD', 'Samsung T7 Shield portable SSD with 1050 MB/s read speed, IP65 dust/water resistance.', 'Accessories', 'Samsung', 9499.00, 4.6, '/static/images/products/product_33.jpg', 40),
            ('Belkin 3-in-1 Wireless Charger', 'Belkin BoostCharge Pro 3-in-1 wireless charging pad for iPhone, Apple Watch, and AirPods.', 'Accessories', 'Belkin', 11999.00, 4.4, '/static/images/products/product_34.jpg', 35)
        ]

        for p in sample_products:
            cur.execute("""
                INSERT INTO products (product_name, description, category, brand, price, rating, image_url, stock_quantity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, p)

        # Seed initial user preference entries
        for cat in categories:
            cur.execute("""
                INSERT OR IGNORE INTO user_preferences (user_id, category, preference_score)
                VALUES (1, %s, 0.0)
            """, (cat,))

        db_conn.commit()
        cur.close()

"""
Features Service Module
=======================
Handles Product Comparisons, Wishlists, Price Drop Alerts,
and Explainable Results for Search & Recommendations.
"""

from backend.database import DatabaseManager


class FeaturesService:
    """Provides business logic for new user workspace and analytical features."""

    def __init__(self, db_config):
        self.db_config = db_config

    def _get_connection(self):
        return DatabaseManager.get_connection(self.db_config)

    # ============================================================
    # 1. NATURAL LANGUAGE SEARCH EXECUTION
    # ============================================================

    def execute_natural_search(self, conditions, user_id=1):
        """
        Executes a database query based on conditions parsed by the CFG engine.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            clauses = []
            params = []

            if conditions.get('category'):
                clauses.append("category = %s")
                params.append(conditions['category'])

            if conditions.get('brand'):
                clauses.append("brand = %s")
                params.append(conditions['brand'])

            if conditions.get('min_price') is not None:
                clauses.append("price >= %s")
                params.append(float(conditions['min_price']))

            if conditions.get('max_price') is not None:
                clauses.append("price <= %s")
                params.append(float(conditions['max_price']))

            if conditions.get('min_rating') is not None:
                clauses.append("rating >= %s")
                params.append(float(conditions['min_rating']))

            where_str = " AND ".join(clauses) if clauses else "1=1"
            query = f"SELECT * FROM products WHERE {where_str} ORDER BY rating DESC, price ASC"
            cursor.execute(query, tuple(params))
            products = cursor.fetchall()

            # Spec filtering (e.g. '8 gb ram', 'oled') against description / name
            specs = conditions.get('specs', [])
            if specs and products:
                filtered = []
                for p in products:
                    text = f"{p['product_name']} {p.get('description', '')}".lower()
                    # If all or any spec keyword matches
                    if any(spec.lower() in text for spec in specs):
                        filtered.append(p)
                if filtered:
                    products = filtered

            # Format price and rating
            formatted = []
            for p in products:
                item = dict(p)
                item['price'] = float(item['price'])
                item['rating'] = float(item['rating'])
                formatted.append(item)

            return {
                'products': formatted,
                'total': len(formatted),
                'conditions': conditions,
                'generated_query': query
            }
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # 2. PRODUCT COMPARISON WORKSPACE
    # ============================================================

    def add_to_comparison(self, user_id, product_id):
        """Add product to comparison list (max 4)."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT COUNT(*) as cnt FROM product_comparisons WHERE user_id = %s", (user_id,))
            res = cursor.fetchone()
            if res and res['cnt'] >= 4:
                return {
                    'status': 'error',
                    'message': 'Comparison limit reached (maximum 4 products). Please remove a product first.'
                }

            # Check if already present
            cursor.execute(
                "SELECT comparison_id FROM product_comparisons WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)
            )
            if cursor.fetchone():
                return {'status': 'info', 'message': 'Product is already in your comparison list.'}

            cursor.execute(
                "INSERT INTO product_comparisons (user_id, product_id) VALUES (%s, %s)",
                (user_id, product_id)
            )
            conn.commit()
            return {'status': 'success', 'message': 'Product added to comparison.'}
        finally:
            cursor.close()
            conn.close()

    def get_comparison(self, user_id=1):
        """Retrieve comparison products and calculate lowest-price and highest-rated markers."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT p.*, pc.added_at
                FROM product_comparisons pc
                JOIN products p ON pc.product_id = p.product_id
                WHERE pc.user_id = %s
                ORDER BY pc.added_at ASC
            """, (user_id,))
            items = cursor.fetchall()

            products = []
            for item in items:
                p = dict(item)
                p['price'] = float(p['price'])
                p['rating'] = float(p['rating'])
                products.append(p)

            # Determine best price and top rating
            lowest_price_id = None
            highest_rated_id = None

            if products:
                lowest_price_id = min(products, key=lambda x: x['price'])['product_id']
                highest_rated_id = max(products, key=lambda x: x['rating'])['product_id']

            return {
                'products': products,
                'count': len(products),
                'lowest_price_id': lowest_price_id,
                'highest_rated_id': highest_rated_id
            }
        finally:
            cursor.close()
            conn.close()

    def remove_from_comparison(self, user_id, product_id):
        """Remove single product from comparison list."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "DELETE FROM product_comparisons WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)
            )
            conn.commit()
            return {'status': 'success', 'message': 'Product removed from comparison.'}
        finally:
            cursor.close()
            conn.close()

    def clear_comparison(self, user_id=1):
        """Clear all products from comparison."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("DELETE FROM product_comparisons WHERE user_id = %s", (user_id,))
            conn.commit()
            return {'status': 'success', 'message': 'Comparison list cleared.'}
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # 3. SMART WISHLIST AND SAVED PRODUCTS
    # ============================================================

    def add_to_wishlist(self, user_id, product_id):
        """Add product to user's wishlist (prevents duplicates)."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "SELECT wishlist_id FROM wishlists WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)
            )
            if cursor.fetchone():
                return {'status': 'info', 'message': 'Product is already in your wishlist.'}

            cursor.execute(
                "INSERT INTO wishlists (user_id, product_id) VALUES (%s, %s)",
                (user_id, product_id)
            )
            conn.commit()
            return {'status': 'success', 'message': 'Added to your Wishlist!'}
        finally:
            cursor.close()
            conn.close()

    def get_wishlist(self, user_id=1):
        """Retrieve all wishlist products for a user."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT p.*, w.wishlist_id, w.added_at,
                       pa.alert_id, pa.target_price, pa.alert_status
                FROM wishlists w
                JOIN products p ON w.product_id = p.product_id
                LEFT JOIN price_alerts pa ON w.product_id = pa.product_id AND w.user_id = pa.user_id
                WHERE w.user_id = %s
                ORDER BY w.added_at DESC
            """, (user_id,))
            items = cursor.fetchall()

            products = []
            for item in items:
                p = dict(item)
                p['price'] = float(p['price'])
                p['rating'] = float(p['rating'])
                if p.get('target_price') is not None:
                    p['target_price'] = float(p['target_price'])
                products.append(p)

            return {
                'products': products,
                'count': len(products)
            }
        finally:
            cursor.close()
            conn.close()

    def remove_from_wishlist(self, user_id, product_id):
        """Remove product from wishlist."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "DELETE FROM wishlists WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)
            )
            conn.commit()
            return {'status': 'success', 'message': 'Product removed from wishlist.'}
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # 4. PRICE DROP ALERT SYSTEM
    # ============================================================

    def set_price_alert(self, user_id, product_id, target_price):
        """Set or update target price alert for a product."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Check current product price
            cursor.execute("SELECT price FROM products WHERE product_id = %s", (product_id,))
            prod = cursor.fetchone()
            if not prod:
                return {'status': 'error', 'message': 'Product not found.'}

            current_price = float(prod['price'])
            status = 'triggered' if current_price <= float(target_price) else 'active'

            cursor.execute(
                "SELECT alert_id FROM price_alerts WHERE user_id = %s AND product_id = %s",
                (user_id, product_id)
            )
            existing = cursor.fetchone()
            if existing:
                cursor.execute("""
                    UPDATE price_alerts
                    SET target_price = %s, alert_status = %s
                    WHERE alert_id = %s
                """, (float(target_price), status, existing['alert_id']))
            else:
                cursor.execute("""
                    INSERT INTO price_alerts (user_id, product_id, target_price, alert_status)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, product_id, float(target_price), status))
            conn.commit()

            return {
                'status': 'success',
                'message': f'Price alert set for ₹{float(target_price):,}!',
                'alert_status': status
            }
        finally:
            cursor.close()
            conn.close()

    def get_price_alerts(self, user_id=1):
        """Retrieve active and triggered price alerts."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # First, check and update alerts based on current DB prices
            cursor.execute("""
                SELECT pa.alert_id, pa.product_id, pa.target_price, p.price as current_price
                FROM price_alerts pa
                JOIN products p ON pa.product_id = p.product_id
                WHERE pa.user_id = %s
            """, (user_id,))
            alerts = cursor.fetchall()

            for a in alerts:
                curr = float(a['current_price'])
                target = float(a['target_price'])
                new_status = 'triggered' if curr <= target else 'active'
                cursor.execute("""
                    UPDATE price_alerts
                    SET alert_status = %s,
                        triggered_at = CASE WHEN %s = 'triggered' THEN CURRENT_TIMESTAMP ELSE NULL END
                    WHERE alert_id = %s
                """, (new_status, new_status, a['alert_id']))
            conn.commit()

            # Retrieve separated lists
            cursor.execute("""
                SELECT pa.*, p.product_name, p.brand, p.category, p.price as current_price, p.image_url
                FROM price_alerts pa
                JOIN products p ON pa.product_id = p.product_id
                WHERE pa.user_id = %s
                ORDER BY pa.created_at DESC
            """, (user_id,))
            all_alerts = cursor.fetchall()

            active = []
            triggered = []
            for item in all_alerts:
                row = dict(item)
                row['current_price'] = float(row['current_price'])
                row['target_price'] = float(row['target_price'])
                row['price_difference'] = round(row['current_price'] - row['target_price'], 2)

                if row['alert_status'] == 'triggered':
                    triggered.append(row)
                else:
                    active.append(row)

            return {
                'active_alerts': active,
                'triggered_alerts': triggered,
                'total_active': len(active),
                'total_triggered': len(triggered)
            }
        finally:
            cursor.close()
            conn.close()

    def delete_price_alert(self, user_id, alert_id):
        """Delete a price alert."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(
                "DELETE FROM price_alerts WHERE user_id = %s AND alert_id = %s",
                (user_id, alert_id)
            )
            conn.commit()
            return {'status': 'success', 'message': 'Price alert deleted.'}
        finally:
            cursor.close()
            conn.close()

    def simulate_price_drop(self, product_id, new_price):
        """
        Controlled demonstration endpoint for evaluation:
        Updates a sample product's price in the database to trigger an alert.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT product_name, price FROM products WHERE product_id = %s", (product_id,))
            p = cursor.fetchone()
            if not p:
                return {'status': 'error', 'message': 'Product not found'}

            old_price = float(p['price'])
            cursor.execute(
                "UPDATE products SET price = %s WHERE product_id = %s",
                (float(new_price), product_id)
            )
            conn.commit()

            # Update alerts
            cursor.execute("""
                UPDATE price_alerts
                SET alert_status = 'triggered', triggered_at = CURRENT_TIMESTAMP
                WHERE product_id = %s AND target_price >= %s
            """, (product_id, float(new_price)))
            conn.commit()

            return {
                'status': 'success',
                'product_id': product_id,
                'product_name': p['product_name'],
                'old_price': old_price,
                'new_price': float(new_price),
                'message': f"Updated {p['product_name']} price from ₹{old_price:,} to ₹{float(new_price):,}. Alerts triggered!"
            }
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # 5. EXPLAINABLE RESULTS
    # ============================================================

    def explain_search_match(self, product_id, query):
        """Provide detailed reasoning why a product matched a search query."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            if not product:
                return {'error': 'Product not found'}

            query_lower = query.lower().strip()
            keywords = query_lower.split()

            name_lower = product['product_name'].lower()
            desc_lower = (product.get('description') or '').lower()
            cat_lower = product['category'].lower()
            brand_lower = product['brand'].lower()

            matches = {
                'exact_name_match': query_lower == name_lower,
                'name_keywords': [kw for kw in keywords if kw in name_lower],
                'description_keywords': [kw for kw in keywords if kw in desc_lower],
                'category_matched': any(kw in cat_lower for kw in keywords),
                'brand_matched': any(kw in brand_lower for kw in keywords)
            }

            return {
                'product_id': product_id,
                'product_name': product['product_name'],
                'category': product['category'],
                'brand': product['brand'],
                'query': query,
                'keywords_extracted': keywords,
                'matching_details': matches,
                'explanation': (
                    f"Product matched because: " +
                    (", ".join(filter(None, [
                        "Product name contains keyword(s)" if matches['name_keywords'] else "",
                        "Description matches query term(s)" if matches['description_keywords'] else "",
                        f"Category '{product['category']}' matches query" if matches['category_matched'] else "",
                        f"Brand '{product['brand']}' matches query" if matches['brand_matched'] else ""
                    ])) or "Matches broad keyword search pattern.")
                )
            }
        finally:
            cursor.close()
            conn.close()

    def explain_recommendation(self, product_id, user_id=1):
        """Provide detailed reasoning why a product was recommended to the user."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            if not product:
                return {'error': 'Product not found'}

            cat = product['category']

            # Get user preference score for this category
            cursor.execute(
                "SELECT preference_score FROM user_preferences WHERE user_id = %s AND category = %s",
                (user_id, cat)
            )
            pref_row = cursor.fetchone()
            pref_score = float(pref_row['preference_score']) if pref_row else 0.0

            # Get user recent views in this category
            cursor.execute("""
                SELECT COUNT(*) as views_count
                FROM user_activity ua
                JOIN products p ON ua.product_id = p.product_id
                WHERE ua.user_id = %s AND p.category = %s AND ua.activity_type = 'view'
            """, (user_id, cat))
            views_row = cursor.fetchone()
            views_count = views_row['views_count'] if views_row else 0

            return {
                'product_id': product_id,
                'product_name': product['product_name'],
                'category': cat,
                'rating': float(product['rating']),
                'user_category_preference_score': pref_score,
                'user_category_views_count': views_count,
                'formula': "Recommendation Score = (Category Preference × 3.0) + (Product Rating × 2.0)",
                'explanation': (
                    f"Recommended because you viewed {views_count} item(s) in {cat} "
                    f"(affinity score: {pref_score:.1f}) and this product has an outstanding "
                    f"rating of {float(product['rating']):.1f} / 5.0."
                )
            }
        finally:
            cursor.close()
            conn.close()

"""
Ranking Engine Module
=====================
Intelligent product ranking and adaptive filtering system.
Calculates relevance scores using weighted scoring of keyword match,
category preference, rating, and user interaction history.
"""

import re
from backend.database import DatabaseManager


class RankingEngine:
    """
    Ranks and filters products using a weighted scoring algorithm.

    Ranking Formula:
        Total Score = (Keyword Score × 3.0) + (Category Pref Score × 2.5)
                    + (Rating Score × 2.0) + (Interaction Score × 1.5)

    Each component is normalized to [0, 1] before weighting.
    """

    WEIGHTS = {
        'keyword_match': 3.0,
        'category_preference': 2.5,
        'rating': 2.0,
        'interaction': 1.5
    }

    def __init__(self, db_config):
        self.db_config = db_config

    def _get_connection(self):
        return DatabaseManager.get_connection(self.db_config)

    def get_filtered_products(self, category=None, min_price=None, max_price=None,
                               brand=None, min_rating=None, sort_by='relevant',
                               search_query=None, user_id=1):
        """
        Filter and rank products based on multiple criteria.

        Args:
            category: Filter by category name.
            min_price: Minimum price filter.
            max_price: Maximum price filter.
            brand: Filter by brand name.
            min_rating: Minimum rating filter.
            sort_by: Sorting method ('price_asc', 'price_desc', 'rating', 'relevant').
            search_query: Optional search query for relevance scoring.
            user_id: User ID for personalized ranking.

        Returns:
            dict with filtered products, their ranking scores, and breakdown.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Build dynamic SQL query
            conditions = []
            params = []

            if category:
                conditions.append("p.category = %s")
                params.append(category)

            if min_price is not None:
                conditions.append("p.price >= %s")
                params.append(float(min_price))

            if max_price is not None:
                conditions.append("p.price <= %s")
                params.append(float(max_price))

            if brand:
                conditions.append("p.brand = %s")
                params.append(brand)

            if min_rating is not None:
                conditions.append("p.rating >= %s")
                params.append(float(min_rating))

            where_clause = " AND ".join(conditions) if conditions else "1=1"

            query = f"SELECT * FROM products p WHERE {where_clause}"
            cursor.execute(query, tuple(params))
            products = cursor.fetchall()

            # Get user preferences
            cursor.execute("""
                SELECT category, preference_score
                FROM user_preferences
                WHERE user_id = %s
            """, (user_id,))
            preferences = {row['category']: float(row['preference_score'])
                           for row in cursor.fetchall()}

            # Get user interaction counts per product
            cursor.execute("""
                SELECT product_id, COUNT(*) as interaction_count
                FROM user_activity
                WHERE user_id = %s
                GROUP BY product_id
            """, (user_id,))
            interactions = {row['product_id']: row['interaction_count']
                            for row in cursor.fetchall()}

            # Calculate ranking score for each product
            max_pref = max(preferences.values()) if preferences and any(v > 0 for v in preferences.values()) else 1.0
            max_interaction = max(interactions.values()) if interactions else 1.0
            max_rating = 5.0

            ranked_products = []
            for product in products:
                p = dict(product)
                p['price'] = float(p['price'])
                p['rating'] = float(p['rating'])

                # Calculate component scores
                keyword_score = 0.0
                if search_query:
                    keyword_score = self._keyword_score(search_query, product)

                cat_pref_score = preferences.get(product['category'], 0) / max_pref if max_pref > 0 else 0
                rating_score = float(product['rating']) / max_rating
                interaction_score = interactions.get(product['product_id'], 0) / max_interaction if max_interaction > 0 else 0

                # Weighted total
                total_score = (
                    keyword_score * self.WEIGHTS['keyword_match'] +
                    cat_pref_score * self.WEIGHTS['category_preference'] +
                    rating_score * self.WEIGHTS['rating'] +
                    interaction_score * self.WEIGHTS['interaction']
                )

                p['ranking_score'] = round(total_score, 3)
                p['ranking_breakdown'] = {
                    'keyword_match': round(keyword_score * self.WEIGHTS['keyword_match'], 3),
                    'category_preference': round(cat_pref_score * self.WEIGHTS['category_preference'], 3),
                    'rating': round(rating_score * self.WEIGHTS['rating'], 3),
                    'interaction': round(interaction_score * self.WEIGHTS['interaction'], 3)
                }

                ranked_products.append(p)

            # Apply sorting
            if sort_by == 'price_asc':
                ranked_products.sort(key=lambda x: x['price'])
            elif sort_by == 'price_desc':
                ranked_products.sort(key=lambda x: x['price'], reverse=True)
            elif sort_by == 'rating':
                ranked_products.sort(key=lambda x: x['rating'], reverse=True)
            else:  # 'relevant' - default
                ranked_products.sort(key=lambda x: x['ranking_score'], reverse=True)

            # Get available filter options for the UI
            filter_options = self._get_filter_options(cursor)

            return {
                'products': ranked_products,
                'total': len(ranked_products),
                'applied_filters': {
                    'category': category,
                    'min_price': min_price,
                    'max_price': max_price,
                    'brand': brand,
                    'min_rating': min_rating,
                    'sort_by': sort_by
                },
                'filter_options': filter_options,
                'ranking_weights': self.WEIGHTS,
                'ranking_formula': (
                    'Total = (Keyword × 3.0) + (Category Pref × 2.5) '
                    '+ (Rating × 2.0) + (Interaction × 1.5)'
                )
            }

        except Exception as e:
            return {
                'products': [],
                'total': 0,
                'error': str(e)
            }
        finally:
            cursor.close()
            conn.close()

    def _keyword_score(self, query, product):
        """
        Calculate keyword match score for a product against a search query.
        Returns a value between 0 and 1.
        """
        if not query:
            return 0.0

        keywords = re.findall(r'[a-zA-Z0-9]+', query.lower())
        if not keywords:
            return 0.0

        searchable_fields = [
            product['product_name'].lower(),
            (product.get('description') or '').lower(),
            product['category'].lower(),
            product['brand'].lower()
        ]
        searchable_text = ' '.join(searchable_fields)

        matches = 0
        for kw in keywords:
            if kw in searchable_text:
                matches += 1
                # Bonus for name match
                if kw in product['product_name'].lower():
                    matches += 0.5

        return min(matches / len(keywords), 1.0)

    def _get_filter_options(self, cursor):
        """Get available filter options (categories, brands, price range)."""
        cursor.execute("SELECT DISTINCT category FROM products ORDER BY category")
        categories = [row['category'] for row in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT brand FROM products ORDER BY brand")
        brands = [row['brand'] for row in cursor.fetchall()]

        cursor.execute("SELECT MIN(price) as min_p, MAX(price) as max_p FROM products")
        price_range = cursor.fetchone()

        return {
            'categories': categories,
            'brands': brands,
            'price_range': {
                'min': float(price_range['min_p']) if price_range['min_p'] else 0,
                'max': float(price_range['max_p']) if price_range['max_p'] else 10000
            }
        }

    def get_all_products(self, user_id=1):
        """Get all products with ranking scores."""
        return self.get_filtered_products(user_id=user_id)

    def get_product_by_id(self, product_id):
        """Get a single product by ID."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT * FROM products WHERE product_id = %s", (product_id,))
            product = cursor.fetchone()
            if product:
                product['price'] = float(product['price'])
                product['rating'] = float(product['rating'])
            return product
        finally:
            cursor.close()
            conn.close()

    def get_categories(self):
        """Get all categories with product counts."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT c.category_name, COUNT(p.product_id) as product_count
                FROM categories c
                LEFT JOIN products p ON c.category_name = p.category
                GROUP BY c.category_name
                ORDER BY c.category_name
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_brands(self):
        """Get all unique brands."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT DISTINCT brand, COUNT(*) as product_count
                FROM products
                GROUP BY brand
                ORDER BY brand
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

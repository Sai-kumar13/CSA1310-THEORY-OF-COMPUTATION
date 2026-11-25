"""
Recommendation Engine Module
=============================
Personalized product recommendation based on user search history,
viewed products, category preferences, and interaction patterns.
"""

from collections import Counter
from backend.database import DatabaseManager


class RecommendationEngine:
    """
    Generates personalized product recommendations based on:
    - Search history frequency
    - Product view history
    - Category preference scores
    - Related product associations
    """

    # Category relationships for cross-category recommendations
    RELATED_CATEGORIES = {
        'Smartphones': ['Accessories', 'Smartwatches', 'Headphones'],
        'Laptops': ['Accessories', 'Headphones'],
        'Headphones': ['Smartphones', 'Accessories', 'Laptops'],
        'Smartwatches': ['Smartphones', 'Accessories', 'Shoes'],
        'Clothing': ['Shoes', 'Accessories'],
        'Shoes': ['Clothing', 'Accessories'],
        'Home Appliances': ['Accessories'],
        'Accessories': ['Smartphones', 'Laptops', 'Headphones']
    }

    def __init__(self, db_config):
        self.db_config = db_config

    def _get_connection(self):
        return DatabaseManager.get_connection(self.db_config)

    def record_product_view(self, user_id, product_id):
        """Record that a user viewed a product."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Insert view activity
            cursor.execute("""
                INSERT INTO user_activity (user_id, product_id, activity_type)
                VALUES (%s, %s, 'view')
            """, (user_id, product_id))

            # Get the product's category
            cursor.execute(
                "SELECT category FROM products WHERE product_id = %s",
                (product_id,)
            )
            result = cursor.fetchone()

            if result:
                category = result['category']
                # Update preference score for this category
                cursor.execute("""
                    INSERT INTO user_preferences (user_id, category, preference_score)
                    VALUES (%s, %s, 2.0)
                    ON DUPLICATE KEY UPDATE preference_score = preference_score + 2.0
                """, (user_id, category))

                # Also boost related categories slightly
                related = self.RELATED_CATEGORIES.get(category, [])
                for rel_cat in related:
                    cursor.execute("""
                        INSERT INTO user_preferences (user_id, category, preference_score)
                        VALUES (%s, %s, 0.5)
                        ON DUPLICATE KEY UPDATE preference_score = preference_score + 0.5
                    """, (user_id, rel_cat))

            conn.commit()
            return {'status': 'success', 'message': 'Product view recorded.'}

        except Exception as e:
            conn.rollback()
            return {'status': 'error', 'message': str(e)}
        finally:
            cursor.close()
            conn.close()

    def get_recommendations(self, user_id=1, limit=12):
        """
        Generate personalized product recommendations.

        Algorithm:
        1. Get user's top category preferences.
        2. Find recently viewed product categories.
        3. Include related categories.
        4. Score products based on:
           - Category preference score (weight: 3)
           - Product rating (weight: 2)
           - Not recently viewed bonus (weight: 1)
        5. Return top-scored products.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # 1. Get user preferences
            cursor.execute("""
                SELECT category, preference_score
                FROM user_preferences
                WHERE user_id = %s
                ORDER BY preference_score DESC
            """, (user_id,))
            preferences = {row['category']: float(row['preference_score'])
                           for row in cursor.fetchall()}

            # 2. Get recently viewed product IDs
            cursor.execute("""
                SELECT DISTINCT product_id FROM user_activity
                WHERE user_id = %s AND activity_type = 'view'
                ORDER BY activity_time DESC
                LIMIT 20
            """, (user_id,))
            viewed_ids = {row['product_id'] for row in cursor.fetchall()}

            # 3. Determine target categories
            top_categories = sorted(preferences.keys(),
                                     key=lambda c: preferences.get(c, 0),
                                     reverse=True)
            target_categories = set()
            for cat in top_categories[:4]:
                if preferences.get(cat, 0) > 0:
                    target_categories.add(cat)
                    for rel in self.RELATED_CATEGORIES.get(cat, []):
                        target_categories.add(rel)

            # 4. Get candidate products
            cursor.execute("SELECT * FROM products")
            all_products = cursor.fetchall()

            # 5. Score each product
            scored = []
            for product in all_products:
                score = 0.0
                cat = product['category']

                # Category preference contribution
                pref_score = preferences.get(cat, 0)
                score += pref_score * 3.0

                # Related category bonus
                if cat in target_categories and pref_score == 0:
                    score += 2.0

                # Rating contribution
                score += float(product['rating']) * 2.0

                # Avoid re-recommending recently viewed (but still include with lower score)
                if product['product_id'] in viewed_ids:
                    score *= 0.5

                # Only recommend products with some relevance
                if score > 0 or not preferences or all(v == 0 for v in preferences.values()):
                    p = dict(product)
                    p['price'] = float(p['price'])
                    p['rating'] = float(p['rating'])
                    p['recommendation_score'] = round(score, 2)
                    scored.append(p)

            # If no preferences exist yet, recommend highest rated products
            if not any(v > 0 for v in preferences.values()):
                scored.sort(key=lambda x: float(x['rating']), reverse=True)
            else:
                scored.sort(key=lambda x: x['recommendation_score'], reverse=True)

            return {
                'recommendations': scored[:limit],
                'user_preferences': preferences,
                'top_categories': list(target_categories)[:5],
                'total': min(len(scored), limit)
            }

        except Exception as e:
            return {
                'recommendations': [],
                'user_preferences': {},
                'top_categories': [],
                'total': 0,
                'error': str(e)
            }
        finally:
            cursor.close()
            conn.close()

    def get_recently_viewed(self, user_id=1, limit=10):
        """Get recently viewed products for a user."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT DISTINCT p.*, ua.activity_time
                FROM user_activity ua
                JOIN products p ON ua.product_id = p.product_id
                WHERE ua.user_id = %s AND ua.activity_type = 'view'
                ORDER BY ua.activity_time DESC
                LIMIT %s
            """, (user_id, limit))
            results = cursor.fetchall()

            products = []
            for r in results:
                r['price'] = float(r['price'])
                r['rating'] = float(r['rating'])
                r['activity_time'] = r['activity_time'].strftime('%Y-%m-%d %H:%M:%S')
                products.append(r)

            return products

        except Exception as e:
            return []
        finally:
            cursor.close()
            conn.close()

    def get_similar_products(self, product_id, limit=6):
        """
        Get products similar to a given product.
        Based on same category, same brand, and similar price range.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get the reference product
            cursor.execute(
                "SELECT * FROM products WHERE product_id = %s",
                (product_id,)
            )
            ref_product = cursor.fetchone()
            if not ref_product:
                return []

            ref_price = float(ref_product['price'])
            price_range_low = ref_price * 0.5
            price_range_high = ref_price * 1.5

            # Get similar products: same category or same brand, similar price
            cursor.execute("""
                SELECT *, ABS(price - %s) as price_diff FROM products
                WHERE product_id != %s
                AND (category = %s OR brand = %s OR (price BETWEEN %s AND %s))
                ORDER BY
                    CASE WHEN category = %s THEN 0 ELSE 1 END,
                    CASE WHEN brand = %s THEN 0 ELSE 1 END,
                    ABS(price - %s)
                LIMIT %s
            """, (ref_price, product_id, ref_product['category'],
                  ref_product['brand'], price_range_low, price_range_high,
                  ref_product['category'], ref_product['brand'],
                  ref_price, limit))

            results = cursor.fetchall()
            for r in results:
                r['price'] = float(r['price'])
                r['rating'] = float(r['rating'])
                if 'price_diff' in r:
                    r['price_diff'] = float(r['price_diff'])

            return results

        except Exception as e:
            return []
        finally:
            cursor.close()
            conn.close()

    def get_because_you_viewed(self, user_id=1, limit=8):
        """
        Get recommendations based on viewed product categories.
        "Because You Viewed These Products" section.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get categories of recently viewed products
            cursor.execute("""
                SELECT DISTINCT p.category
                FROM user_activity ua
                JOIN products p ON ua.product_id = p.product_id
                WHERE ua.user_id = %s AND ua.activity_type = 'view'
                ORDER BY ua.activity_time DESC
                LIMIT 5
            """, (user_id,))
            viewed_categories = [row['category'] for row in cursor.fetchall()]

            if not viewed_categories:
                return {'products': [], 'based_on_categories': []}

            # Get viewed product IDs to exclude
            cursor.execute("""
                SELECT DISTINCT product_id FROM user_activity
                WHERE user_id = %s AND activity_type = 'view'
            """, (user_id,))
            viewed_ids = {row['product_id'] for row in cursor.fetchall()}

            # Build query for products in those categories
            placeholders = ', '.join(['%s'] * len(viewed_categories))
            cursor.execute(f"""
                SELECT * FROM products
                WHERE category IN ({placeholders})
                ORDER BY rating DESC
                LIMIT %s
            """, (*viewed_categories, limit + len(viewed_ids)))

            results = cursor.fetchall()
            products = []
            for r in results:
                if r['product_id'] not in viewed_ids and len(products) < limit:
                    r['price'] = float(r['price'])
                    r['rating'] = float(r['rating'])
                    products.append(r)

            return {
                'products': products,
                'based_on_categories': viewed_categories
            }

        except Exception as e:
            return {'products': [], 'based_on_categories': [], 'error': str(e)}
        finally:
            cursor.close()
            conn.close()

    def get_user_preferences(self, user_id=1):
        """Get the user's category preferences."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT category, preference_score
                FROM user_preferences
                WHERE user_id = %s
                ORDER BY preference_score DESC
            """, (user_id,))
            results = cursor.fetchall()
            for r in results:
                r['preference_score'] = float(r['preference_score'])
            return results
        except Exception as e:
            return []
        finally:
            cursor.close()
            conn.close()

    def get_trending_products(self, limit=8):
        """
        Get trending products based on recent view activity across all users.
        Falls back to highest-rated products if no activity exists.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Try to get products with most views
            cursor.execute("""
                SELECT p.*, COUNT(ua.activity_id) as view_count
                FROM products p
                LEFT JOIN user_activity ua ON p.product_id = ua.product_id
                    AND ua.activity_type = 'view'
                GROUP BY p.product_id
                ORDER BY view_count DESC, p.rating DESC
                LIMIT %s
            """, (limit,))
            results = cursor.fetchall()

            for r in results:
                r['price'] = float(r['price'])
                r['rating'] = float(r['rating'])

            return results
        except Exception as e:
            return []
        finally:
            cursor.close()
            conn.close()

    def get_frequently_searched_categories(self, user_id=1):
        """Get the user's most frequently searched categories."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT category, preference_score
                FROM user_preferences
                WHERE user_id = %s AND preference_score > 0
                ORDER BY preference_score DESC
                LIMIT 5
            """, (user_id,))
            results = cursor.fetchall()
            for r in results:
                r['preference_score'] = float(r['preference_score'])
            return results
        except Exception as e:
            return []
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # DIVERSE & DISCOVERY-BASED RECOMMENDATIONS
    # ============================================================

    def get_similar_recommendations(self, user_id=1, limit=8):
        """
        Get products similar to what the user has shown interest in.
        "More Like What You Like" — same categories, similar brands and prices.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get user's top preferred categories
            cursor.execute("""
                SELECT category, preference_score
                FROM user_preferences
                WHERE user_id = %s AND preference_score > 0
                ORDER BY preference_score DESC
                LIMIT 3
            """, (user_id,))
            top_prefs = cursor.fetchall()

            if not top_prefs:
                # Fallback: return highest rated products
                cursor.execute("""
                    SELECT * FROM products ORDER BY rating DESC LIMIT %s
                """, (limit,))
                products = cursor.fetchall()
                for p in products:
                    p['price'] = float(p['price'])
                    p['rating'] = float(p['rating'])
                    p['similarity_reason'] = 'Top-rated product (no browsing history yet)'
                return {
                    'products': products,
                    'based_on': 'Top-rated products (no preferences yet)',
                    'explanation': 'Browse and search products to build your preference profile!'
                }

            top_categories = [r['category'] for r in top_prefs]

            # Get recently viewed product IDs to exclude
            cursor.execute("""
                SELECT DISTINCT product_id FROM user_activity
                WHERE user_id = %s AND activity_type = 'view'
                ORDER BY activity_time DESC LIMIT 20
            """, (user_id,))
            viewed_ids = {r['product_id'] for r in cursor.fetchall()}

            # Get products in preferred categories
            placeholders = ', '.join(['%s'] * len(top_categories))
            cursor.execute(f"""
                SELECT * FROM products
                WHERE category IN ({placeholders})
                ORDER BY rating DESC
                LIMIT %s
            """, (*top_categories, limit + len(viewed_ids)))
            candidates = cursor.fetchall()

            products = []
            pref_map = {r['category']: float(r['preference_score']) for r in top_prefs}

            for p in candidates:
                if p['product_id'] not in viewed_ids and len(products) < limit:
                    p['price'] = float(p['price'])
                    p['rating'] = float(p['rating'])
                    score = pref_map.get(p['category'], 0)
                    p['similarity_reason'] = (
                        f'Similar to your interests in {p["category"]} '
                        f'(preference score: {score:.1f})'
                    )
                    products.append(p)

            return {
                'products': products,
                'based_on': f'Your interest in: {", ".join(top_categories)}',
                'explanation': (
                    'These products are from categories you have searched for and viewed. '
                    'The recommendation automaton matches your preference state vector '
                    'against the product catalog.'
                )
            }

        except Exception as e:
            return {'products': [], 'based_on': '', 'explanation': str(e)}
        finally:
            cursor.close()
            conn.close()

    def get_discovery_recommendations(self, user_id=1, limit=8):
        """
        Get products from categories the user has NOT explored yet.
        "Explore Something New" — promotes diversity and discovery.
        Uses RELATED_CATEGORIES to find meaningful adjacent categories.
        """
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Get user's explored categories
            cursor.execute("""
                SELECT category, preference_score
                FROM user_preferences
                WHERE user_id = %s AND preference_score > 0
                ORDER BY preference_score DESC
            """, (user_id,))
            explored = {r['category']: float(r['preference_score']) for r in cursor.fetchall()}

            # Get ALL categories
            cursor.execute("SELECT DISTINCT category FROM products")
            all_categories = [r['category'] for r in cursor.fetchall()]

            # Find unexplored categories
            unexplored = [c for c in all_categories if c not in explored]

            # Also include related categories with low scores
            related_unexplored = set()
            for explored_cat in explored:
                for related in self.RELATED_CATEGORIES.get(explored_cat, []):
                    if related not in explored or explored.get(related, 0) < 2.0:
                        related_unexplored.add(related)

            # Combine unexplored and related-but-low-score categories
            discovery_categories = list(set(unexplored) | related_unexplored)

            if not discovery_categories:
                # User has explored everything — suggest lowest-preference categories
                discovery_categories = sorted(
                    explored.keys(), key=lambda c: explored.get(c, 0)
                )[:3]

            if not discovery_categories:
                discovery_categories = all_categories

            # Get products from discovery categories
            placeholders = ', '.join(['%s'] * len(discovery_categories))
            cursor.execute(f"""
                SELECT * FROM products
                WHERE category IN ({placeholders})
                ORDER BY rating DESC
                LIMIT %s
            """, (*discovery_categories, limit))
            products = cursor.fetchall()

            for p in products:
                p['price'] = float(p['price'])
                p['rating'] = float(p['rating'])
                is_related = p['category'] in related_unexplored
                is_new = p['category'] in unexplored
                if is_new:
                    p['discovery_reason'] = f'New category for you — explore {p["category"]}!'
                elif is_related:
                    # Find which explored category it's related to
                    related_to = [ec for ec in explored
                                  if p['category'] in self.RELATED_CATEGORIES.get(ec, [])]
                    p['discovery_reason'] = (
                        f'Related to your interest in {", ".join(related_to)}. '
                        f'Discover {p["category"]}!'
                    )
                else:
                    p['discovery_reason'] = f'Expand your horizons with {p["category"]}'

            return {
                'products': products,
                'discovery_categories': discovery_categories,
                'explored_categories': list(explored.keys()),
                'explanation': (
                    'These products are from categories you haven\'t explored much. '
                    'The discovery automaton uses the RELATED_CATEGORIES graph to find '
                    'adjacent product spaces that might interest you, promoting diversity.'
                )
            }

        except Exception as e:
            return {
                'products': [], 'discovery_categories': [],
                'explored_categories': [], 'explanation': str(e)
            }
        finally:
            cursor.close()
            conn.close()

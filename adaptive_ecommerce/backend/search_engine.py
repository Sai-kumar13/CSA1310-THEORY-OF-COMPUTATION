"""
Search Engine Module
====================
Implements adaptive product search using DFA, NFA, and Regular Expressions.
Processes user queries, tokenizes input, and returns ranked search results.
"""

import re
from backend.automata import SearchAutomaton, RegexMatcher, DFA
from backend.database import DatabaseManager


class SearchEngine:
    """
    Intelligent search engine that uses Theory of Computation concepts
    (DFA, NFA, Regex) to match products against user queries.
    """

    def __init__(self, db_config):
        self.db_config = db_config

    def _get_connection(self):
        return DatabaseManager.get_connection(self.db_config)

    def _tokenize(self, query):
        """
        Tokenize a search query into meaningful keywords.
        Removes stop words and normalizes input.
        """
        stop_words = {'a', 'an', 'the', 'is', 'are', 'was', 'were', 'in',
                       'on', 'at', 'to', 'for', 'of', 'with', 'and', 'or',
                       'but', 'not', 'this', 'that', 'it', 'by', 'from'}
        # Tokenize: split on non-alphanumeric characters
        tokens = re.findall(r'[a-zA-Z0-9]+', query.lower())
        # Filter stop words and very short tokens
        keywords = [t for t in tokens if t not in stop_words and len(t) >= 2]
        return keywords if keywords else tokens  # Fallback to all tokens

    def search(self, query, user_id=1):
        """
        Search products using DFA pattern matching and regex.

        Args:
            query: User's search string.
            user_id: ID of the user performing the search.

        Returns:
            dict with search results, automata details, and matched products.
        """
        if not query or not query.strip():
            return {
                'query': '',
                'keywords': [],
                'products': [],
                'total': 0,
                'automata_info': None,
                'message': 'Please enter a search query.'
            }

        keywords = self._tokenize(query)

        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            # Record search in history
            cursor.execute(
                "INSERT INTO search_history (user_id, search_query) VALUES (%s, %s)",
                (user_id, query)
            )
            conn.commit()

            # Fetch all products
            cursor.execute("SELECT * FROM products ORDER BY product_name")
            all_products = cursor.fetchall()

            # === DFA-based matching ===
            dfa_matched_ids = set()
            dfa_details = []

            for keyword in keywords:
                dfa = SearchAutomaton.build_dfa_for_pattern(keyword)
                if dfa is None:
                    continue

                for product in all_products:
                    # Check product name
                    name_result = dfa.process(product['product_name'].lower())
                    # Check description
                    desc_text = (product.get('description') or '').lower()
                    desc_result = dfa.process(desc_text)
                    # Check category
                    cat_result = dfa.process(product['category'].lower())
                    # Check brand
                    brand_result = dfa.process(product['brand'].lower())

                    if (name_result['accepted'] or desc_result['accepted'] or
                            cat_result['accepted'] or brand_result['accepted']):
                        dfa_matched_ids.add(product['product_id'])
                        # Store first keyword's DFA detail for demo
                        if len(dfa_details) < 3:
                            dfa_details.append({
                                'keyword': keyword,
                                'product': product['product_name'],
                                'name_accepted': name_result['accepted'],
                                'desc_accepted': desc_result['accepted'],
                                'transitions_count': name_result['total_steps'],
                                'final_state': name_result['current_state']
                            })

            # === Regex-based matching (broader) ===
            regex_matched_ids = set()
            escaped_keywords = [re.escape(kw) for kw in keywords]
            pattern = '|'.join(escaped_keywords)
            regex_obj = re.compile(pattern, re.IGNORECASE)

            for product in all_products:
                searchable = f"{product['product_name']} {product.get('description', '')} {product['category']} {product['brand']}"
                if regex_obj.search(searchable):
                    regex_matched_ids.add(product['product_id'])

            # Combine matches (union of DFA and regex matches)
            all_matched_ids = dfa_matched_ids | regex_matched_ids
            matched_products = [p for p in all_products if p['product_id'] in all_matched_ids]

            # Calculate relevance score for ordering
            scored_products = []
            for product in matched_products:
                score = self._calculate_relevance(product, keywords, regex_obj)
                product_dict = dict(product)
                product_dict['relevance_score'] = score
                # Convert Decimal to float for JSON serialization
                product_dict['price'] = float(product_dict['price'])
                product_dict['rating'] = float(product_dict['rating'])
                scored_products.append(product_dict)

            # Sort by relevance score descending
            scored_products.sort(key=lambda x: x['relevance_score'], reverse=True)

            # Update user preferences based on matched categories
            matched_categories = set(p['category'] for p in scored_products)
            for cat in matched_categories:
                cursor.execute("""
                    INSERT INTO user_preferences (user_id, category, preference_score)
                    VALUES (%s, %s, 1.0)
                    ON DUPLICATE KEY UPDATE preference_score = preference_score + 1.0
                """, (user_id, cat))
            conn.commit()

            # Build automata info for display
            automata_info = {
                'input_string': query,
                'keywords': keywords,
                'regex_pattern': f'(?i)({pattern})',
                'dfa_states_example': None,
                'dfa_details': dfa_details,
                'dfa_matched_count': len(dfa_matched_ids),
                'regex_matched_count': len(regex_matched_ids),
                'total_matched': len(all_matched_ids)
            }

            # Include a sample DFA trace for the first keyword
            if keywords:
                sample_dfa = SearchAutomaton.build_dfa_for_pattern(keywords[0])
                if sample_dfa and scored_products:
                    sample_trace = sample_dfa.process(scored_products[0]['product_name'].lower())
                    automata_info['dfa_states_example'] = {
                        'states': sample_trace['states'][:10],  # Limit for display
                        'start_state': sample_trace['start_state'],
                        'accept_states': sample_trace['accept_states'],
                        'current_state': sample_trace['current_state'],
                        'accepted': sample_trace['accepted'],
                        'transitions': sample_trace['transitions'][:15]  # Limit
                    }

            return {
                'query': query,
                'keywords': keywords,
                'products': scored_products,
                'total': len(scored_products),
                'automata_info': automata_info,
                'message': f'Found {len(scored_products)} products' if scored_products else 'No products found matching your search.'
            }

        except Exception as e:
            return {
                'query': query,
                'keywords': keywords,
                'products': [],
                'total': 0,
                'automata_info': None,
                'message': f'Search error: {str(e)}'
            }
        finally:
            cursor.close()
            conn.close()

    def _calculate_relevance(self, product, keywords, regex_obj):
        """
        Calculate relevance score for a product against search keywords.

        Scoring:
        - Exact name match: +10
        - Name contains keyword: +5
        - Description match: +3
        - Category match: +4
        - Brand match: +3
        - Rating bonus: +rating value
        """
        score = 0.0
        name_lower = product['product_name'].lower()
        desc_lower = (product.get('description') or '').lower()
        cat_lower = product['category'].lower()
        brand_lower = product['brand'].lower()

        for kw in keywords:
            kw_lower = kw.lower()
            # Exact name match
            if kw_lower == name_lower:
                score += 10.0
            # Name contains keyword
            elif kw_lower in name_lower:
                score += 5.0
            # Category match
            if kw_lower in cat_lower:
                score += 4.0
            # Brand match
            if kw_lower in brand_lower:
                score += 3.0
            # Description match
            if kw_lower in desc_lower:
                score += 3.0

        # Rating bonus
        score += float(product.get('rating', 0))

        return round(score, 2)

    def get_suggestions(self, partial_query):
        """
        Get search suggestions based on partial input.
        Uses regex for prefix/substring matching.
        """
        if not partial_query or len(partial_query) < 2:
            return []

        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            pattern = f"%{partial_query}%"
            cursor.execute("""
                SELECT DISTINCT product_name FROM products
                WHERE product_name LIKE %s
                ORDER BY product_name
                LIMIT 8
            """, (pattern,))
            name_suggestions = [row['product_name'] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT category FROM products
                WHERE category LIKE %s
                ORDER BY category
                LIMIT 4
            """, (pattern,))
            cat_suggestions = [row['category'] for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT brand FROM products
                WHERE brand LIKE %s
                ORDER BY brand
                LIMIT 4
            """, (pattern,))
            brand_suggestions = [row['brand'] for row in cursor.fetchall()]

            return {
                'products': name_suggestions,
                'categories': cat_suggestions,
                'brands': brand_suggestions
            }
        finally:
            cursor.close()
            conn.close()

    def get_popular_searches(self):
        """Get the most popular search queries."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT search_query, COUNT(*) as count
                FROM search_history
                GROUP BY search_query
                ORDER BY count DESC
                LIMIT 10
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    def get_search_history(self, user_id=1):
        """Get search history for a user."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT search_id, search_query, searched_at
                FROM search_history
                WHERE user_id = %s
                ORDER BY searched_at DESC
                LIMIT 50
            """, (user_id,))
            results = cursor.fetchall()
            # Convert datetime to string
            for r in results:
                r['searched_at'] = r['searched_at'].strftime('%Y-%m-%d %H:%M:%S')
            return results
        finally:
            cursor.close()
            conn.close()

    def clear_search_history(self, user_id=1):
        """Clear search history for a user."""
        conn = self._get_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("DELETE FROM search_history WHERE user_id = %s", (user_id,))
            conn.commit()
            return {'status': 'success', 'message': 'Search history cleared.'}
        finally:
            cursor.close()
            conn.close()

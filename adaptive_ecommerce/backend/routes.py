"""
Flask API Routes
=================
All backend API endpoints for the Adaptive E-Commerce application.
Handles product search, recommendations, filtering, ranking,
user activity tracking, and TOC demonstrations.
"""

from flask import Blueprint, request, jsonify, render_template, session
from backend.search_engine import SearchEngine
from backend.recommendation_engine import RecommendationEngine
from backend.ranking_engine import RankingEngine
from backend.features_service import FeaturesService
from backend.cfg_parser import parse_natural_language_query
from backend import search_intent
from backend import typo_corrector
from backend import filter_advisor
from backend.automata import (
    DFA, NFA, SearchAutomaton, RegexMatcher,
    DFADemoBuilder, NFADemoBuilder, run_search_demo
)

api = Blueprint('api', __name__)

# Engine instances will be initialized in init_engines()
search_engine = None
recommendation_engine = None
ranking_engine = None
features_service = None
db_config = None


def init_engines(config):
    """Initialize the engine instances with database config."""
    global search_engine, recommendation_engine, ranking_engine, features_service, db_config
    db_config = {
        'host': config.MYSQL_HOST,
        'user': config.MYSQL_USER,
        'password': config.MYSQL_PASSWORD,
        'database': config.MYSQL_DATABASE,
        'port': config.MYSQL_PORT
    }
    search_engine = SearchEngine(db_config)
    recommendation_engine = RecommendationEngine(db_config)
    ranking_engine = RankingEngine(db_config)
    features_service = FeaturesService(db_config)


# ============================================================
# PAGE ROUTES
# ============================================================

@api.route('/')
def index():
    return render_template('index.html')

@api.route('/products')
def products_page():
    return render_template('products.html')

@api.route('/product/<int:product_id>')
def product_detail_page(product_id):
    return render_template('product_details.html', product_id=product_id)

@api.route('/recommendations')
def recommendations_page():
    return render_template('recommendations.html')

@api.route('/history')
def history_page():
    return render_template('history.html')

@api.route('/compare')
def compare_page():
    return render_template('compare.html')

@api.route('/wishlist')
def wishlist_page():
    return render_template('wishlist.html')

@api.route('/alerts')
def alerts_page():
    return render_template('alerts.html')

@api.route('/toc-demo')
def toc_demo_page():
    return render_template('toc_demo.html')

@api.route('/about')
def about_page():
    return render_template('about.html')


# ============================================================
# PRODUCT API
# ============================================================

@api.route('/api/products', methods=['GET'])
def get_products():
    """Get all products with optional filters and ranking."""
    try:
        category = request.args.get('category')
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        brand = request.args.get('brand')
        min_rating = request.args.get('min_rating', type=float)
        sort_by = request.args.get('sort_by', 'relevant')
        search_query = request.args.get('q')

        result = ranking_engine.get_filtered_products(
            category=category,
            min_price=min_price,
            max_price=max_price,
            brand=brand,
            min_rating=min_rating,
            sort_by=sort_by,
            search_query=search_query,
            user_id=1
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': [], 'total': 0}), 500


@api.route('/api/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    """Get a single product by ID."""
    try:
        product = ranking_engine.get_product_by_id(product_id)
        if product:
            # Also get similar products
            similar = recommendation_engine.get_similar_products(product_id)
            return jsonify({
                'product': product,
                'similar_products': similar
            })
        return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# SEARCH API
# ============================================================

@api.route('/api/search', methods=['GET', 'POST'])
def search_products():
    """
    Search products using DFA, NFA, and regex.
    Returns matched products and automata execution details.
    Auto-records search intent evolution and provides zero-result typo recovery.
    """
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            query = data.get('query', '').strip()
        else:
            query = request.args.get('q', '').strip()

        if not query:
            return jsonify({
                'query': '',
                'products': [],
                'total': 0,
                'message': 'Please enter a search query.'
            })

        # Session key for intent evolution
        session_key = session.get('session_id', 'user_session_1')

        # 1. Execute search
        result = search_engine.search(query, user_id=1)

        # 2. Record search intent evolution in finite-state model
        try:
            intent_entry = search_intent.record_search(session_key, query)
            result['search_intent'] = intent_entry
        except Exception:
            result['search_intent'] = None

        # 3. If zero results, trigger intelligent typo recovery & alternative suggestions
        if result.get('total', 0) == 0:
            try:
                recovery = typo_corrector.find_corrections(query, db_config)
                result['recovery'] = recovery
                result['has_typos'] = recovery.get('has_typos', False)
                result['suggestions_recovery'] = recovery.get('suggested_queries', [])
                result['partial_matches'] = recovery.get('partial_matches', [])
            except Exception as ex:
                result['recovery_error'] = str(ex)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': [], 'total': 0}), 500


@api.route('/api/search/suggestions', methods=['GET'])
def search_suggestions():
    """Get search suggestions for autocomplete."""
    try:
        query = request.args.get('q', '').strip()
        suggestions = search_engine.get_suggestions(query)
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'products': [], 'categories': [], 'brands': []})


# ============================================================
# CATEGORIES API
# ============================================================

@api.route('/api/categories', methods=['GET'])
def get_categories():
    """Get all categories with product counts."""
    try:
        categories = ranking_engine.get_categories()
        return jsonify({'categories': categories})
    except Exception as e:
        return jsonify({'error': str(e), 'categories': []}), 500


@api.route('/api/brands', methods=['GET'])
def get_brands():
    """Get all unique brands."""
    try:
        brands = ranking_engine.get_brands()
        return jsonify({'brands': brands})
    except Exception as e:
        return jsonify({'error': str(e), 'brands': []}), 500


# ============================================================
# RECOMMENDATION API
# ============================================================

@api.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """Get personalized product recommendations."""
    try:
        limit = request.args.get('limit', 12, type=int)
        result = recommendation_engine.get_recommendations(user_id=1, limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'recommendations': []}), 500


@api.route('/api/recommendations/similar', methods=['GET'])
def get_similar_recommendations():
    """Get recommendations similar to user's expressed interests (same category/brand)."""
    try:
        limit = request.args.get('limit', 8, type=int)
        result = recommendation_engine.get_similar_recommendations(user_id=1, limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500


@api.route('/api/recommendations/discover', methods=['GET'])
def get_discovery_recommendations():
    """Get discovery-based recommendations exploring new/adjacent categories."""
    try:
        limit = request.args.get('limit', 8, type=int)
        result = recommendation_engine.get_discovery_recommendations(user_id=1, limit=limit)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500


@api.route('/api/recently-viewed', methods=['GET'])
def get_recently_viewed():
    """Get recently viewed products."""
    try:
        products = recommendation_engine.get_recently_viewed(user_id=1)
        return jsonify({'products': products})
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500


@api.route('/api/because-you-viewed', methods=['GET'])
def get_because_you_viewed():
    """Get recommendations based on viewed products."""
    try:
        result = recommendation_engine.get_because_you_viewed(user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500


@api.route('/api/trending', methods=['GET'])
def get_trending():
    """Get trending products."""
    try:
        products = recommendation_engine.get_trending_products()
        return jsonify({'products': products})
    except Exception as e:
        return jsonify({'error': str(e), 'products': []}), 500


@api.route('/api/user-preferences', methods=['GET'])
def get_user_preferences():
    """Get user's category preferences."""
    try:
        prefs = recommendation_engine.get_user_preferences(user_id=1)
        return jsonify({'preferences': prefs})
    except Exception as e:
        return jsonify({'error': str(e), 'preferences': []}), 500


@api.route('/api/frequently-searched', methods=['GET'])
def get_frequently_searched():
    """Get frequently searched categories."""
    try:
        cats = recommendation_engine.get_frequently_searched_categories(user_id=1)
        return jsonify({'categories': cats})
    except Exception as e:
        return jsonify({'error': str(e), 'categories': []}), 500


# ============================================================
# USER ACTIVITY API
# ============================================================

@api.route('/api/view-product', methods=['POST'])
def record_view():
    """Record that a user viewed a product."""
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        if not product_id:
            return jsonify({'error': 'product_id required'}), 400

        result = recommendation_engine.record_product_view(user_id=1, product_id=product_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# SEARCH HISTORY API
# ============================================================

@api.route('/api/history', methods=['GET'])
def get_history():
    """Get user's search history."""
    try:
        history = search_engine.get_search_history(user_id=1)
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e), 'history': []}), 500


@api.route('/api/popular-searches', methods=['GET'])
def get_popular_searches():
    """Get popular search queries."""
    try:
        searches = search_engine.get_popular_searches()
        return jsonify({'searches': searches})
    except Exception as e:
        return jsonify({'error': str(e), 'searches': []}), 500


@api.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear user's search history."""
    try:
        result = search_engine.clear_search_history(user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# TOC DEMONSTRATION API
# ============================================================

@api.route('/api/demo/dfa', methods=['POST'])
def demo_dfa():
    """
    Run DFA demonstration.
    Accepts a pattern and an input string, builds a DFA, and processes the input.
    """
    try:
        data = request.get_json() or {}
        pattern = data.get('pattern', '').strip()
        input_string = data.get('input_string', '').strip()
        demo_type = data.get('demo_type', 'pattern')  # 'pattern', 'email', 'product_code'

        if not input_string:
            return jsonify({'error': 'Input string is required.'}), 400

        if demo_type == 'email':
            dfa = DFADemoBuilder.build_email_validator()
            result = dfa.process(input_string)
            result['demo_type'] = 'Email Validator DFA'
            result['description'] = 'Validates basic email format: username@domain.tld'
        elif demo_type == 'product_code':
            dfa = DFADemoBuilder.build_product_code_validator()
            result = dfa.process(input_string)
            result['demo_type'] = 'Product Code Validator DFA'
            result['description'] = 'Validates product codes: 2+ letters followed by 2-4 digits'
        else:
            if not pattern:
                return jsonify({'error': 'Pattern is required for pattern matching DFA.'}), 400
            dfa = SearchAutomaton.build_dfa_for_pattern(pattern)
            if dfa is None:
                return jsonify({'error': 'Could not build DFA for the given pattern.'}), 400
            result = dfa.process(input_string)
            result['demo_type'] = 'Pattern Matching DFA'
            result['description'] = f'Checks if input contains the pattern "{pattern}"'

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/demo/nfa', methods=['POST'])
def demo_nfa():
    """
    Run NFA demonstration.
    Accepts patterns and an input string, builds an NFA, and processes.
    """
    try:
        data = request.get_json() or {}
        patterns = data.get('patterns', [])
        input_string = data.get('input_string', '').strip()

        if not input_string:
            return jsonify({'error': 'Input string is required.'}), 400

        if not patterns:
            return jsonify({'error': 'At least one pattern is required.'}), 400

        # Clean patterns
        patterns = [p.strip() for p in patterns if p.strip()]

        # Build NFA
        nfa = SearchAutomaton.build_nfa_for_patterns(patterns)
        if nfa is None:
            return jsonify({'error': 'Could not build NFA.'}), 400

        result = nfa.process(input_string)
        result['patterns'] = patterns
        result['demo_type'] = 'Multi-Pattern NFA'
        result['description'] = f'Recognizes any of: {", ".join(patterns)}'

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/demo/regex', methods=['POST'])
def demo_regex():
    """
    Run regular expression demonstration.
    """
    try:
        data = request.get_json() or {}
        pattern = data.get('pattern', '').strip()
        test_input = data.get('input_string', '').strip()

        if not pattern:
            return jsonify({'error': 'Regex pattern is required.'}), 400
        if not test_input:
            return jsonify({'error': 'Test input is required.'}), 400

        result = RegexMatcher.match(pattern, test_input)
        result['demo_type'] = 'Regular Expression Matching'
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/demo/search-pattern', methods=['POST'])
def demo_search_pattern():
    """
    Demonstrate how search query is compared against product database.
    Shows DFA, NFA, and regex matching steps.
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()

        if not query:
            return jsonify({'error': 'Search query is required.'}), 400

        from backend.database import DatabaseManager
        conn = DatabaseManager.get_connection(db_config)
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT product_name FROM products")
        product_names = [row['product_name'] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        result = run_search_demo(query, product_names)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# NATURAL LANGUAGE SEARCH & CFG API
# ============================================================

@api.route('/api/search/natural', methods=['POST'])
def natural_language_search():
    """
    Parses a natural-language query using Context-Free Grammar (CFG),
    extracts structured conditions, and returns matching products.
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()

        if not query:
            return jsonify({'error': 'Please enter a natural language query.'}), 400

        # Step 1: Parse query via CFG
        parse_result = parse_natural_language_query(query)

        if not parse_result['success']:
            return jsonify({
                'success': False,
                'error': parse_result.get('error', 'Could not parse query.'),
                'query': query,
                'tokens': parse_result.get('tokens', []),
                'grammar_rules': parse_result.get('grammar_rules', []),
                'suggested_format': 'Example: "Show laptops under 50000" or "Find Samsung phones between 15000 and 30000"'
            }), 422

        # Step 2: Query DB with extracted conditions
        conditions = parse_result['conditions']
        exec_result = features_service.execute_natural_search(conditions, user_id=1)

        return jsonify({
            'success': True,
            'query': query,
            'parse_result': parse_result,
            'conditions': conditions,
            'products': exec_result['products'],
            'total': exec_result['total']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/demo/cfg', methods=['POST'])
def demo_cfg():
    """
    TOC Academic Demonstration for Context-Free Grammar (CFG).
    Returns tokens, grammar derivation rules, parse tree, conditions,
    and actual matching database products.
    """
    try:
        data = request.get_json() or {}
        query = data.get('query', 'Show laptops under 50000.').strip()

        # Parse with CFG
        parse_result = parse_natural_language_query(query)

        products = []
        if parse_result['success']:
            exec_result = features_service.execute_natural_search(parse_result['conditions'], user_id=1)
            products = exec_result['products']

        return jsonify({
            'query': query,
            'parse_result': parse_result,
            'matching_products': products,
            'total_matches': len(products)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PRODUCT COMPARISON API
# ============================================================

@api.route('/api/compare', methods=['GET'])
def get_comparison_list():
    """Get all products in the user's comparison list (up to 4)."""
    try:
        result = features_service.get_comparison(user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': [], 'count': 0}), 500


@api.route('/api/compare', methods=['POST'])
def add_to_comparison():
    """Add a product to comparison list."""
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        if not product_id:
            return jsonify({'error': 'product_id is required'}), 400

        result = features_service.add_to_comparison(user_id=1, product_id=product_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/compare/<int:product_id>', methods=['DELETE'])
def remove_from_comparison(product_id):
    """Remove a product from comparison list."""
    try:
        result = features_service.remove_from_comparison(user_id=1, product_id=product_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/compare/clear', methods=['DELETE'])
def clear_comparison_list():
    """Clear all products from comparison."""
    try:
        result = features_service.clear_comparison(user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# SMART WISHLIST API
# ============================================================

@api.route('/api/wishlist', methods=['GET'])
def get_wishlist():
    """Get all saved products in the user's wishlist."""
    try:
        result = features_service.get_wishlist(user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'products': [], 'count': 0}), 500


@api.route('/api/wishlist', methods=['POST'])
def add_to_wishlist():
    """Add product to wishlist."""
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        if not product_id:
            return jsonify({'error': 'product_id is required'}), 400

        result = features_service.add_to_wishlist(user_id=1, product_id=product_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/wishlist/<int:product_id>', methods=['DELETE'])
def remove_from_wishlist(product_id):
    """Remove product from wishlist."""
    try:
        result = features_service.remove_from_wishlist(user_id=1, product_id=product_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# PRICE DROP ALERT API
# ============================================================

@api.route('/api/alerts', methods=['GET'])
def get_price_alerts():
    """Get active and triggered price drop alerts."""
    try:
        result = features_service.get_price_alerts(user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'active_alerts': [], 'triggered_alerts': []}), 500


@api.route('/api/alerts', methods=['POST'])
def set_price_alert():
    """Create or update a price alert."""
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        target_price = data.get('target_price')

        if not product_id or target_price is None:
            return jsonify({'error': 'product_id and target_price are required'}), 400

        result = features_service.set_price_alert(user_id=1, product_id=product_id, target_price=target_price)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/alerts/<int:alert_id>', methods=['DELETE'])
def delete_price_alert(alert_id):
    """Delete a price alert."""
    try:
        result = features_service.delete_price_alert(user_id=1, alert_id=alert_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/alerts/simulate-drop', methods=['POST'])
def simulate_price_drop():
    """Demonstration endpoint to test price drop alert trigger."""
    try:
        data = request.get_json() or {}
        product_id = data.get('product_id')
        new_price = data.get('new_price')

        if not product_id or new_price is None:
            return jsonify({'error': 'product_id and new_price are required'}), 400

        result = features_service.simulate_price_drop(product_id=product_id, new_price=new_price)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# EXPLAINABLE AI API
# ============================================================

@api.route('/api/explain/search', methods=['GET'])
def explain_search():
    """Explain why a product matched a search query."""
    try:
        product_id = request.args.get('product_id', type=int)
        query = request.args.get('q', '')

        if not product_id or not query:
            return jsonify({'error': 'product_id and q parameters required'}), 400

        result = features_service.explain_search_match(product_id, query)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/explain/recommendation', methods=['GET'])
def explain_recommendation():
    """Explain why a product was recommended."""
    try:
        product_id = request.args.get('product_id', type=int)
        if not product_id:
            return jsonify({'error': 'product_id parameter required'}), 400

        result = features_service.explain_recommendation(product_id, user_id=1)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# FEATURE 1: SEARCH INTENT EVOLUTION & QUERY REFORMULATION
# ============================================================

@api.route('/api/search-journey', methods=['GET'])
def get_search_journey():
    """Get the current session's search progression and intent states."""
    try:
        session_key = session.get('session_id', 'user_session_1')
        journey_data = search_intent.get_journey(session_key)
        return jsonify(journey_data)
    except Exception as e:
        return jsonify({'error': str(e), 'journey': [], 'current_state': 'INITIAL'}), 500


@api.route('/api/search-journey/record', methods=['POST'])
def record_search_journey():
    """Explicitly record a query in the user's search journey."""
    try:
        data = request.get_json() or {}
        query = data.get('query', '').strip()
        if not query:
            return jsonify({'error': 'Query is required'}), 400

        session_key = session.get('session_id', 'user_session_1')
        entry = search_intent.record_search(session_key, query)
        journey_data = search_intent.get_journey(session_key)
        return jsonify({
            'status': 'success',
            'entry': entry,
            'journey': journey_data['journey'],
            'current_state': journey_data['current_state'],
            'state_description': journey_data['state_description']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/search-journey/suggestions', methods=['GET'])
def get_search_journey_suggestions():
    """Get next suggested queries based on evolving search intent."""
    try:
        session_key = session.get('session_id', 'user_session_1')
        suggestions = search_intent.get_suggestions(session_key, db_config)
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e), 'suggestions': []}), 500


@api.route('/api/search-journey/clear', methods=['POST'])
def clear_search_journey():
    """Reset the current session's search journey."""
    try:
        session_key = session.get('session_id', 'user_session_1')
        res = search_intent.clear_journey(session_key)
        return jsonify(res)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/demo/search-intent', methods=['POST'])
def demo_search_intent():
    """TOC Academic Demonstration for Search Intent FSM."""
    try:
        data = request.get_json() or {}
        queries = data.get('queries', [])
        if not queries:
            queries = [
                'Laptop',
                'Gaming Laptop',
                'Gaming Laptop with 16GB RAM',
                'Gaming Laptop under 60000'
            ]
        demo_data = search_intent.get_demo_data(queries)
        return jsonify(demo_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# FEATURE 2: ZERO-RESULT SEARCH RECOVERY & TYPO CORRECTION
# ============================================================

@api.route('/api/search/recover', methods=['GET', 'POST'])
def recover_search():
    """
    Recover from a failed or misspelled query.
    Calculates Levenshtein edit distance and suggests alternatives.
    """
    try:
        if request.method == 'POST':
            data = request.get_json() or {}
            query = data.get('query', '').strip()
        else:
            query = request.args.get('q', '').strip()

        if not query:
            return jsonify({'error': 'query parameter required'}), 400

        recovery = typo_corrector.find_corrections(query, db_config)
        return jsonify(recovery)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@api.route('/api/demo/typo-correction', methods=['POST'])
def demo_typo_correction():
    """
    TOC Academic Demonstration for Levenshtein Distance.
    Accepts source and target words, computes DP matrix and operations.
    """
    try:
        data = request.get_json() or {}
        source = data.get('source', 'samsng').strip()
        target = data.get('target', 'Samsung').strip()

        demo_data = typo_corrector.get_demo_data(source, target)
        return jsonify(demo_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# FEATURE 3: SESSION-AWARE ADAPTIVE FILTER ADVISOR
# ============================================================

@api.route('/api/filters/suggestions', methods=['GET'])
def get_filter_suggestions():
    """Get dynamic, context-aware filter suggestions for current search/category."""
    try:
        query = request.args.get('q', '')
        applied = {
            'category': request.args.get('category', ''),
            'brand': request.args.get('brand', ''),
            'min_price': request.args.get('min_price', ''),
            'max_price': request.args.get('max_price', ''),
            'min_rating': request.args.get('min_rating', '')
        }
        # Filter out empty entries
        applied = {k: v for k, v in applied.items() if v}

        result = filter_advisor.get_filter_suggestions(query, applied, db_config)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e), 'suggestions': []}), 500


@api.route('/api/demo/filter-advisor', methods=['POST'])
def demo_filter_advisor():
    """TOC Academic Demonstration for Adaptive Filter Automaton."""
    try:
        data = request.get_json() or {}
        category = data.get('category', 'Smartphones')
        applied = data.get('applied_filters', {'category': category})

        demo_data = filter_advisor.get_demo_data(category, applied)
        return jsonify(demo_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

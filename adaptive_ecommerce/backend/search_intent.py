"""
Search Intent Evolution & Query Reformulation Module
=====================================================
Tracks how a user's search intent evolves across consecutive queries
in a session. Uses a finite-state model to represent the search journey
and suggests relevant next queries.

TOC Concepts: Finite-State Model for Search Intent,
              State Transitions, Deterministic Computation on Query Sequences.
"""

import re
from collections import defaultdict

# ============================================================
# IN-MEMORY SESSION STORE
# ============================================================
# Maps session_key → list of search journey entries
_session_journeys = defaultdict(list)


# ============================================================
# KNOWN CATEGORIES, BRANDS, SPECS
# ============================================================
KNOWN_CATEGORIES = {
    'smartphones', 'laptops', 'headphones', 'smartwatches',
    'clothing', 'shoes', 'home appliances', 'accessories',
    'phone', 'laptop', 'watch', 'earphone', 'earbuds',
    'speaker', 'tablet', 'camera', 'tv'
}

KNOWN_BRANDS = {
    'apple', 'samsung', 'google', 'oneplus', 'xiaomi',
    'dell', 'hp', 'lenovo', 'asus', 'sony', 'bose', 'jbl',
    'garmin', 'fitbit', 'nike', 'adidas', 'puma', 'levis',
    'dyson', 'philips', 'irobot', 'anker', 'logitech', 'belkin',
    'new balance', 'under armour', 'instant pot'
}

SPEC_KEYWORDS = {
    'ram', 'gb', 'tb', 'ssd', 'hdd', 'processor', 'chip',
    'camera', 'mp', 'megapixel', 'battery', 'mah', 'display',
    'oled', 'amoled', 'lcd', 'inch', 'hz', 'refresh',
    'noise', 'cancelling', 'wireless', 'bluetooth', 'wifi',
    'waterproof', 'water', 'resistant', 'charging', 'usb',
    'gaming', '5g', '4g', 'gps', 'nfc', 'fingerprint',
    'lightweight', 'portable', 'foldable', 'touchscreen',
    'intel', 'amd', 'snapdragon', 'nvidia', 'rtx', 'i5', 'i7', 'i9',
    'm1', 'm2', 'm3', 'gen'
}

PRICE_PATTERNS = re.compile(
    r'(?:under|below|above|over|less\s+than|more\s+than|between|'
    r'(?:₹|rs\.?|inr)\s*)\s*[\d,]+', re.IGNORECASE
)

# ============================================================
# FINITE-STATE MODEL FOR SEARCH INTENT
# ============================================================

# States
STATES = [
    'INITIAL',          # No search yet
    'EXPLORING',        # Broad, general search
    'CATEGORY_FOCUSED', # User has settled on a category
    'SPEC_REFINING',    # Adding technical specifications
    'PRICE_COMPARING',  # Adding price constraints
    'BRAND_FOCUSED',    # Focusing on a specific brand
    'DECIDED'           # Very specific, narrow search
]

# Transitions are determined by comparing consecutive queries
TRANSITION_TABLE = {
    ('INITIAL', 'broad_search'):       'EXPLORING',
    ('INITIAL', 'category_search'):    'CATEGORY_FOCUSED',
    ('INITIAL', 'spec_search'):        'SPEC_REFINING',
    ('INITIAL', 'price_search'):       'PRICE_COMPARING',
    ('INITIAL', 'brand_search'):       'BRAND_FOCUSED',
    ('EXPLORING', 'narrowing'):        'CATEGORY_FOCUSED',
    ('EXPLORING', 'add_spec'):         'SPEC_REFINING',
    ('EXPLORING', 'add_price'):        'PRICE_COMPARING',
    ('EXPLORING', 'add_brand'):        'BRAND_FOCUSED',
    ('EXPLORING', 'category_change'):  'EXPLORING',
    ('EXPLORING', 'broadening'):       'EXPLORING',
    ('CATEGORY_FOCUSED', 'add_spec'):  'SPEC_REFINING',
    ('CATEGORY_FOCUSED', 'add_price'): 'PRICE_COMPARING',
    ('CATEGORY_FOCUSED', 'add_brand'): 'BRAND_FOCUSED',
    ('CATEGORY_FOCUSED', 'category_change'): 'CATEGORY_FOCUSED',
    ('CATEGORY_FOCUSED', 'broadening'): 'EXPLORING',
    ('CATEGORY_FOCUSED', 'narrowing'):  'SPEC_REFINING',
    ('SPEC_REFINING', 'add_price'):    'DECIDED',
    ('SPEC_REFINING', 'add_brand'):    'DECIDED',
    ('SPEC_REFINING', 'add_spec'):     'SPEC_REFINING',
    ('SPEC_REFINING', 'broadening'):   'CATEGORY_FOCUSED',
    ('SPEC_REFINING', 'category_change'): 'CATEGORY_FOCUSED',
    ('PRICE_COMPARING', 'add_spec'):   'DECIDED',
    ('PRICE_COMPARING', 'add_brand'):  'DECIDED',
    ('PRICE_COMPARING', 'narrowing'):  'DECIDED',
    ('PRICE_COMPARING', 'broadening'): 'EXPLORING',
    ('PRICE_COMPARING', 'category_change'): 'CATEGORY_FOCUSED',
    ('BRAND_FOCUSED', 'add_spec'):     'DECIDED',
    ('BRAND_FOCUSED', 'add_price'):    'DECIDED',
    ('BRAND_FOCUSED', 'narrowing'):    'DECIDED',
    ('BRAND_FOCUSED', 'broadening'):   'EXPLORING',
    ('BRAND_FOCUSED', 'category_change'): 'CATEGORY_FOCUSED',
    ('DECIDED', 'broadening'):         'EXPLORING',
    ('DECIDED', 'category_change'):    'CATEGORY_FOCUSED',
    ('DECIDED', 'add_spec'):           'DECIDED',
    ('DECIDED', 'add_price'):          'DECIDED',
    ('DECIDED', 'add_brand'):          'DECIDED',
}


def _extract_attributes(query):
    """Extract categories, brands, specs, price info from a query."""
    tokens = set(re.findall(r'[a-zA-Z0-9]+', query.lower()))
    words = query.lower()

    categories = tokens & KNOWN_CATEGORIES
    brands = tokens & KNOWN_BRANDS
    # Check multi-word brands
    for b in ['new balance', 'under armour', 'instant pot', 'home appliances']:
        if b in words:
            brands.add(b)
    specs = tokens & SPEC_KEYWORDS
    has_price = bool(PRICE_PATTERNS.search(query)) or bool(tokens & {'under', 'below', 'above', 'over', 'cheap', 'budget', 'expensive', 'premium'})

    # Extract numeric values that might be prices
    numbers = re.findall(r'\d[\d,]*', query)
    price_numbers = []
    for n in numbers:
        val = int(n.replace(',', ''))
        if val >= 500:  # Likely a price in INR
            price_numbers.append(val)
            has_price = True

    return {
        'categories': categories,
        'brands': brands,
        'specs': specs,
        'has_price': has_price,
        'price_values': price_numbers,
        'token_count': len(tokens),
        'raw_tokens': tokens
    }


def _classify_transition(prev_attrs, curr_attrs):
    """
    Compare two consecutive query attribute sets and classify the transition.
    Returns a transition label string.
    """
    prev_cats = prev_attrs['categories']
    curr_cats = curr_attrs['categories']
    prev_brands = prev_attrs['brands']
    curr_brands = curr_attrs['brands']
    prev_specs = prev_attrs['specs']
    curr_specs = curr_attrs['specs']
    prev_price = prev_attrs['has_price']
    curr_price = curr_attrs['has_price']

    # Category changed?
    if curr_cats and prev_cats and curr_cats != prev_cats:
        return 'category_change'

    # New brand added
    new_brands = curr_brands - prev_brands
    if new_brands:
        return 'add_brand'

    # New specs added
    new_specs = curr_specs - prev_specs
    if new_specs:
        return 'add_spec'

    # Price constraint added
    if curr_price and not prev_price:
        return 'add_price'

    # Narrowing: more tokens or attributes
    total_prev = len(prev_cats) + len(prev_brands) + len(prev_specs) + (1 if prev_price else 0)
    total_curr = len(curr_cats) + len(curr_brands) + len(curr_specs) + (1 if curr_price else 0)

    if total_curr > total_prev:
        return 'narrowing'
    elif total_curr < total_prev:
        return 'broadening'

    # Token count comparison
    if curr_attrs['token_count'] > prev_attrs['token_count']:
        return 'narrowing'
    elif curr_attrs['token_count'] < prev_attrs['token_count']:
        return 'broadening'

    return 'narrowing'  # Default: treat as narrowing if same attributes


def _classify_first_query(attrs):
    """Classify the type of the very first query in a session."""
    if attrs['categories'] and attrs['specs']:
        return 'spec_search'
    if attrs['categories'] and attrs['has_price']:
        return 'price_search'
    if attrs['brands']:
        return 'brand_search'
    if attrs['categories']:
        return 'category_search'
    return 'broad_search'


INTENT_DESCRIPTIONS = {
    'broad_search': 'General exploration — broad product discovery',
    'category_search': 'Category-focused browsing',
    'spec_search': 'Technical specification filtering',
    'price_search': 'Price-aware shopping',
    'brand_search': 'Brand-specific browsing',
    'narrowing': 'Narrowing down to specific requirements',
    'broadening': 'Expanding search scope for more options',
    'add_spec': 'Adding technical specification constraints',
    'add_price': 'Adding price range requirements',
    'add_brand': 'Focusing on a specific brand',
    'category_change': 'Switching to a different product category',
}

STATE_DESCRIPTIONS = {
    'INITIAL': 'No searches yet — ready to begin browsing',
    'EXPLORING': 'Broadly exploring products across categories',
    'CATEGORY_FOCUSED': 'Focused on a specific product category',
    'SPEC_REFINING': 'Refining search with technical specifications',
    'PRICE_COMPARING': 'Comparing products within a price range',
    'BRAND_FOCUSED': 'Narrowed down to a preferred brand',
    'DECIDED': 'Highly specific search — close to purchase decision',
}


# ============================================================
# PUBLIC API
# ============================================================

def record_search(session_key, query):
    """
    Record a search query in the session journey.
    Returns the updated journey with intent analysis.
    """
    journey = _session_journeys[session_key]
    attrs = _extract_attributes(query)

    entry = {
        'query': query,
        'attributes': {
            'categories': list(attrs['categories']),
            'brands': list(attrs['brands']),
            'specs': list(attrs['specs']),
            'has_price': attrs['has_price'],
            'price_values': attrs['price_values'],
            'token_count': attrs['token_count'],
        },
        'step_index': len(journey),
    }

    if len(journey) == 0:
        # First query
        transition_type = _classify_first_query(attrs)
        new_state = TRANSITION_TABLE.get(('INITIAL', transition_type), 'EXPLORING')
        entry['previous_state'] = 'INITIAL'
        entry['transition'] = transition_type
        entry['current_state'] = new_state
    else:
        prev_entry = journey[-1]
        prev_attrs = _extract_attributes(prev_entry['query'])
        transition_type = _classify_transition(prev_attrs, attrs)
        prev_state = prev_entry['current_state']
        new_state = TRANSITION_TABLE.get(
            (prev_state, transition_type),
            prev_state  # Stay in same state if no transition defined
        )
        entry['previous_state'] = prev_state
        entry['transition'] = transition_type
        entry['current_state'] = new_state

    entry['transition_description'] = INTENT_DESCRIPTIONS.get(transition_type, transition_type)
    entry['state_description'] = STATE_DESCRIPTIONS.get(new_state, new_state)

    journey.append(entry)
    return entry


def get_journey(session_key):
    """Get the full search journey for a session."""
    journey = _session_journeys.get(session_key, [])
    current_state = journey[-1]['current_state'] if journey else 'INITIAL'
    return {
        'journey': journey,
        'current_state': current_state,
        'state_description': STATE_DESCRIPTIONS.get(current_state, ''),
        'total_searches': len(journey),
        'states_visited': list(dict.fromkeys(
            [e['current_state'] for e in journey]
        )),
        'fsm_definition': {
            'states': STATES,
            'initial_state': 'INITIAL',
            'transitions': [
                {'from': k[0], 'input': k[1], 'to': v}
                for k, v in TRANSITION_TABLE.items()
            ],
            'state_descriptions': STATE_DESCRIPTIONS,
        }
    }


def get_suggestions(session_key, db_config):
    """
    Generate suggested next queries based on the current search journey state
    and actual product data in the database.
    """
    from backend.database import DatabaseManager

    journey = _session_journeys.get(session_key, [])
    suggestions = []

    if not journey:
        return {
            'suggestions': [
                {'query': 'Laptops', 'reason': 'Browse popular category'},
                {'query': 'Samsung smartphones', 'reason': 'Explore brand + category'},
                {'query': 'Headphones under 10000', 'reason': 'Price-focused search'},
                {'query': 'Gaming laptop with RTX', 'reason': 'Specification-based search'},
            ]
        }

    latest = journey[-1]
    current_state = latest['current_state']
    attrs = latest['attributes']
    current_query = latest['query'].lower()

    conn = DatabaseManager.get_connection(db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        # Get available categories, brands
        cursor.execute("SELECT DISTINCT category FROM products")
        all_categories = [r['category'] for r in cursor.fetchall()]

        cursor.execute("SELECT DISTINCT brand FROM products")
        all_brands = [r['brand'] for r in cursor.fetchall()]

        # Get price range
        cursor.execute("SELECT MIN(price) as min_p, MAX(price) as max_p FROM products")
        price_range = cursor.fetchone()

        if current_state == 'EXPLORING':
            # Suggest narrowing by category
            for cat in all_categories[:4]:
                if cat.lower() not in current_query:
                    suggestions.append({
                        'query': cat,
                        'reason': f'Explore {cat} category'
                    })
            # Suggest adding a brand
            for brand in all_brands[:3]:
                if brand.lower() not in current_query:
                    suggestions.append({
                        'query': f'{brand} products',
                        'reason': f'Focus on {brand} brand'
                    })

        elif current_state == 'CATEGORY_FOCUSED':
            cat = attrs['categories'][0] if attrs['categories'] else ''
            # Suggest adding specs
            suggestions.append({
                'query': f'{current_query} with high rating',
                'reason': 'Filter by top-rated products'
            })
            suggestions.append({
                'query': f'{current_query} under 50000',
                'reason': 'Add budget constraint'
            })
            # Suggest brands in that category
            if cat:
                cursor.execute(
                    "SELECT DISTINCT brand FROM products WHERE LOWER(category) = %s LIMIT 3",
                    (cat,)
                )
                cat_brands = [r['brand'] for r in cursor.fetchall()]
                for b in cat_brands:
                    if b.lower() not in current_query:
                        suggestions.append({
                            'query': f'{b} {cat}',
                            'reason': f'Explore {b} in {cat}'
                        })

        elif current_state == 'SPEC_REFINING':
            suggestions.append({
                'query': f'{current_query} under 50000',
                'reason': 'Add price limit to narrow results'
            })
            suggestions.append({
                'query': f'{current_query} premium',
                'reason': 'Focus on premium segment'
            })

        elif current_state == 'PRICE_COMPARING':
            suggestions.append({
                'query': f'{current_query} with best rating',
                'reason': 'Compare by rating within budget'
            })
            # Suggest different price ranges
            if attrs['price_values']:
                price = attrs['price_values'][0]
                suggestions.append({
                    'query': current_query.replace(str(price), str(int(price * 1.5))),
                    'reason': 'Increase budget for more options'
                })

        elif current_state == 'BRAND_FOCUSED':
            brand = list(attrs['brands'])[0] if attrs['brands'] else ''
            if brand:
                cursor.execute(
                    "SELECT DISTINCT category FROM products WHERE LOWER(brand) = %s",
                    (brand.lower(),)
                )
                brand_cats = [r['category'] for r in cursor.fetchall()]
                for c in brand_cats:
                    if c.lower() not in current_query:
                        suggestions.append({
                            'query': f'{brand} {c.lower()}',
                            'reason': f'View {brand} in {c}'
                        })
            suggestions.append({
                'query': f'{current_query} under 100000',
                'reason': 'Add budget constraint'
            })

        elif current_state == 'DECIDED':
            suggestions.append({
                'query': attrs['categories'][0] if attrs['categories'] else 'products',
                'reason': 'Broaden search — explore more options'
            })
            suggestions.append({
                'query': 'trending products',
                'reason': 'See what others are buying'
            })

        # Always suggest exploring a different category
        explored_cats = set()
        for e in journey:
            explored_cats.update(e['attributes']['categories'])
        unexplored = [c for c in all_categories if c.lower() not in explored_cats]
        if unexplored:
            suggestions.append({
                'query': unexplored[0],
                'reason': f'Discover {unexplored[0]} — a new category for you'
            })

    except Exception as e:
        suggestions = [{'query': 'laptops', 'reason': f'Suggestion error: {str(e)}'}]
    finally:
        cursor.close()
        conn.close()

    # Deduplicate and limit
    seen = set()
    unique = []
    for s in suggestions:
        key = s['query'].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(s)
    return {'suggestions': unique[:6]}


def clear_journey(session_key):
    """Clear the search journey for a session."""
    _session_journeys.pop(session_key, None)
    return {'status': 'success', 'message': 'Search journey cleared.'}


def get_demo_data(queries):
    """
    Run a demo of the search intent evolution for a list of queries.
    Returns full journey data for TOC demonstration.
    """
    demo_key = '__demo__'
    _session_journeys.pop(demo_key, None)

    for q in queries:
        record_search(demo_key, q)

    result = get_journey(demo_key)
    _session_journeys.pop(demo_key, None)
    return result

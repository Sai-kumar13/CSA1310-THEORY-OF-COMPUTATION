"""
Session-Aware Adaptive Filter Advisor Module
==============================================
Suggests the most useful filters based on the current search context,
browsed category, and already-applied filters.

TOC Concepts: State-based filter selection automaton,
              Context-dependent transitions, Attribute extraction.
"""

import re
from collections import Counter
from backend.database import DatabaseManager


# ============================================================
# CATEGORY-TO-ATTRIBUTE MAPPINGS
# ============================================================

CATEGORY_ATTRIBUTES = {
    'Smartphones': {
        'primary_specs': ['RAM', 'Storage', 'Camera', 'Battery', 'Processor', '5G'],
        'filter_keywords': {
            'RAM': ['4gb', '6gb', '8gb', '12gb', '16gb', 'ram'],
            'Camera': ['48mp', '50mp', '64mp', '108mp', '200mp', 'camera', 'megapixel'],
            'Battery': ['4000mah', '5000mah', 'battery', 'charging', 'fast charge'],
            'Display': ['amoled', 'oled', 'lcd', 'ips', '120hz', '90hz', 'display'],
            'Processor': ['snapdragon', 'dimensity', 'exynos', 'bionic', 'tensor', 'chip'],
            'Connectivity': ['5g', '4g', 'wifi', 'bluetooth', 'nfc', 'usb-c'],
        }
    },
    'Laptops': {
        'primary_specs': ['Processor', 'RAM', 'Storage', 'GPU', 'Display', 'Battery Life'],
        'filter_keywords': {
            'Processor': ['i5', 'i7', 'i9', 'm1', 'm2', 'm3', 'ryzen', 'intel', 'amd', 'core'],
            'RAM': ['8gb', '16gb', '32gb', '64gb', 'ram'],
            'Storage': ['256gb', '512gb', '1tb', '2tb', 'ssd', 'hdd'],
            'GPU': ['rtx', 'nvidia', 'gtx', 'radeon', 'gpu', 'graphics'],
            'Display': ['oled', 'ips', '4k', '2k', 'fhd', '14inch', '15inch', '16inch', 'touchscreen'],
            'Usage': ['gaming', 'business', 'creative', 'ultrabook', 'convertible', '2-in-1'],
        }
    },
    'Headphones': {
        'primary_specs': ['Type', 'Noise Cancellation', 'Battery', 'Connectivity'],
        'filter_keywords': {
            'Type': ['over-ear', 'on-ear', 'in-ear', 'earbuds', 'tws', 'wired', 'wireless'],
            'Noise Cancellation': ['anc', 'noise cancelling', 'noise cancellation', 'active'],
            'Battery': ['battery', 'hours', 'playtime', 'charging'],
            'Sound': ['bass', 'spatial', 'dolby', 'hi-res', 'lossless'],
            'Connectivity': ['bluetooth', 'wireless', 'wired', '3.5mm', 'usb-c'],
        }
    },
    'Smartwatches': {
        'primary_specs': ['Health Tracking', 'GPS', 'Battery Life', 'Display'],
        'filter_keywords': {
            'Health': ['heart rate', 'ecg', 'spo2', 'blood oxygen', 'sleep', 'fitness'],
            'GPS': ['gps', 'navigation', 'dual-frequency'],
            'Battery': ['battery', 'days', 'solar', 'charging'],
            'Display': ['amoled', 'oled', 'always-on', 'touch'],
            'Durability': ['waterproof', 'water resistant', 'titanium', 'rugged', 'military'],
        }
    },
    'Clothing': {
        'primary_specs': ['Material', 'Fit', 'Style', 'Activity'],
        'filter_keywords': {
            'Material': ['cotton', 'polyester', 'dri-fit', 'fleece', 'mesh', 'recycled'],
            'Fit': ['slim', 'regular', 'loose', 'athletic', 'relaxed'],
            'Style': ['casual', 'sport', 'formal', 'streetwear'],
            'Activity': ['running', 'training', 'outdoor', 'gym', 'hiking'],
        }
    },
    'Shoes': {
        'primary_specs': ['Type', 'Cushioning', 'Activity', 'Material'],
        'filter_keywords': {
            'Type': ['running', 'sneaker', 'casual', 'sport', 'lifestyle', 'training'],
            'Cushioning': ['air max', 'boost', 'foam', 'gel', 'encap', 'midsole'],
            'Material': ['mesh', 'knit', 'leather', 'synthetic', 'primeknit'],
            'Activity': ['running', 'walking', 'gym', 'casual', 'outdoor'],
        }
    },
    'Home Appliances': {
        'primary_specs': ['Type', 'Power', 'Smart Features', 'Capacity'],
        'filter_keywords': {
            'Type': ['vacuum', 'air fryer', 'pressure cooker', 'robot', 'blender'],
            'Smart': ['smart', 'wifi', 'app', 'voice', 'alexa', 'google'],
            'Power': ['watt', 'cordless', 'battery', 'runtime'],
            'Features': ['self-emptying', 'laser', 'sensor', 'digital', 'programmable'],
        }
    },
    'Accessories': {
        'primary_specs': ['Type', 'Compatibility', 'Capacity', 'Connectivity'],
        'filter_keywords': {
            'Type': ['charger', 'cable', 'mouse', 'keyboard', 'stand', 'case', 'power bank', 'ssd'],
            'Compatibility': ['iphone', 'android', 'universal', 'usb-c', 'lightning', 'windows', 'mac'],
            'Speed': ['fast', 'quick', 'rapid', 'mbps', 'gbps'],
            'Capacity': ['mah', 'gb', 'tb', 'watt'],
        }
    }
}

# Filter states for the adaptive filter automaton
FILTER_STATES = [
    'NO_FILTERS',       # No filters applied yet
    'CATEGORY_SET',     # Category filter is set
    'PRICE_SET',        # Price range is set
    'BRAND_SET',        # Brand filter is set
    'RATING_SET',       # Rating filter is set
    'MULTI_FILTER',     # Multiple filters applied
    'FULLY_FILTERED',   # 3+ filters applied
]


def get_filter_suggestions(query, applied_filters, db_config):
    """
    Get intelligent filter suggestions based on query context and applied filters.

    Args:
        query: Current search query string.
        applied_filters: Dict of already-applied filters
                        (e.g. {'category': 'Laptops', 'brand': 'Dell'}).
        db_config: Database configuration dict.

    Returns:
        dict with suggested filters, rationale, and filter automaton state.
    """
    conn = DatabaseManager.get_connection(db_config)
    cursor = conn.cursor(dictionary=True)

    try:
        query_lower = (query or '').lower()
        applied = applied_filters or {}

        # Determine current filter state
        filter_count = sum(1 for v in applied.values() if v)
        if filter_count == 0:
            current_state = 'NO_FILTERS'
        elif filter_count == 1:
            if applied.get('category'):
                current_state = 'CATEGORY_SET'
            elif applied.get('brand'):
                current_state = 'BRAND_SET'
            elif applied.get('min_price') or applied.get('max_price'):
                current_state = 'PRICE_SET'
            elif applied.get('min_rating'):
                current_state = 'RATING_SET'
            else:
                current_state = 'CATEGORY_SET'
        elif filter_count == 2:
            current_state = 'MULTI_FILTER'
        else:
            current_state = 'FULLY_FILTERED'

        suggestions = []
        active_category = applied.get('category', '')

        # Detect category from query if not in filters
        if not active_category:
            for cat_name in CATEGORY_ATTRIBUTES:
                if cat_name.lower() in query_lower:
                    active_category = cat_name
                    break
            # Try partial matches
            if not active_category:
                cat_keywords = {
                    'phone': 'Smartphones', 'mobile': 'Smartphones', 'smartphone': 'Smartphones',
                    'laptop': 'Laptops', 'notebook': 'Laptops', 'computer': 'Laptops',
                    'headphone': 'Headphones', 'earphone': 'Headphones', 'earbuds': 'Headphones',
                    'watch': 'Smartwatches', 'smartwatch': 'Smartwatches',
                    'cloth': 'Clothing', 'shirt': 'Clothing', 'jacket': 'Clothing', 'jeans': 'Clothing',
                    'shoe': 'Shoes', 'sneaker': 'Shoes', 'running': 'Shoes',
                    'vacuum': 'Home Appliances', 'fryer': 'Home Appliances', 'cooker': 'Home Appliances',
                    'charger': 'Accessories', 'mouse': 'Accessories', 'ssd': 'Accessories',
                }
                for kw, cat in cat_keywords.items():
                    if kw in query_lower:
                        active_category = cat
                        break

        # --- Suggest category filter if not set ---
        if not applied.get('category'):
            cursor.execute("""
                SELECT category, COUNT(*) as cnt FROM products
                GROUP BY category ORDER BY cnt DESC
            """)
            categories = cursor.fetchall()
            suggestions.append({
                'filter_type': 'category',
                'label': 'Product Category',
                'icon': '📁',
                'reason': 'Filter by category to narrow results',
                'options': [{'value': c['category'], 'count': c['cnt']} for c in categories],
                'priority': 10 if not active_category else 5,
            })

        # --- Suggest brand filter if not set ---
        if not applied.get('brand'):
            brand_query = "SELECT brand, COUNT(*) as cnt FROM products"
            brand_params = []
            if active_category:
                brand_query += " WHERE category = %s"
                brand_params.append(active_category)
            brand_query += " GROUP BY brand ORDER BY cnt DESC LIMIT 10"
            cursor.execute(brand_query, tuple(brand_params))
            brands = cursor.fetchall()
            if brands:
                suggestions.append({
                    'filter_type': 'brand',
                    'label': 'Brand',
                    'icon': '🏷️',
                    'reason': f'Filter by brand{" in " + active_category if active_category else ""}',
                    'options': [{'value': b['brand'], 'count': b['cnt']} for b in brands],
                    'priority': 8,
                })

        # --- Suggest price range if not set ---
        if not applied.get('min_price') and not applied.get('max_price'):
            price_query = "SELECT MIN(price) as min_p, MAX(price) as max_p, AVG(price) as avg_p FROM products"
            price_params = []
            if active_category:
                price_query += " WHERE category = %s"
                price_params.append(active_category)
            cursor.execute(price_query, tuple(price_params))
            pr = cursor.fetchone()
            if pr and pr['min_p'] is not None:
                min_p = float(pr['min_p'])
                max_p = float(pr['max_p'])
                avg_p = float(pr['avg_p'])
                # Create smart price buckets
                buckets = []
                if max_p > 10000:
                    buckets.append({'label': 'Under ₹10,000', 'min': 0, 'max': 10000})
                if max_p > 25000:
                    buckets.append({'label': '₹10,000 – ₹25,000', 'min': 10000, 'max': 25000})
                if max_p > 50000:
                    buckets.append({'label': '₹25,000 – ₹50,000', 'min': 25000, 'max': 50000})
                if max_p > 100000:
                    buckets.append({'label': '₹50,000 – ₹1,00,000', 'min': 50000, 'max': 100000})
                if max_p > 100000:
                    buckets.append({'label': 'Above ₹1,00,000', 'min': 100000, 'max': None})
                if not buckets:
                    buckets.append({'label': f'₹{int(min_p):,} – ₹{int(max_p):,}', 'min': min_p, 'max': max_p})

                suggestions.append({
                    'filter_type': 'price_range',
                    'label': 'Price Range',
                    'icon': '💰',
                    'reason': f'Price ranges {"for " + active_category if active_category else "across all products"}',
                    'options': buckets,
                    'price_stats': {
                        'min': round(min_p),
                        'max': round(max_p),
                        'average': round(avg_p),
                    },
                    'priority': 7,
                })

        # --- Suggest rating filter if not set ---
        if not applied.get('min_rating'):
            suggestions.append({
                'filter_type': 'rating',
                'label': 'Minimum Rating',
                'icon': '⭐',
                'reason': 'Filter by customer rating',
                'options': [
                    {'label': '★★★★½ 4.5+', 'value': 4.5},
                    {'label': '★★★★☆ 4.0+', 'value': 4.0},
                    {'label': '★★★½☆ 3.5+', 'value': 3.5},
                ],
                'priority': 6,
            })

        # --- Category-specific spec suggestions ---
        if active_category and active_category in CATEGORY_ATTRIBUTES:
            cat_attrs = CATEGORY_ATTRIBUTES[active_category]
            # Find which spec keywords appear in product descriptions
            desc_query = "SELECT description FROM products WHERE category = %s"
            cursor.execute(desc_query, (active_category,))
            descriptions = [r['description'] or '' for r in cursor.fetchall()]
            combined_desc = ' '.join(descriptions).lower()

            for spec_group, keywords in cat_attrs['filter_keywords'].items():
                # Check if any keyword from this group appears in descriptions
                matched = [kw for kw in keywords if kw in combined_desc]
                already_in_query = any(kw in query_lower for kw in keywords)

                if matched and not already_in_query:
                    suggestions.append({
                        'filter_type': 'spec_keyword',
                        'label': f'{spec_group} Filter',
                        'icon': '🔧',
                        'reason': f'Refine by {spec_group} in {active_category}',
                        'options': [{'value': kw, 'keyword': True} for kw in matched[:5]],
                        'priority': 5,
                    })

        # Sort suggestions by priority (highest first)
        suggestions.sort(key=lambda x: x.get('priority', 0), reverse=True)

        # Build filter state transition info
        transitions = _get_filter_transitions(current_state)

        return {
            'suggestions': suggestions,
            'current_state': current_state,
            'detected_category': active_category,
            'applied_filters': applied,
            'filter_count': filter_count,
            'state_transitions': transitions,
            'automaton': {
                'states': FILTER_STATES,
                'current': current_state,
                'description': _get_state_description(current_state),
            }
        }

    except Exception as e:
        return {
            'suggestions': [],
            'current_state': 'NO_FILTERS',
            'error': str(e)
        }
    finally:
        cursor.close()
        conn.close()


def _get_filter_transitions(current_state):
    """Get possible transitions from the current filter state."""
    transitions = {
        'NO_FILTERS': [
            {'action': 'Set category', 'next_state': 'CATEGORY_SET'},
            {'action': 'Set brand', 'next_state': 'BRAND_SET'},
            {'action': 'Set price range', 'next_state': 'PRICE_SET'},
            {'action': 'Set rating', 'next_state': 'RATING_SET'},
        ],
        'CATEGORY_SET': [
            {'action': 'Add brand', 'next_state': 'MULTI_FILTER'},
            {'action': 'Add price range', 'next_state': 'MULTI_FILTER'},
            {'action': 'Add rating', 'next_state': 'MULTI_FILTER'},
        ],
        'BRAND_SET': [
            {'action': 'Add category', 'next_state': 'MULTI_FILTER'},
            {'action': 'Add price range', 'next_state': 'MULTI_FILTER'},
        ],
        'PRICE_SET': [
            {'action': 'Add category', 'next_state': 'MULTI_FILTER'},
            {'action': 'Add brand', 'next_state': 'MULTI_FILTER'},
        ],
        'RATING_SET': [
            {'action': 'Add category', 'next_state': 'MULTI_FILTER'},
            {'action': 'Add price range', 'next_state': 'MULTI_FILTER'},
        ],
        'MULTI_FILTER': [
            {'action': 'Add another filter', 'next_state': 'FULLY_FILTERED'},
            {'action': 'Reset filters', 'next_state': 'NO_FILTERS'},
        ],
        'FULLY_FILTERED': [
            {'action': 'Reset filters', 'next_state': 'NO_FILTERS'},
            {'action': 'Remove a filter', 'next_state': 'MULTI_FILTER'},
        ],
    }
    return transitions.get(current_state, [])


def _get_state_description(state):
    """Get human-readable description of a filter state."""
    descriptions = {
        'NO_FILTERS': 'No filters applied — showing all products',
        'CATEGORY_SET': 'Category filter active — consider adding brand or price range',
        'BRAND_SET': 'Brand filter active — add category or price range to narrow down',
        'PRICE_SET': 'Price range set — add category or brand to refine',
        'RATING_SET': 'Rating filter active — combine with category for best results',
        'MULTI_FILTER': 'Multiple filters active — results are well-focused',
        'FULLY_FILTERED': 'Fully filtered — very specific results shown',
    }
    return descriptions.get(state, state)


def get_demo_data(category, applied_filters):
    """
    Generate demo data for the TOC adaptive filter demonstration.
    Shows the filter automaton state, transitions, and reasoning.
    """
    filter_count = sum(1 for v in (applied_filters or {}).values() if v)

    all_transitions = []
    for state in FILTER_STATES:
        for t in _get_filter_transitions(state):
            all_transitions.append({
                'from_state': state,
                'action': t['action'],
                'to_state': t['next_state']
            })

    return {
        'category': category,
        'applied_filters': applied_filters,
        'automaton': {
            'states': FILTER_STATES,
            'transitions': all_transitions,
            'state_descriptions': {s: _get_state_description(s) for s in FILTER_STATES},
        },
        'category_attributes': CATEGORY_ATTRIBUTES.get(category, {}),
        'toc_context': {
            'concept': 'Mealy Machine / State-Based Filter Selection Automaton',
            'description': (
                'The filter advisor operates as a Mealy machine where the output '
                '(filter suggestions) depends on both the current state (applied filters) '
                'and the input (search query and product context). State transitions '
                'occur when the user applies or removes filters.'
            ),
        }
    }

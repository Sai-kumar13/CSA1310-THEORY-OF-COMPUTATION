"""
Typo Correction & Zero-Result Search Recovery Module
=====================================================
Detects spelling mistakes, generates alternative search suggestions,
and recovers from zero-result searches using edit distance and
approximate string matching.

TOC Concepts: Levenshtein Edit Distance (string-to-string correction),
              Approximate Pattern Matching via dynamic programming,
              Finite transducers for character transformation.
"""

import re
from backend.database import DatabaseManager


# ============================================================
# LEVENSHTEIN EDIT DISTANCE (Pure Python)
# ============================================================

def levenshtein_distance(s1, s2):
    """
    Compute the Levenshtein edit distance between two strings.
    Uses dynamic programming (Wagner–Fischer algorithm).

    Operations: Insert, Delete, Substitute — each costs 1.

    Returns:
        int: minimum number of single-character edits.
    """
    len_s1, len_s2 = len(s1), len(s2)
    # dp[i][j] = edit distance between s1[:i] and s2[:j]
    dp = [[0] * (len_s2 + 1) for _ in range(len_s1 + 1)]

    for i in range(len_s1 + 1):
        dp[i][0] = i
    for j in range(len_s2 + 1):
        dp[0][j] = j

    for i in range(1, len_s1 + 1):
        for j in range(1, len_s2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],      # deletion
                    dp[i][j - 1],      # insertion
                    dp[i - 1][j - 1]   # substitution
                )
    return dp[len_s1][len_s2]


def levenshtein_matrix(s1, s2):
    """
    Compute the full edit distance matrix for demonstration purposes.
    Returns:
        (distance, matrix, operations)
    """
    len_s1, len_s2 = len(s1), len(s2)
    dp = [[0] * (len_s2 + 1) for _ in range(len_s1 + 1)]

    for i in range(len_s1 + 1):
        dp[i][0] = i
    for j in range(len_s2 + 1):
        dp[0][j] = j

    for i in range(1, len_s1 + 1):
        for j in range(1, len_s2 + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = 1 + min(
                    dp[i - 1][j],
                    dp[i][j - 1],
                    dp[i - 1][j - 1]
                )

    # Backtrace to find operations
    operations = []
    i, j = len_s1, len_s2
    while i > 0 or j > 0:
        if i > 0 and j > 0 and s1[i - 1] == s2[j - 1]:
            operations.append({
                'type': 'match',
                'from_char': s1[i - 1],
                'to_char': s2[j - 1],
                'position': i - 1
            })
            i -= 1
            j -= 1
        elif i > 0 and j > 0 and dp[i][j] == dp[i - 1][j - 1] + 1:
            operations.append({
                'type': 'substitute',
                'from_char': s1[i - 1],
                'to_char': s2[j - 1],
                'position': i - 1
            })
            i -= 1
            j -= 1
        elif j > 0 and dp[i][j] == dp[i][j - 1] + 1:
            operations.append({
                'type': 'insert',
                'to_char': s2[j - 1],
                'position': i
            })
            j -= 1
        elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
            operations.append({
                'type': 'delete',
                'from_char': s1[i - 1],
                'position': i - 1
            })
            i -= 1
        else:
            break

    operations.reverse()

    return dp[len_s1][len_s2], dp, operations


def similarity_score(s1, s2):
    """
    Compute normalized similarity between two strings (0.0 to 1.0).
    1.0 = identical, 0.0 = completely different.
    """
    if not s1 and not s2:
        return 1.0
    max_len = max(len(s1), len(s2))
    if max_len == 0:
        return 1.0
    dist = levenshtein_distance(s1, s2)
    return round(1.0 - (dist / max_len), 3)


# ============================================================
# VOCABULARY BUILDER
# ============================================================

def _build_vocabulary(db_config):
    """
    Build a vocabulary set from all product names, brands, categories
    and their individual words for typo detection.
    """
    conn = DatabaseManager.get_connection(db_config)
    cursor = conn.cursor(dictionary=True)
    vocab = {}

    try:
        cursor.execute("SELECT product_id, product_name, brand, category, description FROM products")
        products = cursor.fetchall()

        for p in products:
            name = p['product_name']
            brand = p['brand']
            category = p['category']
            desc = p.get('description', '') or ''

            # Full names
            vocab[name.lower()] = {
                'original': name, 'type': 'product_name', 'product_id': p['product_id']
            }
            vocab[brand.lower()] = {
                'original': brand, 'type': 'brand', 'product_id': p['product_id']
            }
            vocab[category.lower()] = {
                'original': category, 'type': 'category', 'product_id': p['product_id']
            }

            # Individual words from product names
            for word in re.findall(r'[a-zA-Z]+', name):
                if len(word) >= 3:
                    vocab[word.lower()] = {
                        'original': word, 'type': 'keyword', 'product_id': p['product_id']
                    }

            # Key words from descriptions
            for word in re.findall(r'[a-zA-Z]+', desc):
                if len(word) >= 4:
                    key = word.lower()
                    if key not in vocab:
                        vocab[key] = {
                            'original': word, 'type': 'description_keyword',
                            'product_id': p['product_id']
                        }

        return vocab, products
    finally:
        cursor.close()
        conn.close()


# ============================================================
# TYPO CORRECTION ENGINE
# ============================================================

def find_corrections(query, db_config, max_distance=3, max_suggestions=8):
    """
    Given a search query, find spelling corrections using edit distance.

    Args:
        query: The user's (possibly misspelled) search query.
        db_config: Database configuration dict.
        max_distance: Maximum edit distance to consider.
        max_suggestions: Maximum number of suggestions to return.

    Returns:
        dict with corrections, suggestions, and analysis details.
    """
    vocab, products = _build_vocabulary(db_config)
    query_lower = query.lower().strip()
    tokens = re.findall(r'[a-zA-Z0-9]+', query_lower)

    corrections = []
    token_analysis = []

    for token in tokens:
        if len(token) < 2:
            token_analysis.append({
                'token': token,
                'status': 'skipped',
                'reason': 'Too short'
            })
            continue

        # Check if token exists exactly in vocabulary
        if token in vocab:
            token_analysis.append({
                'token': token,
                'status': 'correct',
                'match': vocab[token]['original'],
                'type': vocab[token]['type']
            })
            continue

        # Find closest matches
        candidates = []
        for vocab_word, info in vocab.items():
            # Quick length filter to avoid computing distance for very different lengths
            if abs(len(vocab_word) - len(token)) > max_distance:
                continue

            dist = levenshtein_distance(token, vocab_word)
            if dist <= max_distance and dist > 0:
                sim = similarity_score(token, vocab_word)
                candidates.append({
                    'original_token': token,
                    'suggestion': info['original'],
                    'vocab_key': vocab_word,
                    'distance': dist,
                    'similarity': sim,
                    'type': info['type']
                })

        # Sort by distance, then similarity
        candidates.sort(key=lambda x: (x['distance'], -x['similarity']))

        if candidates:
            # Remove duplicates (same suggestion text)
            seen = set()
            unique = []
            for c in candidates:
                key = c['suggestion'].lower()
                if key not in seen:
                    seen.add(key)
                    unique.append(c)

            top = unique[:5]
            corrections.extend(top)
            token_analysis.append({
                'token': token,
                'status': 'misspelled',
                'closest_match': top[0]['suggestion'],
                'edit_distance': top[0]['distance'],
                'similarity': top[0]['similarity'],
                'alternatives_count': len(unique)
            })
        else:
            token_analysis.append({
                'token': token,
                'status': 'unknown',
                'reason': 'No close matches found in vocabulary'
            })

    # Build corrected query suggestions
    suggested_queries = _build_suggested_queries(query, tokens, corrections, vocab)

    # Find partial matches from product names
    partial_matches = _find_partial_matches(query_lower, products)

    return {
        'original_query': query,
        'tokens': tokens,
        'token_analysis': token_analysis,
        'corrections': corrections[:max_suggestions],
        'suggested_queries': suggested_queries[:5],
        'partial_matches': partial_matches[:6],
        'has_typos': any(t['status'] == 'misspelled' for t in token_analysis),
        'vocabulary_size': len(vocab)
    }


def _build_suggested_queries(original_query, tokens, corrections, vocab):
    """Build complete corrected query strings from individual token corrections."""
    if not corrections:
        return []

    suggested = []
    query_lower = original_query.lower()

    # Group corrections by original token
    token_corrections = {}
    for c in corrections:
        orig = c['original_token']
        if orig not in token_corrections:
            token_corrections[orig] = []
        token_corrections[orig].append(c)

    # Build corrected queries by replacing each misspelled token with its best correction
    corrected = original_query
    total_distance = 0
    for token, corrs in token_corrections.items():
        best = corrs[0]
        # Case-insensitive replacement
        pattern = re.compile(re.escape(token), re.IGNORECASE)
        corrected = pattern.sub(best['suggestion'], corrected, count=1)
        total_distance += best['distance']

    if corrected.lower() != original_query.lower():
        suggested.append({
            'query': corrected,
            'total_edit_distance': total_distance,
            'corrections_applied': len(token_corrections)
        })

    # Also suggest individual product name corrections
    for c in corrections:
        if c['type'] == 'product_name' and c['similarity'] >= 0.5:
            suggested.append({
                'query': c['suggestion'],
                'total_edit_distance': c['distance'],
                'corrections_applied': 1
            })

    # Also suggest category/brand corrections
    for c in corrections:
        if c['type'] in ('category', 'brand') and c['similarity'] >= 0.5:
            suggested.append({
                'query': c['suggestion'],
                'total_edit_distance': c['distance'],
                'corrections_applied': 1
            })

    # Deduplicate
    seen = set()
    unique = []
    for s in suggested:
        key = s['query'].lower()
        if key not in seen and key != original_query.lower():
            seen.add(key)
            unique.append(s)

    return unique


def _find_partial_matches(query, products):
    """Find products whose names partially match the query using substring."""
    matches = []
    tokens = re.findall(r'[a-zA-Z]+', query.lower())

    for p in products:
        name_lower = p['product_name'].lower()
        desc_lower = (p.get('description', '') or '').lower()
        score = 0

        for token in tokens:
            if len(token) < 3:
                continue
            if token in name_lower:
                score += 5
            elif token in desc_lower:
                score += 2
            elif token in p['brand'].lower():
                score += 3
            elif token in p['category'].lower():
                score += 3

        if score > 0:
            matches.append({
                'product_id': p['product_id'],
                'product_name': p['product_name'],
                'brand': p['brand'],
                'category': p['category'],
                'match_score': score
            })

    matches.sort(key=lambda x: x['match_score'], reverse=True)
    return matches


def get_demo_data(source_word, target_word):
    """
    Generate full edit-distance demonstration data for the TOC demo.
    Shows the DP matrix, operations, and educational annotations.
    """
    distance, matrix, operations = levenshtein_matrix(source_word.lower(), target_word.lower())

    return {
        'source': source_word,
        'target': target_word,
        'distance': distance,
        'similarity': similarity_score(source_word.lower(), target_word.lower()),
        'matrix': matrix,
        'matrix_labels': {
            'rows': [''] + list(source_word.lower()),
            'cols': [''] + list(target_word.lower())
        },
        'operations': operations,
        'operation_summary': {
            'matches': sum(1 for o in operations if o['type'] == 'match'),
            'substitutions': sum(1 for o in operations if o['type'] == 'substitute'),
            'insertions': sum(1 for o in operations if o['type'] == 'insert'),
            'deletions': sum(1 for o in operations if o['type'] == 'delete'),
        },
        'explanation': (
            f'To transform "{source_word}" → "{target_word}", '
            f'{distance} edit operation(s) are needed. '
            f'Similarity: {similarity_score(source_word.lower(), target_word.lower()) * 100:.1f}%.'
        ),
        'toc_context': {
            'concept': 'Levenshtein Edit Distance (Wagner–Fischer Algorithm)',
            'complexity': 'O(m × n) time and space',
            'relation_to_automata': (
                'Edit distance can be computed by a weighted finite-state transducer (FST). '
                'Each cell in the DP matrix corresponds to a state in a 2D finite automaton '
                'that processes both strings simultaneously.'
            ),
        }
    }

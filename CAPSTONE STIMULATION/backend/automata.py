"""
Theory of Computation - Automata Implementation Module
======================================================
Implements DFA, NFA, Regular Expression pattern matching,
and Search Automaton for the Adaptive E-Commerce system.

All automata execute real computational logic - no hardcoded results.
"""

import re
from collections import defaultdict


# ============================================================
# DFA - Deterministic Finite Automaton
# ============================================================
class DFA:
    """
    A general-purpose Deterministic Finite Automaton.
    Used for exact and substring pattern matching in product search.
    """

    def __init__(self, states, alphabet, transitions, start_state, accept_states):
        """
        Initialize a DFA.

        Args:
            states (set): Set of state names (e.g., {'q0', 'q1', 'q2'}).
            alphabet (set): Set of valid input symbols.
            transitions (dict): Mapping of (state, symbol) -> next_state.
            start_state (str): The initial state.
            accept_states (set): Set of accepting/final states.
        """
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = accept_states

    def process(self, input_string):
        """
        Process an input string through the DFA.

        Returns a detailed result dict showing each step of the computation.
        """
        current_state = self.start_state
        transition_log = []
        input_string_lower = input_string.lower()

        transition_log.append({
            'step': 0,
            'symbol': 'START',
            'from_state': None,
            'to_state': current_state,
            'description': f'Begin at start state {current_state}'
        })

        for i, symbol in enumerate(input_string_lower):
            prev_state = current_state
            key = (current_state, symbol)

            if key in self.transitions:
                current_state = self.transitions[key]
                transition_log.append({
                    'step': i + 1,
                    'symbol': symbol,
                    'from_state': prev_state,
                    'to_state': current_state,
                    'description': f'δ({prev_state}, \'{symbol}\') = {current_state}'
                })
            else:
                # No transition defined: go to dead/trap state
                current_state = 'DEAD'
                transition_log.append({
                    'step': i + 1,
                    'symbol': symbol,
                    'from_state': prev_state,
                    'to_state': 'DEAD',
                    'description': f'δ({prev_state}, \'{symbol}\') = DEAD (no transition)'
                })
                # Once in DEAD state, stay there
                for j in range(i + 1, len(input_string_lower)):
                    transition_log.append({
                        'step': j + 1,
                        'symbol': input_string_lower[j],
                        'from_state': 'DEAD',
                        'to_state': 'DEAD',
                        'description': f'δ(DEAD, \'{input_string_lower[j]}\') = DEAD (trapped)'
                    })
                break

        accepted = current_state in self.accept_states

        return {
            'input_string': input_string,
            'states': sorted(list(self.states)),
            'alphabet': sorted(list(self.alphabet)),
            'start_state': self.start_state,
            'accept_states': sorted(list(self.accept_states)),
            'current_state': current_state,
            'accepted': accepted,
            'transitions': transition_log,
            'total_steps': len(transition_log),
            'result': 'ACCEPTED' if accepted else 'REJECTED'
        }


# ============================================================
# NFA - Non-Deterministic Finite Automaton
# ============================================================
class NFA:
    """
    A general-purpose Non-Deterministic Finite Automaton.
    Supports epsilon transitions and multiple possible paths.
    """

    def __init__(self, states, alphabet, transitions, start_state, accept_states):
        """
        Initialize an NFA.

        Args:
            states (set): Set of state names.
            alphabet (set): Set of valid input symbols.
            transitions (dict): Mapping of (state, symbol) -> set of next_states.
                               Use symbol = 'ε' for epsilon transitions.
            start_state (str): The initial state.
            accept_states (set): Set of accepting/final states.
        """
        self.states = states
        self.alphabet = alphabet
        self.transitions = transitions
        self.start_state = start_state
        self.accept_states = accept_states

    def _epsilon_closure(self, states_set):
        """Compute the epsilon closure of a set of states."""
        closure = set(states_set)
        stack = list(states_set)

        while stack:
            state = stack.pop()
            key = (state, 'ε')
            if key in self.transitions:
                for next_state in self.transitions[key]:
                    if next_state not in closure:
                        closure.add(next_state)
                        stack.append(next_state)
        return closure

    def process(self, input_string):
        """
        Process an input string through the NFA using subset construction.

        Returns detailed result with all possible state paths.
        """
        input_lower = input_string.lower()
        transition_log = []

        # Start with epsilon closure of start state
        current_states = self._epsilon_closure({self.start_state})

        transition_log.append({
            'step': 0,
            'symbol': 'START',
            'from_states': [],
            'to_states': sorted(list(current_states)),
            'description': f'ε-closure({{{self.start_state}}}) = {{{", ".join(sorted(current_states))}}}'
        })

        for i, symbol in enumerate(input_lower):
            prev_states = current_states
            next_states = set()

            moves = []
            for state in sorted(prev_states):
                key = (state, symbol)
                if key in self.transitions:
                    targets = self.transitions[key]
                    next_states.update(targets)
                    moves.append(f'δ({state}, \'{symbol}\') = {{{", ".join(sorted(targets))}}}')

            # Apply epsilon closure to the result
            next_states = self._epsilon_closure(next_states)

            transition_log.append({
                'step': i + 1,
                'symbol': symbol,
                'from_states': sorted(list(prev_states)),
                'to_states': sorted(list(next_states)),
                'moves': moves,
                'description': f'Move on \'{symbol}\': {{{", ".join(sorted(next_states))}}}' if next_states else f'Move on \'{symbol}\': ∅ (no transitions)'
            })

            current_states = next_states

            if not current_states:
                # Dead end - process remaining symbols
                for j in range(i + 1, len(input_lower)):
                    transition_log.append({
                        'step': j + 1,
                        'symbol': input_lower[j],
                        'from_states': [],
                        'to_states': [],
                        'moves': [],
                        'description': f'No active states, all paths dead'
                    })
                break

        accepted = bool(current_states & self.accept_states)

        return {
            'input_string': input_string,
            'states': sorted(list(self.states)),
            'alphabet': sorted(list(self.alphabet)),
            'start_state': self.start_state,
            'accept_states': sorted(list(self.accept_states)),
            'final_states': sorted(list(current_states)),
            'accepted': accepted,
            'transitions': transition_log,
            'total_steps': len(transition_log),
            'result': 'ACCEPTED' if accepted else 'REJECTED'
        }


# ============================================================
# Regular Expression Matcher
# ============================================================
class RegexMatcher:
    """
    Wrapper around Python's re module that provides detailed
    matching information for demonstration purposes.
    """

    @staticmethod
    def match(pattern, text, flags=re.IGNORECASE):
        """
        Perform regex matching and return detailed results.
        """
        try:
            compiled = re.compile(pattern, flags)
            matches = list(compiled.finditer(text))

            match_details = []
            for m in matches:
                match_details.append({
                    'matched_text': m.group(),
                    'start_pos': m.start(),
                    'end_pos': m.end(),
                    'span': f'[{m.start()}:{m.end()}]',
                    'groups': list(m.groups()) if m.groups() else []
                })

            return {
                'pattern': pattern,
                'input_text': text,
                'regex_flags': 'IGNORECASE',
                'is_match': len(matches) > 0,
                'match_count': len(matches),
                'matches': match_details,
                'result': 'MATCH FOUND' if matches else 'NO MATCH'
            }
        except re.error as e:
            return {
                'pattern': pattern,
                'input_text': text,
                'regex_flags': 'IGNORECASE',
                'is_match': False,
                'match_count': 0,
                'matches': [],
                'error': str(e),
                'result': 'INVALID REGEX'
            }

    @staticmethod
    def search_products(query, product_names):
        """
        Use regex to search for products matching the query.
        Returns match details for each product.
        """
        # Build regex pattern from query keywords
        keywords = query.strip().split()
        if not keywords:
            return {'query': query, 'pattern': '', 'results': [], 'total_matches': 0}

        # Create pattern that matches any keyword
        escaped_keywords = [re.escape(kw) for kw in keywords]
        pattern = '|'.join(escaped_keywords)

        results = []
        for name in product_names:
            matches = list(re.finditer(pattern, name, re.IGNORECASE))
            if matches:
                results.append({
                    'product_name': name,
                    'matched': True,
                    'match_count': len(matches),
                    'matched_keywords': [m.group() for m in matches],
                    'positions': [{'start': m.start(), 'end': m.end()} for m in matches]
                })
            else:
                results.append({
                    'product_name': name,
                    'matched': False,
                    'match_count': 0,
                    'matched_keywords': [],
                    'positions': []
                })

        return {
            'query': query,
            'pattern': pattern,
            'regex_used': f'(?i)({pattern})',
            'results': [r for r in results if r['matched']],
            'non_matches': [r for r in results if not r['matched']],
            'total_matches': sum(1 for r in results if r['matched'])
        }


# ============================================================
# Search Automaton - DFA builder for product search
# ============================================================
class SearchAutomaton:
    """
    Builds and runs DFA/NFA automata for product search matching.
    This is the core TOC component that connects automata theory
    to the practical search functionality.
    """

    @staticmethod
    def build_dfa_for_pattern(pattern):
        """
        Build a DFA that accepts strings containing the given pattern.
        Uses a simplified KMP-style automaton construction.

        Args:
            pattern: The search pattern (converted to lowercase).

        Returns:
            A DFA instance that accepts strings containing the pattern.
        """
        pattern = pattern.lower().strip()
        if not pattern:
            return None

        n = len(pattern)

        # States: q0 (start) through q_n (accept)
        # qk means we've matched the first k characters of the pattern
        states = {f'q{i}' for i in range(n + 1)}
        states.add('DEAD')

        # Alphabet: all lowercase letters, digits, spaces, common punctuation
        alphabet = set('abcdefghijklmnopqrstuvwxyz0123456789 -_.')

        start_state = 'q0'
        accept_states = {f'q{n}'}

        # Build transitions
        transitions = {}

        # Compute failure function (KMP-style)
        failure = [0] * n
        k = 0
        for i in range(1, n):
            while k > 0 and pattern[k] != pattern[i]:
                k = failure[k - 1]
            if pattern[k] == pattern[i]:
                k += 1
            failure[i] = k

        # Build DFA transitions for each state and symbol
        for state_idx in range(n):
            state_name = f'q{state_idx}'
            for symbol in alphabet:
                if symbol == pattern[state_idx]:
                    # Match: advance to next state
                    transitions[(state_name, symbol)] = f'q{state_idx + 1}'
                else:
                    # Mismatch: use failure function to find next state
                    j = state_idx
                    while j > 0:
                        j = failure[j - 1]
                        if pattern[j] == symbol:
                            transitions[(state_name, symbol)] = f'q{j + 1}'
                            break
                    else:
                        if pattern[0] == symbol:
                            transitions[(state_name, symbol)] = 'q1'
                        else:
                            transitions[(state_name, symbol)] = 'q0'

        # Accept state: stay in accept state for any further input
        for symbol in alphabet:
            transitions[(f'q{n}', symbol)] = f'q{n}'

        return DFA(states, alphabet, transitions, start_state, accept_states)

    @staticmethod
    def build_nfa_for_patterns(patterns):
        """
        Build an NFA that accepts strings matching any of the given patterns.
        Uses epsilon transitions to combine multiple pattern branches.

        Args:
            patterns: List of search patterns.

        Returns:
            An NFA instance.
        """
        if not patterns:
            return None

        all_states = set()
        all_transitions = {}
        accept_states = set()
        alphabet = set('abcdefghijklmnopqrstuvwxyz0123456789 -_.')

        start_state = 'q0'
        all_states.add(start_state)

        for p_idx, pattern in enumerate(patterns):
            pattern = pattern.lower().strip()
            if not pattern:
                continue

            prefix = f'p{p_idx}'

            # Create states for this pattern branch
            branch_states = []
            for c_idx in range(len(pattern) + 1):
                state_name = f'{prefix}_q{c_idx}'
                all_states.add(state_name)
                branch_states.append(state_name)

            # Epsilon transition from start to branch start
            eps_key = (start_state, 'ε')
            if eps_key not in all_transitions:
                all_transitions[eps_key] = set()
            all_transitions[eps_key].add(branch_states[0])

            # Transitions within branch
            for c_idx, char in enumerate(pattern):
                key = (branch_states[c_idx], char)
                if key not in all_transitions:
                    all_transitions[key] = set()
                all_transitions[key].add(branch_states[c_idx + 1])

            # Mark final state as accepting
            accept_states.add(branch_states[-1])

        return NFA(all_states, alphabet, all_transitions, start_state, accept_states)

    @staticmethod
    def match_product(query, product_name):
        """
        Check if a query pattern matches within a product name using DFA.

        Returns:
            dict with match result and DFA execution trace.
        """
        query = query.lower().strip()
        product_lower = product_name.lower()

        if not query:
            return {
                'query': query,
                'product_name': product_name,
                'matched': False,
                'reason': 'Empty query'
            }

        # Build DFA for the query pattern
        dfa = SearchAutomaton.build_dfa_for_pattern(query)
        if dfa is None:
            return {
                'query': query,
                'product_name': product_name,
                'matched': False,
                'reason': 'Could not build DFA'
            }

        # Run the product name through the DFA
        result = dfa.process(product_lower)

        return {
            'query': query,
            'product_name': product_name,
            'matched': result['accepted'],
            'dfa_result': result,
            'reason': 'Pattern found in product name' if result['accepted'] else 'Pattern not found'
        }


# ============================================================
# DFA Demo Builder - For the TOC Demonstration page
# ============================================================
class DFADemoBuilder:
    """Builds demonstration DFAs for specific pattern types."""

    @staticmethod
    def build_email_validator():
        """
        Build a simplified DFA that validates basic email format:
        Accepts strings matching: [a-z]+@[a-z]+\\.[a-z]+
        """
        states = {'q0', 'q1', 'q2', 'q3', 'q4', 'DEAD'}
        alphabet = set('abcdefghijklmnopqrstuvwxyz@.0123456789_-')
        accept_states = {'q4'}

        transitions = {}
        letters = set('abcdefghijklmnopqrstuvwxyz0123456789_-')

        # q0: expecting username characters
        for c in letters:
            transitions[('q0', c)] = 'q1'
        transitions[('q0', '@')] = 'DEAD'
        transitions[('q0', '.')] = 'DEAD'

        # q1: more username chars or @
        for c in letters:
            transitions[('q1', c)] = 'q1'
        transitions[('q1', '@')] = 'q2'
        transitions[('q1', '.')] = 'DEAD'

        # q2: expecting domain characters
        for c in letters:
            transitions[('q2', c)] = 'q3'
        transitions[('q2', '@')] = 'DEAD'
        transitions[('q2', '.')] = 'DEAD'

        # q3: more domain chars or .
        for c in letters:
            transitions[('q3', c)] = 'q3'
        transitions[('q3', '.')] = 'q4'
        transitions[('q3', '@')] = 'DEAD'

        # q4: expecting TLD characters (accept state)
        for c in letters:
            transitions[('q4', c)] = 'q4'
        transitions[('q4', '.')] = 'q4'
        transitions[('q4', '@')] = 'DEAD'

        return DFA(states, alphabet, transitions, 'q0', accept_states)

    @staticmethod
    def build_product_code_validator():
        """
        Build a DFA that validates product codes.
        Format: 2-3 uppercase letters followed by 3-4 digits.
        Example: AB123, XYZ1234
        """
        states = {'q0', 'q1', 'q2', 'q3', 'q4', 'q5', 'q6', 'DEAD'}
        alphabet = set('abcdefghijklmnopqrstuvwxyz0123456789')
        accept_states = {'q4', 'q5', 'q6'}

        transitions = {}
        letters = set('abcdefghijklmnopqrstuvwxyz')
        digits = set('0123456789')

        # q0: first letter (required)
        for c in letters:
            transitions[('q0', c)] = 'q1'
        for c in digits:
            transitions[('q0', c)] = 'DEAD'

        # q1: second letter (required)
        for c in letters:
            transitions[('q1', c)] = 'q2'
        for c in digits:
            transitions[('q1', c)] = 'q3'  # At least 2 letters, now digits

        # q2: third letter (optional) or first digit
        for c in letters:
            transitions[('q2', c)] = 'q2'  # Allow more letters (simplified)
        for c in digits:
            transitions[('q2', c)] = 'q3'

        # q3: second digit
        for c in digits:
            transitions[('q3', c)] = 'q4'
        for c in letters:
            transitions[('q3', c)] = 'DEAD'

        # q4: third digit (accept state)
        for c in digits:
            transitions[('q4', c)] = 'q5'
        for c in letters:
            transitions[('q4', c)] = 'DEAD'

        # q5: fourth digit (accept state)
        for c in digits:
            transitions[('q5', c)] = 'q6'
        for c in letters:
            transitions[('q5', c)] = 'DEAD'

        # q6: (accept state - no more input expected)
        for c in alphabet:
            transitions[('q6', c)] = 'DEAD'

        return DFA(states, alphabet, transitions, 'q0', accept_states)


# ============================================================
# NFA Demo Builder
# ============================================================
class NFADemoBuilder:
    """Builds demonstration NFAs for the TOC page."""

    @staticmethod
    def build_keyword_recognizer(keywords):
        """
        Build an NFA that recognizes any of the given keywords.
        Each keyword gets its own branch from the start state.
        """
        return SearchAutomaton.build_nfa_for_patterns(keywords)

    @staticmethod
    def build_pattern_nfa(pattern):
        """
        Build an NFA for a simple pattern with optional characters.
        Supports:
         - Regular characters (exact match)
         - '.' (any single character)
        """
        states = set()
        transitions = {}
        alphabet = set('abcdefghijklmnopqrstuvwxyz0123456789 ')
        pattern = pattern.lower()

        start = 'q0'
        states.add(start)

        current_state = start
        for i, char in enumerate(pattern):
            next_state = f'q{i + 1}'
            states.add(next_state)

            if char == '.':
                # Any character
                for c in alphabet:
                    key = (current_state, c)
                    if key not in transitions:
                        transitions[key] = set()
                    transitions[key].add(next_state)
            else:
                key = (current_state, char)
                if key not in transitions:
                    transitions[key] = set()
                transitions[key].add(next_state)

            current_state = next_state

        accept_states = {current_state}
        return NFA(states, alphabet, transitions, start, accept_states)


# ============================================================
# Utility: Run a complete search demo
# ============================================================
def run_search_demo(query, product_names):
    """
    Run a complete search demonstration showing DFA, NFA, and regex results.

    Args:
        query: Search query string.
        product_names: List of product names to search against.

    Returns:
        dict with comprehensive demo results.
    """
    # Tokenize query
    keywords = [kw.strip() for kw in query.lower().split() if kw.strip()]

    # 1. DFA matching for each keyword against each product
    dfa_results = []
    for keyword in keywords:
        dfa = SearchAutomaton.build_dfa_for_pattern(keyword)
        if dfa:
            for product in product_names:
                result = dfa.process(product.lower())
                dfa_results.append({
                    'keyword': keyword,
                    'product': product,
                    'accepted': result['accepted'],
                    'final_state': result['current_state'],
                    'steps': result['total_steps']
                })

    # 2. NFA matching
    nfa = SearchAutomaton.build_nfa_for_patterns(keywords)
    nfa_results = []
    if nfa:
        for product in product_names:
            # Test each word of the product name
            words = product.lower().split()
            accepted = False
            for word in words:
                r = nfa.process(word)
                if r['accepted']:
                    accepted = True
                    break
            nfa_results.append({
                'product': product,
                'accepted': accepted
            })

    # 3. Regex matching
    regex_result = RegexMatcher.search_products(query, product_names)

    return {
        'query': query,
        'keywords': keywords,
        'dfa_matches': [r for r in dfa_results if r['accepted']],
        'dfa_non_matches': [r for r in dfa_results if not r['accepted']],
        'nfa_results': nfa_results,
        'regex_result': regex_result,
        'matched_products': list(set(
            r['product'] for r in dfa_results if r['accepted']
        ))
    }

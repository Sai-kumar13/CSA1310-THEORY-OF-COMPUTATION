"""
Natural Language Product Search Using Context-Free Grammar (CFG)
===============================================================
Academic Module for Theory of Computation:
Implements formal CFG Lexer, Parser (Recursive Descent), Parse Tree generator,
and semantic query extractor for e-commerce catalog queries.

Grammar Formalism: G = (V_N, V_T, P, S)
"""

import re


class ParseTreeNode:
    """Represents a node in the formal CFG Parse Tree."""

    def __init__(self, symbol, value=None):
        self.symbol = symbol          # Non-terminal or Terminal name
        self.value = value            # Leaf value / token text
        self.children = []            # Child nodes

    def add_child(self, node):
        if node:
            self.children.append(node)
        return node

    def to_dict(self):
        """Converts parse tree to recursive JSON-serializable dictionary."""
        return {
            'symbol': self.symbol,
            'value': self.value,
            'children': [c.to_dict() for c in self.children]
        }

    def to_text_tree(self, indent="", is_last=True):
        """Generates pretty ASCII / unicode parse tree representation."""
        marker = "└── " if is_last else "├── "
        node_str = f"{self.symbol}"
        if self.value is not None:
            node_str += f": \"{self.value}\""
        lines = [indent + marker + node_str]

        new_indent = indent + ("    " if is_last else "│   ")
        for i, child in enumerate(self.children):
            lines.append(child.to_text_tree(new_indent, i == len(self.children) - 1))
        return "\n".join(lines)


class CFGLexer:
    """Lexical analyzer for natural language product search queries."""

    CATEGORIES = {
        'laptop': 'Laptops', 'laptops': 'Laptops', 'notebook': 'Laptops', 'notebooks': 'Laptops',
        'smartphone': 'Smartphones', 'smartphones': 'Smartphones', 'phone': 'Smartphones', 'phones': 'Smartphones', 'mobile': 'Smartphones', 'mobiles': 'Smartphones',
        'headphone': 'Headphones', 'headphones': 'Headphones', 'earphone': 'Headphones', 'earphones': 'Headphones', 'headset': 'Headphones', 'headsets': 'Headphones',
        'smartwatch': 'Smartwatches', 'smartwatches': 'Smartwatches', 'watch': 'Smartwatches', 'watches': 'Smartwatches',
        'clothing': 'Clothing', 'clothes': 'Clothing', 'shirt': 'Clothing', 'shirts': 'Clothing', 'jeans': 'Clothing', 'jacket': 'Clothing', 'hoodie': 'Clothing',
        'shoe': 'Shoes', 'shoes': 'Shoes', 'sneaker': 'Shoes', 'sneakers': 'Shoes', 'footwear': 'Shoes',
        'appliance': 'Home Appliances', 'appliances': 'Home Appliances', 'home appliance': 'Home Appliances', 'home appliances': 'Home Appliances',
        'vacuum': 'Home Appliances', 'cooker': 'Home Appliances', 'air fryer': 'Home Appliances',
        'accessory': 'Accessories', 'accessories': 'Accessories', 'charger': 'Accessories', 'mouse': 'Accessories', 'ssd': 'Accessories'
    }

    BRANDS = {
        'apple': 'Apple', 'samsung': 'Samsung', 'google': 'Google', 'oneplus': 'OnePlus', 'xiaomi': 'Xiaomi',
        'dell': 'Dell', 'hp': 'HP', 'lenovo': 'Lenovo', 'asus': 'ASUS',
        'sony': 'Sony', 'bose': 'Bose', 'jbl': 'JBL',
        'garmin': 'Garmin', 'fitbit': 'Fitbit',
        'nike': 'Nike', 'levis': 'Levis', "levi's": 'Levis', 'adidas': 'Adidas', 'under armour': 'Under Armour',
        'puma': 'Puma', 'new balance': 'New Balance',
        'dyson': 'Dyson', 'instant pot': 'Instant Pot', 'philips': 'Philips', 'irobot': 'iRobot',
        'anker': 'Anker', 'logitech': 'Logitech', 'belkin': 'Belkin'
    }

    COMMANDS = {'show', 'find', 'search', 'get', 'list', 'display', 'give', 'look', 'fetch'}
    PRICE_LT_OPS = {'under', 'below', 'less', 'cheaper', 'within', 'max', 'upto'}
    PRICE_GT_OPS = {'above', 'over', 'more', 'greater', 'exceeding', 'min'}
    RANGE_OPS = {'between', 'from'}

    def tokenize(self, text):
        # Normalize punctuation: strip trailing periods, question marks, commas
        cleaned = re.sub(r'[\.,!?;:]', ' ', text.lower()).strip()
        words = cleaned.split()
        tokens = []
        i = 0

        while i < len(words):
            word = words[i]

            # Multi-word brand checks
            if i + 1 < len(words):
                two_word = f"{word} {words[i+1]}"
                if two_word in self.BRANDS:
                    tokens.append(('BRAND', self.BRANDS[two_word], two_word))
                    i += 2
                    continue
                if two_word in self.CATEGORIES:
                    tokens.append(('CATEGORY', self.CATEGORIES[two_word], two_word))
                    i += 2
                    continue

            # Command
            if word in self.COMMANDS:
                tokens.append(('COMMAND', word, word))
                i += 1
                continue

            # Category
            if word in self.CATEGORIES:
                tokens.append(('CATEGORY', self.CATEGORIES[word], word))
                i += 1
                continue

            # Brand
            if word in self.BRANDS:
                tokens.append(('BRAND', self.BRANDS[word], word))
                i += 1
                continue

            # Range words (between / from)
            if word in self.RANGE_OPS:
                tokens.append(('RANGE_START', word, word))
                i += 1
                continue

            if word in {'and', 'to'}:
                tokens.append(('AND', word, word))
                i += 1
                continue

            # Comparison operators (less than, more than)
            if word == 'less' and i + 1 < len(words) and words[i+1] == 'than':
                tokens.append(('OP_LT', 'less than', 'less than'))
                i += 2
                continue
            if word in self.PRICE_LT_OPS:
                tokens.append(('OP_LT', word, word))
                i += 1
                continue

            if word == 'more' and i + 1 < len(words) and words[i+1] == 'than':
                tokens.append(('OP_GT', 'more than', 'more than'))
                i += 2
                continue
            if word in self.PRICE_GT_OPS:
                tokens.append(('OP_GT', word, word))
                i += 1
                continue

            # Rating keywords
            if word in {'rating', 'rated', 'stars', 'star'}:
                tokens.append(('RATING_KEY', word, word))
                i += 1
                continue

            # Connectors
            if word in {'with', 'having', 'has'}:
                tokens.append(('WITH', word, word))
                i += 1
                continue

            # Spec keywords
            if word in {'ram', 'rom', 'storage', 'ssd', 'gb', 'tb', 'oled', 'battery', 'mah', 'inch'}:
                tokens.append(('SPEC_KEY', word, word))
                i += 1
                continue

            # Number with optional spec unit attached (e.g. 8gb, 50000, 4.5)
            num_match = re.match(r'^(\d+(?:\.\d+)?)([a-z]*)$', word)
            if num_match:
                val = float(num_match.group(1))
                unit = num_match.group(2)
                tokens.append(('NUMBER', val, word))
                if unit in {'gb', 'tb', 'ram', 'star', 'stars'}:
                    tokens.append(('SPEC_KEY', unit, unit))
                i += 1
                continue

            # Filler / noise words
            if word in {'the', 'a', 'an', 'me', 'all', 'for', 'items', 'products', 'than', 'of', 'in', 'rs', 'inr'}:
                tokens.append(('FILLER', word, word))
                i += 1
                continue

            tokens.append(('WORD', word, word))
            i += 1

        return tokens


class CFGParser:
    """
    Context-Free Grammar Parser for natural language queries.
    Formally derives sentences according to Production Rules P in G = (V_N, V_T, P, S).
    """

    GRAMMAR_RULES = [
        "S -> [Command] Entity [Filters]",
        "Command -> 'show' | 'find' | 'search' | 'get' | 'list' | 'display'",
        "Entity -> Brand Category | Category | Brand",
        "Filters -> Filter Filters | Filter",
        "Filter -> PriceClause | RatingClause | SpecClause",
        "PriceClause -> OpLt Number | OpGt Number | 'between' Number 'and' Number",
        "RatingClause -> ['rating'] [OpGt] Number ['stars'] | OpGt Number 'stars'",
        "SpecClause -> ['with'] [Number] SpecKey"
    ]

    def __init__(self):
        self.lexer = CFGLexer()
        self.tokens = []
        self.pos = 0
        self.applied_rules = []
        self.extracted_conditions = {}

    def parse(self, sentence):
        """
        Parses a natural language query sentence.
        Returns:
            dict containing success status, parse tree, extracted conditions,
            grammar rules used, and tokens.
        """
        raw_tokens = self.lexer.tokenize(sentence)
        self.tokens = [t for t in raw_tokens if t[0] != 'FILLER']
        self.pos = 0
        self.applied_rules = []
        self.extracted_conditions = {
            'category': None,
            'brand': None,
            'min_price': None,
            'max_price': None,
            'min_rating': None,
            'specs': []
        }

        if not self.tokens:
            return {
                'success': False,
                'sentence': sentence,
                'error': 'Query contains no recognizable search keywords.',
                'grammar_rules': self.GRAMMAR_RULES,
                'tokens': [],
                'parse_tree': None,
                'conditions': {}
            }

        try:
            tree = self._parse_S()
            return {
                'success': True,
                'sentence': sentence,
                'tokens': [{'type': t[0], 'value': t[1], 'text': t[2]} for t in self.tokens],
                'grammar_rules': self.applied_rules,
                'parse_tree': tree.to_dict(),
                'text_tree': tree.to_text_tree(),
                'conditions': self.extracted_conditions,
                'all_grammar_rules': self.GRAMMAR_RULES
            }
        except Exception as e:
            return {
                'success': False,
                'sentence': sentence,
                'tokens': [{'type': t[0], 'value': t[1], 'text': t[2]} for t in self.tokens],
                'error': str(e),
                'grammar_rules': self.applied_rules,
                'all_grammar_rules': self.GRAMMAR_RULES,
                'conditions': self.extracted_conditions
            }

    # ================= Recursive Descent Rules =================

    def _cur(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _match(self, token_type):
        tok = self._cur()
        if tok and tok[0] == token_type:
            self.pos += 1
            return tok
        return None

    def _parse_S(self):
        """S -> [Command] Entity [Filters]"""
        self.applied_rules.append("S -> [Command] Entity [Filters]")
        node = ParseTreeNode("S")

        # Optional Command
        if self._cur() and self._cur()[0] == 'COMMAND':
            node.add_child(self._parse_Command())

        # Entity (Category / Brand)
        node.add_child(self._parse_Entity())

        # Optional Filters
        if self.pos < len(self.tokens):
            filters_node = self._parse_Filters()
            if filters_node and filters_node.children:
                node.add_child(filters_node)

        return node

    def _parse_Command(self):
        """Command -> 'show' | 'find' | ..."""
        tok = self._match('COMMAND')
        self.applied_rules.append(f"Command -> '{tok[1]}'")
        return ParseTreeNode("Command", tok[1])

    def _parse_Entity(self):
        """Entity -> Brand Category | Category | Brand"""
        node = ParseTreeNode("Entity")
        tok = self._cur()

        if not tok:
            raise ValueError("Expected category or brand in the query (e.g. laptops, phones, Samsung).")

        # Brand followed by Category
        if tok[0] == 'BRAND':
            brand_tok = self._match('BRAND')
            self.extracted_conditions['brand'] = brand_tok[1]
            node.add_child(ParseTreeNode("Brand", brand_tok[1]))

            if self._cur() and self._cur()[0] == 'CATEGORY':
                cat_tok = self._match('CATEGORY')
                self.extracted_conditions['category'] = cat_tok[1]
                node.add_child(ParseTreeNode("Category", cat_tok[1]))
                self.applied_rules.append(f"Entity -> Brand('{brand_tok[1]}') Category('{cat_tok[1]}')")
            else:
                self.applied_rules.append(f"Entity -> Brand('{brand_tok[1]}')")
            return node

        # Category
        if tok[0] == 'CATEGORY':
            cat_tok = self._match('CATEGORY')
            self.extracted_conditions['category'] = cat_tok[1]
            node.add_child(ParseTreeNode("Category", cat_tok[1]))

            # Category followed by Brand
            if self._cur() and self._cur()[0] == 'BRAND':
                brand_tok = self._match('BRAND')
                self.extracted_conditions['brand'] = brand_tok[1]
                node.add_child(ParseTreeNode("Brand", brand_tok[1]))
                self.applied_rules.append(f"Entity -> Category('{cat_tok[1]}') Brand('{brand_tok[1]}')")
            else:
                self.applied_rules.append(f"Entity -> Category('{cat_tok[1]}')")
            return node

        raise ValueError(f"Unrecognized entity: '{tok[2]}'. Please specify a product category (e.g. laptops, smartphones, shoes) or brand.")

    def _parse_Filters(self):
        """Filters -> Filter Filters | Filter"""
        node = ParseTreeNode("Filters")
        self.applied_rules.append("Filters -> Filter [Filters]")

        while self.pos < len(self.tokens):
            filter_node = self._parse_Filter()
            if filter_node:
                node.add_child(filter_node)
            else:
                self.pos += 1  # Skip unrecognized token to avoid infinite loop

        return node

    def _parse_Filter(self):
        """Filter -> RatingClause | PriceClause | SpecClause"""
        tok = self._cur()
        if not tok:
            return None

        # Check Rating clause first:
        # e.g., 'with rating above 4', 'rating above 4', 'above 4 stars'
        if self._is_rating_clause():
            node = ParseTreeNode("Filter")
            node.add_child(self._parse_RatingClause())
            return node

        # Check Price clause:
        # e.g., 'under 50000', 'between 15000 and 30000', 'below 3000'
        if tok[0] in {'OP_LT', 'OP_GT', 'RANGE_START'}:
            node = ParseTreeNode("Filter")
            node.add_child(self._parse_PriceClause())
            return node

        # Check Spec clause:
        # e.g., 'with 8GB RAM', 'having 16gb'
        if tok[0] in {'WITH', 'SPEC_KEY'} or (tok[0] == 'NUMBER' and self._is_spec_clause()):
            node = ParseTreeNode("Filter")
            node.add_child(self._parse_SpecClause())
            return node

        return None

    def _is_rating_clause(self):
        """Lookahead to determine if current tokens form a rating condition."""
        tok = self._cur()
        if not tok:
            return False

        # If starts with 'with', look ahead
        offset = 1 if tok[0] == 'WITH' else 0
        idx = self.pos + offset

        if idx < len(self.tokens) and self.tokens[idx][0] == 'RATING_KEY':
            return True

        # e.g. 'above 4 stars' -> OP_GT, NUMBER <= 5, RATING_KEY ('stars')
        if idx + 2 < len(self.tokens):
            if (self.tokens[idx][0] in {'OP_GT', 'OP_LT'} and
                self.tokens[idx+1][0] == 'NUMBER' and
                self.tokens[idx+1][1] <= 5.0 and
                self.tokens[idx+2][0] == 'RATING_KEY'):
                return True

        return False

    def _is_spec_clause(self):
        """Lookahead to see if next token is a spec unit."""
        if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1][0] == 'SPEC_KEY':
            return True
        return False

    def _parse_RatingClause(self):
        """RatingClause -> ['with'] ['rating'] [OpGt] Number ['stars']"""
        node = ParseTreeNode("RatingClause")

        if self._cur() and self._cur()[0] == 'WITH':
            self._match('WITH')

        if self._cur() and self._cur()[0] == 'RATING_KEY':
            self._match('RATING_KEY')

        op_name = "above"
        if self._cur() and self._cur()[0] in {'OP_GT', 'OP_LT'}:
            op = self._match(self._cur()[0])
            op_name = op[1]

        num = self._match('NUMBER')
        if num:
            rating_val = min(float(num[1]), 5.0)
            self.extracted_conditions['min_rating'] = rating_val
            self.applied_rules.append(f"RatingClause -> Op('{op_name}') Number({rating_val})")
            node.add_child(ParseTreeNode("RatingOp", op_name))
            node.add_child(ParseTreeNode("MinRating", rating_val))

            if self._cur() and self._cur()[0] == 'RATING_KEY':
                star = self._match('RATING_KEY')
                node.add_child(ParseTreeNode("Unit", star[1]))

            return node

        self.pos += 1
        return None

    def _parse_PriceClause(self):
        """PriceClause -> OpLt Number | OpGt Number | 'between' Number 'and' Number"""
        node = ParseTreeNode("PriceClause")
        tok = self._cur()

        # 'between X and Y'
        if tok[0] == 'RANGE_START':
            self._match('RANGE_START')
            num1 = self._match('NUMBER')
            self._match('AND')
            num2 = self._match('NUMBER')
            if num1 and num2:
                low = min(num1[1], num2[1])
                high = max(num1[1], num2[1])
                self.extracted_conditions['min_price'] = low
                self.extracted_conditions['max_price'] = high
                self.applied_rules.append(f"PriceClause -> 'between' {low} 'and' {high}")
                node.add_child(ParseTreeNode("Range", f"between ₹{int(low):,} and ₹{int(high):,}"))
                return node

        # 'under X' / 'below X'
        if tok[0] == 'OP_LT':
            op = self._match('OP_LT')
            num = self._match('NUMBER')
            if num:
                self.extracted_conditions['max_price'] = num[1]
                self.applied_rules.append(f"PriceClause -> OpLt('{op[1]}') Number(₹{int(num[1]):,})")
                node.add_child(ParseTreeNode("PriceOp", op[1]))
                node.add_child(ParseTreeNode("MaxPrice", f"₹{int(num[1]):,}"))
                return node

        # 'above X' / 'over X'
        if tok[0] == 'OP_GT':
            op = self._match('OP_GT')
            num = self._match('NUMBER')
            if num:
                self.extracted_conditions['min_price'] = num[1]
                self.applied_rules.append(f"PriceClause -> OpGt('{op[1]}') Number(₹{int(num[1]):,})")
                node.add_child(ParseTreeNode("PriceOp", op[1]))
                node.add_child(ParseTreeNode("MinPrice", f"₹{int(num[1]):,}"))
                return node

        self.pos += 1
        return None

    def _parse_SpecClause(self):
        """SpecClause -> ['with'] [Number] SpecKey"""
        node = ParseTreeNode("SpecClause")

        if self._cur() and self._cur()[0] == 'WITH':
            self._match('WITH')

        spec_val = ""
        if self._cur() and self._cur()[0] == 'NUMBER':
            num = self._match('NUMBER')
            spec_val += str(int(num[1]) if num[1].is_integer() else num[1])

        while self._cur() and self._cur()[0] == 'SPEC_KEY':
            k = self._match('SPEC_KEY')
            spec_val += (" " if spec_val else "") + str(k[1])

        if spec_val:
            self.extracted_conditions['specs'].append(spec_val.strip())
            self.applied_rules.append(f"SpecClause -> Spec('{spec_val}')")
            node.add_child(ParseTreeNode("Specification", spec_val))
            return node

        self.pos += 1
        return None


# Global parser instance
cfg_parser_instance = CFGParser()


def parse_natural_language_query(query):
    """Entry point for natural language query parsing."""
    return cfg_parser_instance.parse(query)

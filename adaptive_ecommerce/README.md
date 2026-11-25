# Adaptive E-Commerce Search and Personalized Product Recommendation System
### Subject: Theory of Computation (TOC) Capstone Project

A complete, fully functional, real-time web application titled **AdaptiveShop** demonstrating the practical application of **Deterministic Finite Automata (DFA)**, **Non-Deterministic Finite Automata (NFA)**, **Regular Expressions**, and **State Transition Diagrams** in an e-commerce platform.

---

## 🌟 Features Overview

### Module 1: Adaptive Product Search (Automata-Powered)
- **Tokenization:** Breaks user queries into alphanumeric tokens, removing noise words while keeping key identifiers.
- **DFA Pattern Matching:** Converts search keywords into DFA state transition tables that process product names, descriptions, categories, and brands symbol-by-symbol without external search engines.
- **NFA Multi-Pattern Recognizer:** Executes concurrent pattern matching using subset construction and \(\epsilon\)-closure algorithms.
- **Regular Expressions:** Dynamic Python regex generation for keyword matching and boundary verification.
- **Live Autocomplete Suggestions:** Instant category, brand, and product name suggestions.

### Module 2: Personalized Product Recommendation
- **User Activity Tracking:** Records viewed products and search history asynchronously via Fetch API.
- **Dynamic Category Scoring:** Incrementally updates preference scores for categories and their associated accessory categories.
- **Sections:**
  - *"Recommended For You"* (ranked based on user's category affinity vector and product ratings).
  - *"Because You Viewed These Products"* (cross-recommendations linked to recent views).
  - *"Recently Viewed"* and *"Frequently Searched Categories"*.

### Module 3: Product Ranking & Adaptive Filtering
- **Multi-Filter Support:** Category, Brand, Price Range (min & max), Minimum Star Rating.
- **Sorting Options:** Most Relevant, Price: Low to High, Price: High to Low, Highest Rating.
- **Mathematical Ranking Formula:**
  $$\text{Relevance Score} = (w_1 \times \text{Keyword}) + (w_2 \times \text{Category Pref}) + (w_3 \times \text{Rating}) + (w_4 \times \text{Interaction})$$
  Weights: Keyword Match (3.0), Category Preference (2.5), Rating (2.0), User Interaction (1.5).

### Module 4: Natural Language Search Using Context-Free Grammar (CFG)
- **Chomsky Hierarchy Type 2 Formalism:** Implements formal grammar $G = (V_N, V_T, P, S)$.
- **Recursive-Descent Parser:** Tokenizes free-form user sentences into categories, brands, price comparison operators, rating bounds, and technical specifications.
- **Concrete Parse Tree Generation:** Visualizes derivation trees and applied production rules.
- **Examples:**
  - *"Show laptops under 50000."* $\to$ Category: Laptops, Max Price: ₹50,000.
  - *"Find smartphones with 8GB RAM."* $\to$ Category: Smartphones, Specs: 8GB RAM.
  - *"Show headphones below 3000 with rating above 4."* $\to$ Category: Headphones, Max Price: ₹3,000, Min Rating: 4.0.
  - *"Find Samsung phones between 15000 and 30000."* $\to$ Brand: Samsung, Category: Smartphones, Price: ₹15,000 - ₹30,000.
  - *"Show shoes above 4 stars."* $\to$ Category: Shoes, Min Rating: 4.0.

### Module 5: Product Comparison Workspace (`/compare`)
- Compare up to 4 products side by side in a dedicated comparison table.
- Highlights lowest price with green "Lowest Price" badge and highest rating with gold "Highest Rated" badge.
- Comparison of Product image, Brand, Category, Price, Rating, Specifications, and Live Availability.
- Add, individual remove, and Clear All actions updated dynamically.

### Module 6: Smart Wishlist & Saved Products (`/wishlist`)
- Save favorite items with duplicate entry prevention.
- Persistent storage in database for user session.
- Real-time wishlist item count displayed in navbar badge.
- Instant "Set Price Alert" option directly from saved items.

### Module 7: Price Drop Alert System (`/alerts`)
- Set custom target price in Indian Rupees (₹ INR).
- Active vs. Triggered alert tracking: when product database price drops $\le$ target price, system notifies user with animated navbar alert pill.
- **Evaluation Simulation Panel:** Real-time demonstration control to simulate database price updates and immediately trigger alerts for evaluators.

### Module 8: Explainable Search and Recommendation Results
- "💡 Explain" button on search and recommended product cards.
- **Search Explainability:** Displays matched query tokens, exact name/description/category matches, and scoring metrics.
- **Recommendation Explainability:** Shows user's category affinity scores, recent view history count, and weighting calculation.

### Module 9: Theory of Computation Demonstration Page (`/toc-demo`)
- **DFA Processor:** Interactive state transitions ($\delta$), active state, and accept/reject classification.
- **NFA Processor:** Multi-branch keyword recognition with $\epsilon$-closures.
- **Regular Expressions:** Interactive regex pattern evaluator with highlighted match spans.
- **Catalog Automaton Inspector:** Live catalog verification with automata.
- **Context-Free Grammar Demonstration:** Full sentence derivation with parse tree, production rules, extracted database constraints, and live matching items.

---

## 🛠️ Technology Stack
- **Frontend:** HTML5, CSS3 (Modern Blue/Light-Blue responsive theme), Vanilla JavaScript (ES6+ Fetch API).
- **Backend:** Python 3, Flask framework.
- **Database:** MySQL relational database (`adaptive_ecommerce_db`).
- **TOC Engine:** Pure Python implementation of DFA, NFA, and Regex evaluators (`backend/automata.py`).
- **Database Connector:** `mysql-connector-python`.

---

## 📁 Project Folder Structure

```
adaptive_ecommerce/
├── app.py                      # Main Flask application entry point
├── config.py                   # App configuration and MySQL database settings
├── database.sql                # Complete MySQL schema & 34 sample products
├── requirements.txt            # Python dependencies
├── README.md                   # Project documentation & instructions
├── backend/
│   ├── __init__.py             # Backend package initialization
│   ├── automata.py             # DFA, NFA, and Regex engines
│   ├── cfg_parser.py           # Context-Free Grammar (CFG) engine
│   ├── features_service.py     # Comparison, Wishlist, Alerts, and Explainability
│   ├── search_engine.py        # Module 1: Search engine implementation
│   ├── recommendation_engine.py# Module 2: Recommendation engine implementation
│   ├── ranking_engine.py       # Module 3: Ranking and filtering engine
│   └── routes.py               # Flask REST API endpoints and web routes
└── frontend/
    ├── templates/
    │   ├── base.html           # Master layout with navigation & modals
    │   ├── index.html          # Homepage with natural & keyword search
    │   ├── products.html       # Catalog with sidebar filters & ranking
    │   ├── product_details.html# Single product view & comparison/wishlist actions
    │   ├── compare.html        # Product comparison workspace
    │   ├── wishlist.html       # Smart wishlist & saved products
    │   ├── alerts.html         # Price drop alerts & evaluator simulator
    │   ├── recommendations.html# Personalized recommendations & preferences
    │   ├── history.html        # Search history viewer & cleaner
    │   ├── toc_demo.html       # Interactive TOC Demonstrations (DFA/NFA/Regex/CFG)
    │   └── about.html          # Project overview & theory explanation
    └── static/
        ├── css/
        │   └── style.css       # Clean, modern styling
        └── js/
            ├── main.js         # Core frontend async operations
            └── toc_demo.js     # Automata interactive demonstrations
```

---

## 🚀 Installation & Execution Guide

### Step 1: Open the Project in VS Code
Open VS Code, select **File > Open Folder**, and open the `adaptive_ecommerce` folder.

### Step 2: Install Python Dependencies
Open the integrated terminal in VS Code (`Ctrl + ~`) and execute:
```bash
pip install -r requirements.txt
```

### Step 3: Setup the MySQL Database
1. Ensure your MySQL server (e.g., MySQL Server, XAMPP, WampServer) is running.
2. Log in to MySQL via command line or phpMyAdmin / MySQL Workbench:
   ```bash
   mysql -u root -p
   ```
3. Import the database script:
   ```sql
   SOURCE database.sql;
   ```
   *(Or copy-paste the contents of `database.sql` into MySQL Workbench or phpMyAdmin SQL query window).*

### Step 4: Configure Database Credentials
Check `config.py` (or set environment variables):
```python
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = ''  # Set your MySQL root password if any
MYSQL_DATABASE = 'adaptive_ecommerce_db'
MYSQL_PORT = 3306
```

### Step 5: Start the Application
Run the Flask server:
```bash
python app.py
```
*(Or `py app.py` depending on your Python setup)*

### Step 6: Access the Website
Open your browser and navigate to:
**[http://127.0.0.1:5000/](http://127.0.0.1:5000/)**

---

## 🎓 Academic Demonstration Guide
1. Navigate to **TOC Demonstration** in the top navigation bar.
2. Select **DFA Demonstration**: Enter a target pattern (e.g. `phone`) and input string (e.g. `iPhone 15 Pro`). Click **Execute DFA** to view the active state transitions and accept/reject decision.
3. Select **NFA Demonstration**: Enter multiple branch patterns (e.g. `smart, watch, lap`) and test tokens to see state subsets.
4. Try searching on the **Home** or **All Products** page: Search `"phone"`, `"lap"`, or `"head"` to see real-time DFA and Regex matching in action.
5. Browse products and view their detail pages, then inspect **Recommendations** to verify how category preference scores evolve.

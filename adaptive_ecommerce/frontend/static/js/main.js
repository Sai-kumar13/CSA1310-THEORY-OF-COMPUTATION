/**
 * AdaptiveShop - Main JavaScript
 * Handles all interactive frontend functionality:
 * search, filters, product loading, recommendations, history.
 */

const API = {
    search: '/api/search',
    suggestions: '/api/search/suggestions',
    products: '/api/products',
    product: (id) => `/api/products/${id}`,
    categories: '/api/categories',
    brands: '/api/brands',
    recommendations: '/api/recommendations',
    recentlyViewed: '/api/recently-viewed',
    becauseYouViewed: '/api/because-you-viewed',
    trending: '/api/trending',
    history: '/api/history',
    popularSearches: '/api/popular-searches',
    clearHistory: '/api/clear-history',
    viewProduct: '/api/view-product',
    userPreferences: '/api/user-preferences',
    frequentlySearched: '/api/frequently-searched',
    compare: '/api/compare',
    compareClear: '/api/compare/clear',
    wishlist: '/api/wishlist',
    alerts: '/api/alerts',
    alertSimulateDrop: '/api/alerts/simulate-drop',
    naturalSearch: '/api/search/natural',
    explainSearch: '/api/explain/search',
    explainRec: '/api/explain/recommendation',
    searchJourney: '/api/search-journey',
    searchJourneyRecord: '/api/search-journey/record',
    searchJourneySuggestions: '/api/search-journey/suggestions',
    searchJourneyClear: '/api/search-journey/clear',
    searchRecover: '/api/search/recover',
    filterSuggestions: '/api/filters/suggestions',
    recSimilar: '/api/recommendations/similar',
    recDiscover: '/api/recommendations/discover'
};

let currentSearchMode = 'standard'; // 'standard' or 'natural'
let currentSearchQuery = '';

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

function showLoading(containerId) {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = '<div class="loading"><div class="spinner"></div> Loading...</div>';
}

function showEmpty(containerId, message = 'No items found.', icon = '<i class="fa-solid fa-box-open"></i>') {
    const el = document.getElementById(containerId);
    if (el) el.innerHTML = `<div class="empty-state"><span class="empty-icon">${icon}</span><h3>${message}</h3></div>`;
}

function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

function renderStars(rating) {
    const full = Math.floor(rating);
    const half = rating % 1 >= 0.5 ? 1 : 0;
    const empty = 5 - full - half;
    return '★'.repeat(full) + (half ? '½' : '') + '☆'.repeat(empty);
}

function formatPrice(amount) {
    return '₹' + Math.round(Number(amount)).toLocaleString('en-IN');
}

function createProductCard(product, showRanking = false) {
    const card = document.createElement('div');
    card.className = 'product-card';
    card.onclick = () => window.location.href = `/product/${product.product_id}`;

    let rankingHtml = '';
    if (showRanking && product.ranking_breakdown) {
        const b = product.ranking_breakdown;
        rankingHtml = `
            <div class="ranking-info">
                <span class="score-label">Relevance Score: </span>
                <span class="score-value">${product.ranking_score || 0}</span>
                <div class="ranking-breakdown">
                    <span>Keyword: ${b.keyword_match}</span>
                    <span>Category: ${b.category_preference}</span>
                    <span>Rating: ${b.rating}</span>
                    <span>History: ${b.interaction}</span>
                </div>
            </div>`;
    }

    card.innerHTML = `
        <div class="product-image">
            <img src="${product.image_url || ''}" 
                 alt="${product.product_name}"
                 onerror="this.parentElement.innerHTML='<div style=\\'display:flex;align-items:center;justify-content:center;height:100%;background:#f1f5f9;color:#64748b;font-size:0.85rem;padding:1rem;text-align:center\\'>${product.product_name}</div>'">
        </div>
        <div class="product-info">
            <span class="product-brand">${product.brand}</span>
            <h3 class="product-name">${product.product_name}</h3>
            <div class="product-rating">
                <span class="stars">${renderStars(product.rating)}</span>
                <span class="rating-num">(${product.rating})</span>
            </div>
            <div class="product-price">${formatPrice(product.price)}</div>
            <span class="product-category-tag">${product.category}</span>
            ${rankingHtml}
            <div class="card-actions-bar">
                <button type="button" class="btn-card-action" onclick="addToComparison(event, ${product.product_id})" title="Add up to 4 products to compare">
                    <i class="fa-solid fa-scale-balanced"></i> Compare
                </button>
                <button type="button" class="btn-card-action" onclick="addToWishlist(event, ${product.product_id})" title="Save to wishlist">
                    <i class="fa-regular fa-heart"></i> Save
                </button>
                <button type="button" class="btn-card-action" onclick="openExplainModal(event, ${product.product_id}, '${product.product_name.replace(/'/g, "\\'")}')" title="Recommendation insights">
                    <i class="fa-solid fa-circle-info"></i> Insights
                </button>
            </div>
        </div>
    `;
    return card;
}

function renderProductsGrid(containerId, products, showRanking = false) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!products || products.length === 0) {
        showEmpty(containerId, 'No products found.', '<i class="fa-solid fa-magnifying-glass"></i>');
        return;
    }

    products.forEach(p => container.appendChild(createProductCard(p, showRanking)));
}

function renderProductsScroll(containerId, products) {
    const container = document.getElementById(containerId);
    if (!container) return;
    container.innerHTML = '';

    if (!products || products.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">No products to show yet.</p>';
        return;
    }

    products.forEach(p => container.appendChild(createProductCard(p)));
}


// ============================================================
// SEARCH FUNCTIONALITY
// ============================================================

let searchTimeout = null;

function initSearch() {
    const searchInput = document.getElementById('searchInput');
    const searchBtn = document.getElementById('searchBtn');
    const suggestionsEl = document.getElementById('searchSuggestions');

    if (!searchInput) return;

    // Live suggestions
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        const q = searchInput.value.trim();
        if (q.length < 2) {
            if (suggestionsEl) suggestionsEl.classList.remove('active');
            return;
        }
        searchTimeout = setTimeout(() => fetchSuggestions(q), 300);
    });

    // Search on Enter
    searchInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            performSearch(searchInput.value.trim());
            if (suggestionsEl) suggestionsEl.classList.remove('active');
        }
    });

    // Search button click
    if (searchBtn) {
        searchBtn.addEventListener('click', () => {
            performSearch(searchInput.value.trim());
            if (suggestionsEl) suggestionsEl.classList.remove('active');
        });
    }

    // Hide suggestions on click outside
    document.addEventListener('click', (e) => {
        if (suggestionsEl && !e.target.closest('.search-container-relative')) {
            suggestionsEl.classList.remove('active');
        }
    });
}

async function fetchSuggestions(query) {
    try {
        const res = await fetch(`${API.suggestions}?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        const suggestionsEl = document.getElementById('searchSuggestions');
        if (!suggestionsEl) return;

        let html = '';
        if (data.products) {
            data.products.forEach(name => {
                html += `<div class="suggestion-item" onclick="performSearch('${name.replace(/'/g, "\\'")}')">
                    <span class="icon"><i class="fa-solid fa-magnifying-glass"></i></span> ${name}
                </div>`;
            });
        }
        if (data.categories) {
            data.categories.forEach(cat => {
                html += `<div class="suggestion-item" onclick="performSearch('${cat}')">
                    <span class="icon"><i class="fa-solid fa-layer-group"></i></span> ${cat}
                </div>`;
            });
        }
        if (data.brands) {
            data.brands.forEach(brand => {
                html += `<div class="suggestion-item" onclick="performSearch('${brand}')">
                    <span class="icon"><i class="fa-solid fa-tag"></i></span> ${brand}
                </div>`;
            });
        }

        if (html) {
            suggestionsEl.innerHTML = html;
            suggestionsEl.classList.add('active');
        } else {
            suggestionsEl.classList.remove('active');
        }
    } catch (err) {
        console.error('Suggestions error:', err);
    }
}

async function performSearch(query) {
    if (!query) return;
    currentSearchQuery = query;

    if (currentSearchMode === 'natural') {
        performNaturalSearch(query);
        return;
    }

    // Update the search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) searchInput.value = query;

    // If we're on the homepage, redirect to products page with query
    if (window.location.pathname === '/' || window.location.pathname === '') {
        window.location.href = `/products?q=${encodeURIComponent(query)}`;
        return;
    }

    // If on products page, show results
    const resultsContainer = document.getElementById('productsGrid');
    const resultsInfo = document.getElementById('resultsInfo');
    const automataInfo = document.getElementById('automataInfo');

    if (resultsContainer) showLoading('productsGrid');

    try {
        const res = await fetch(`${API.search}?q=${encodeURIComponent(query)}`);
        const data = await res.json();

        if (resultsInfo) {
            resultsInfo.innerHTML = `<span class="count">${data.total || 0} results</span> for "<strong>${query}</strong>"`;
            resultsInfo.style.display = 'flex';
        }

        renderProductsGrid('productsGrid', data.products, true);

        // Show automata info if available
        if (automataInfo && data.automata_info) {
            renderAutomataInfo(automataInfo, data.automata_info);
        }

        // FEATURE 1: Render Search Intent Journey & Next Suggestions
        updateSearchJourneyUI();

        // FEATURE 2: Zero-Result Recovery & Typo Correction
        const typoContainer = document.getElementById('zeroResultRecoverySection');
        if (typoContainer) {
            if (data.total === 0 && (data.recovery || data.has_typos)) {
                renderZeroResultRecovery(typoContainer, data.recovery, query);
            } else {
                typoContainer.style.display = 'none';
            }
        }

        // FEATURE 3: Adaptive Filter Suggestions
        loadAdaptiveFilterSuggestions(query);

    } catch (err) {
        console.error('Search error:', err);
        showEmpty('productsGrid', 'Error performing search. Please try again.', '⚠️');
    }
}

function renderAutomataInfo(container, info) {
    if (!container || !info) return;

    let dfa_html = '';
    if (info.dfa_states_example) {
        const ex = info.dfa_states_example;
        dfa_html = `
            <div style="margin-top:0.5rem">
                <strong>DFA Trace (sample):</strong><br>
                States: {${(ex.states || []).join(', ')}}<br>
                Start: ${ex.start_state} | Accept: {${(ex.accept_states || []).join(', ')}}<br>
                Final: ${ex.current_state} → <strong>${ex.accepted ? 'ACCEPTED ✓' : 'REJECTED ✗'}</strong>
            </div>`;
    }

    container.innerHTML = `
        <div class="automata-debug">
            <h4><i class="fa-solid fa-diagram-project"></i> Search Analysis</h4>
            <pre>
Input String:    "${info.input_string}"
Keywords:        [${(info.keywords || []).join(', ')}]
Regex Pattern:   ${info.regex_pattern || 'N/A'}
DFA Matches:     ${info.dfa_matched_count || 0} products
Regex Matches:   ${info.regex_matched_count || 0} products
Total Matches:   ${info.total_matched || 0} products
            </pre>
            ${dfa_html}
        </div>
    `;
    container.style.display = 'block';
}


// ============================================================
// PRODUCTS PAGE
// ============================================================

async function loadProducts() {
    const grid = document.getElementById('productsGrid');
    if (!grid) return;

    // Check for search query in URL
    const urlParams = new URLSearchParams(window.location.search);
    const query = urlParams.get('q');

    if (query) {
        const searchInput = document.getElementById('searchInput');
        if (searchInput) searchInput.value = query;
        await performSearch(query);
        return;
    }

    showLoading('productsGrid');

    try {
        const res = await fetch(API.products);
        const data = await res.json();
        renderProductsGrid('productsGrid', data.products, true);

        const resultsInfo = document.getElementById('resultsInfo');
        if (resultsInfo) {
            resultsInfo.innerHTML = `<span class="count">${data.total || 0} products</span> found`;
            resultsInfo.style.display = 'flex';
        }
    } catch (err) {
        console.error('Load products error:', err);
        showEmpty('productsGrid', 'Error loading products.', '⚠️');
    }
}

async function loadFilterOptions() {
    try {
        const [catRes, brandRes] = await Promise.all([
            fetch(API.categories),
            fetch(API.brands)
        ]);
        const catData = await catRes.json();
        const brandData = await brandRes.json();

        const catSelect = document.getElementById('filterCategory');
        const brandSelect = document.getElementById('filterBrand');

        if (catSelect && catData.categories) {
            catData.categories.forEach(c => {
                const opt = document.createElement('option');
                opt.value = c.category_name;
                opt.textContent = `${c.category_name} (${c.product_count})`;
                catSelect.appendChild(opt);
            });
        }

        if (brandSelect && brandData.brands) {
            brandData.brands.forEach(b => {
                const opt = document.createElement('option');
                opt.value = b.brand;
                opt.textContent = `${b.brand} (${b.product_count})`;
                brandSelect.appendChild(opt);
            });
        }
    } catch (err) {
        console.error('Filter options error:', err);
    }
}

async function applyFilters() {
    const category = document.getElementById('filterCategory')?.value || '';
    const brand = document.getElementById('filterBrand')?.value || '';
    const minPrice = document.getElementById('filterMinPrice')?.value || '';
    const maxPrice = document.getElementById('filterMaxPrice')?.value || '';
    const minRating = document.querySelector('input[name="rating"]:checked')?.value || '';
    const sortBy = document.getElementById('sortBy')?.value || 'relevant';
    const searchQuery = document.getElementById('searchInput')?.value || '';

    showLoading('productsGrid');

    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (brand) params.append('brand', brand);
    if (minPrice) params.append('min_price', minPrice);
    if (maxPrice) params.append('max_price', maxPrice);
    if (minRating) params.append('min_rating', minRating);
    if (sortBy) params.append('sort_by', sortBy);
    if (searchQuery) params.append('q', searchQuery);

    try {
        const res = await fetch(`${API.products}?${params.toString()}`);
        const data = await res.json();

        renderProductsGrid('productsGrid', data.products, true);

        // Update results info
        const resultsInfo = document.getElementById('resultsInfo');
        if (resultsInfo) {
            resultsInfo.innerHTML = `<span class="count">${data.total || 0} products</span> found`;
            resultsInfo.style.display = 'flex';
        }

        // Update applied filters display
        renderAppliedFilters(data.applied_filters);
    } catch (err) {
        console.error('Filter error:', err);
        showEmpty('productsGrid', 'Error applying filters.', '⚠️');
    }
}

function renderAppliedFilters(filters) {
    const container = document.getElementById('appliedFilters');
    if (!container) return;
    container.innerHTML = '';

    if (!filters) return;

    const labels = {
        category: 'Category',
        brand: 'Brand',
        min_price: 'Min Price (₹)',
        max_price: 'Max Price (₹)',
        min_rating: 'Min Rating'
    };

    for (const [key, value] of Object.entries(filters)) {
        if (value && key !== 'sort_by') {
            const displayVal = (key === 'min_price' || key === 'max_price') ? formatPrice(value) : value;
            const tag = document.createElement('span');
            tag.className = 'filter-tag';
            tag.innerHTML = `${labels[key] || key}: ${displayVal} <span class="remove-filter" onclick="clearFilter('${key}')">×</span>`;
            container.appendChild(tag);
        }
    }
}

function clearFilter(filterKey) {
    const mapping = {
        category: 'filterCategory',
        brand: 'filterBrand',
        min_price: 'filterMinPrice',
        max_price: 'filterMaxPrice',
        min_rating: null // handled separately
    };

    if (filterKey === 'min_rating') {
        document.querySelectorAll('input[name="rating"]').forEach(r => r.checked = false);
    } else {
        const el = document.getElementById(mapping[filterKey]);
        if (el) el.value = '';
    }

    applyFilters();
}

function resetFilters() {
    const filterCategory = document.getElementById('filterCategory');
    const filterBrand = document.getElementById('filterBrand');
    const filterMinPrice = document.getElementById('filterMinPrice');
    const filterMaxPrice = document.getElementById('filterMaxPrice');
    const sortBy = document.getElementById('sortBy');

    if (filterCategory) filterCategory.value = '';
    if (filterBrand) filterBrand.value = '';
    if (filterMinPrice) filterMinPrice.value = '';
    if (filterMaxPrice) filterMaxPrice.value = '';
    if (sortBy) sortBy.value = 'relevant';
    document.querySelectorAll('input[name="rating"]').forEach(r => r.checked = false);

    applyFilters();
}


// ============================================================
// FEATURE 1: SEARCH INTENT JOURNEY (FSM)
// ============================================================

async function updateSearchJourneyUI() {
    const journeyPanel = document.getElementById('searchJourneySection');
    const timelineEl = document.getElementById('journeyTimeline');
    const stateBadge = document.getElementById('journeyStateBadge');
    const stateDesc = document.getElementById('journeyStateDesc');
    const suggWrap = document.getElementById('journeySuggestionsWrap');
    const suggChips = document.getElementById('journeySuggestions');

    if (!journeyPanel || !timelineEl) return;

    try {
        const [journeyRes, suggRes] = await Promise.all([
            fetch(API.searchJourney),
            fetch(API.searchJourneySuggestions)
        ]);
        const journeyData = await journeyRes.json();
        const suggData = await suggRes.json();

        const journey = journeyData.journey || [];
        if (journey.length === 0) {
            journeyPanel.style.display = 'none';
            return;
        }

        journeyPanel.style.display = 'block';
        if (stateBadge) stateBadge.textContent = journeyData.current_state || 'EXPLORING';
        if (stateDesc) stateDesc.textContent = journeyData.state_description || '';

        // Render timeline of searches with transition labels
        timelineEl.innerHTML = journey.map((step, idx) => {
            const isLast = idx === journey.length - 1;
            const arrow = !isLast ? `<span class="journey-step-arrow">➔ <small>${journey[idx + 1]?.transition || 'next'}</small></span>` : '';
            return `
                <div class="journey-step-node ${isLast ? 'active' : ''}">
                    <span class="journey-step-query" onclick="performSearch('${step.query.replace(/'/g, "\\'")}')" title="Click to repeat search">
                        ${step.query}
                    </span>
                    <span class="journey-step-state">${step.current_state}</span>
                </div>
                ${arrow}
            `;
        }).join('');

        // Render suggested next queries
        if (suggChips && suggData.suggestions && suggData.suggestions.length > 0) {
            suggChips.innerHTML = suggData.suggestions.map(s => `
                <button type="button" class="journey-chip" onclick="performSearch('${s.query.replace(/'/g, "\\'")}')" title="${s.reason}">
                    <i class="fa-solid fa-magnifying-glass"></i> ${s.query} <span class="chip-hint">(${s.reason})</span>
                </button>
            `).join('');
            if (suggWrap) suggWrap.style.display = 'flex';
        } else if (suggWrap) {
            suggWrap.style.display = 'none';
        }

    } catch (err) {
        console.error('Search journey error:', err);
    }
}

async function clearSearchJourney() {
    try {
        await fetch(API.searchJourneyClear, { method: 'POST' });
        const journeyPanel = document.getElementById('searchJourneySection');
        if (journeyPanel) journeyPanel.style.display = 'none';
        showToast('Search journey reset.');
    } catch (err) {
        console.error('Clear journey error:', err);
    }
}


// ============================================================
// FEATURE 2: ZERO-RESULT SEARCH RECOVERY & TYPO CORRECTION
// ============================================================

function renderZeroResultRecovery(container, recovery, originalQuery) {
    if (!container) return;
    if (!recovery) {
        container.style.display = 'none';
        return;
    }

    container.style.display = 'block';

    const suggestedQueries = recovery.suggested_queries || [];
    const corrections = recovery.corrections || [];
    const partials = recovery.partial_matches || [];

    let didYouMeanHtml = '';
    if (suggestedQueries.length > 0) {
        const top = suggestedQueries[0];
        didYouMeanHtml = `
            <div class="typo-did-you-mean">
                <span class="typo-dym-label">Did you mean:</span>
                <button type="button" class="typo-dym-button" onclick="performSearch('${top.query.replace(/'/g, "\\'")}')">
                    ${top.query}
                </button>
                <span class="typo-dist-badge">(edit distance: ${top.total_edit_distance})</span>
            </div>
        `;
    }

    let alternativesHtml = '';
    if (corrections.length > 0) {
        alternativesHtml = `
            <div class="typo-suggestions-list">
                <span style="font-weight:600; font-size:0.85rem; color:var(--text-secondary);">Suggested Corrections:</span>
                <div class="typo-chips">
                    ${corrections.map(c => `
                        <button type="button" class="typo-chip" onclick="performSearch('${c.suggestion.replace(/'/g, "\\'")}')">
                            ${c.suggestion} <small>(d=${c.distance}, ${c.type})</small>
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    let partialsHtml = '';
    if (partials.length > 0) {
        partialsHtml = `
            <div class="typo-partials-list" style="margin-top:10px;">
                <span style="font-weight:600; font-size:0.85rem; color:var(--text-secondary);">Matching Products:</span>
                <div class="typo-chips">
                    ${partials.map(p => `
                        <button type="button" class="typo-chip" onclick="performSearch('${p.product_name.replace(/'/g, "\\'")}')">
                            <i class="fa-solid fa-box"></i> ${p.product_name}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;
    }

    container.innerHTML = `
        <div class="typo-recovery-box">
            <div class="typo-recovery-header">
                <span class="icon"><i class="fa-solid fa-magnifying-glass"></i></span>
                <div>
                    <strong>No exact matches for "${originalQuery}"</strong>
                    <div style="font-size:0.82rem; color:var(--text-secondary);">
                        Theory of Computation: Levenshtein Edit Distance & Approximate Pattern Matching
                    </div>
                </div>
            </div>
            ${didYouMeanHtml}
            ${alternativesHtml}
            ${partialsHtml}
        </div>
    `;
}


// ============================================================
// FEATURE 3: SESSION-AWARE ADAPTIVE FILTER ADVISOR
// ============================================================

async function loadAdaptiveFilterSuggestions(query = '') {
    const panel = document.getElementById('adaptiveFiltersSection');
    const chipsContainer = document.getElementById('adaptiveFilterChips');
    const stateBadge = document.getElementById('filterStateBadge');

    if (!panel || !chipsContainer) return;

    try {
        const cat = document.getElementById('filterCategory')?.value || '';
        const brand = document.getElementById('filterBrand')?.value || '';
        const minP = document.getElementById('filterMinPrice')?.value || '';
        const maxP = document.getElementById('filterMaxPrice')?.value || '';
        const rating = document.querySelector('input[name="rating"]:checked')?.value || '';

        const params = new URLSearchParams();
        if (query) params.append('q', query);
        if (cat) params.append('category', cat);
        if (brand) params.append('brand', brand);
        if (minP) params.append('min_price', minP);
        if (maxP) params.append('max_price', maxP);
        if (rating) params.append('min_rating', rating);

        const res = await fetch(`${API.filterSuggestions}?${params.toString()}`);
        const data = await res.json();

        if (!data.suggestions || data.suggestions.length === 0) {
            panel.style.display = 'none';
            return;
        }

        panel.style.display = 'block';
        if (stateBadge) stateBadge.textContent = data.current_state || 'ADAPTING';

        // Render filter suggestions as interactive action chips
        chipsContainer.innerHTML = '';
        data.suggestions.forEach(s => {
            if (s.options && s.options.length > 0) {
                s.options.slice(0, 3).forEach(opt => {
                    const chip = document.createElement('button');
                    chip.type = 'button';
                    chip.className = 'adaptive-filter-chip';

                    let labelText = '';
                    if (s.filter_type === 'category') {
                        labelText = `<i class="fa-solid fa-layer-group"></i> ${opt.value}`;
                        chip.onclick = () => applyAdaptiveFilter('category', opt.value);
                    } else if (s.filter_type === 'brand') {
                        labelText = `<i class="fa-solid fa-tag"></i> ${opt.value}`;
                        chip.onclick = () => applyAdaptiveFilter('brand', opt.value);
                    } else if (s.filter_type === 'price_range') {
                        labelText = `<i class="fa-solid fa-indian-rupee-sign"></i> ${opt.label}`;
                        chip.onclick = () => applyAdaptiveFilter('price', null, opt.min, opt.max);
                    } else if (s.filter_type === 'rating') {
                        labelText = `<i class="fa-solid fa-star"></i> ${opt.label}`;
                        chip.onclick = () => applyAdaptiveFilter('rating', opt.value);
                    } else if (s.filter_type === 'spec_keyword') {
                        labelText = `<i class="fa-solid fa-microchip"></i> ${opt.value}`;
                        chip.onclick = () => {
                            const input = document.getElementById('searchInput');
                            if (input) {
                                input.value = `${input.value} ${opt.value}`.trim();
                                performSearch(input.value);
                            }
                        };
                    }

                    chip.innerHTML = `${labelText} <span class="chip-plus">+</span>`;
                    chip.title = s.reason;
                    chipsContainer.appendChild(chip);
                });
            }
        });

    } catch (err) {
        console.error('Filter suggestions error:', err);
    }
}

function applyAdaptiveFilter(filterType, value, min = null, max = null) {
    if (filterType === 'category') {
        const catSelect = document.getElementById('filterCategory');
        if (catSelect) catSelect.value = value;
    } else if (filterType === 'brand') {
        const brandSelect = document.getElementById('filterBrand');
        if (brandSelect) brandSelect.value = value;
    } else if (filterType === 'price') {
        const minInput = document.getElementById('filterMinPrice');
        const maxInput = document.getElementById('filterMaxPrice');
        if (minInput) minInput.value = min !== null ? min : '';
        if (maxInput) maxInput.value = max !== null ? max : '';
    } else if (filterType === 'rating') {
        const ratingRadio = document.querySelector(`input[name="rating"][value="${value}"]`);
        if (ratingRadio) ratingRadio.checked = true;
    }
    applyFilters();
}


// ============================================================
// PRODUCT DETAIL PAGE
// ============================================================

async function loadProductDetail(productId) {
    if (!productId) return;

    showLoading('productDetailContent');

    try {
        // Record view
        await fetch(API.viewProduct, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId })
        });

        const res = await fetch(API.product(productId));
        const data = await res.json();

        if (data.error) {
            showEmpty('productDetailContent', 'Product not found.', '😕');
            return;
        }

        const p = data.product;
        const container = document.getElementById('productDetailContent');
        container.innerHTML = `
            <div class="product-detail">
                <div class="product-detail-image">
                    <img src="${p.image_url || ''}" alt="${p.product_name}"
                         onerror="this.src='/static/images/product-placeholder.svg'">
                </div>
                <div class="product-detail-info">
                    <div class="detail-brand">${p.brand}</div>
                    <h1>${p.product_name}</h1>
                    <div class="detail-rating">
                        <span class="stars">${renderStars(p.rating)}</span>
                        <span>${p.rating} / 5.0</span>
                    </div>
                    <div class="detail-price">${formatPrice(p.price)}</div>
                    <p class="detail-description">${p.description || ''}</p>
                    <div class="detail-meta">
                        <div>
                            <div class="meta-label">Category</div>
                            <div class="meta-value">${p.category}</div>
                        </div>
                        <div>
                            <div class="meta-label">Brand</div>
                            <div class="meta-value">${p.brand}</div>
                        </div>
                        <div>
                            <div class="meta-label">In Stock</div>
                            <div class="meta-value">${p.stock_quantity} units</div>
                        </div>
                        <div>
                            <div class="meta-label">Product ID</div>
                            <div class="meta-value">#${p.product_id}</div>
                        </div>
                    </div>
                    <div style="display:flex; flex-wrap:wrap; gap:10px; margin-top:1.5rem;">
                        <button class="btn btn-primary" onclick="addToWishlist(event, ${p.product_id})">
                            <i class="fa-solid fa-heart"></i> Add to Wishlist
                        </button>
                        <button class="btn btn-secondary" onclick="addToComparison(event, ${p.product_id})">
                            <i class="fa-solid fa-scale-balanced"></i> Add to Compare
                        </button>
                        <button class="btn btn-secondary" onclick="openPriceAlertModal(${p.product_id}, '${p.product_name.replace(/'/g, "\\'")}', ${p.price})">
                            <i class="fa-solid fa-bell"></i> Set Price Alert
                        </button>
                        <button class="btn btn-secondary" onclick="openExplainModal(event, ${p.product_id}, '${p.product_name.replace(/'/g, "\\'")}')">
                            <i class="fa-solid fa-circle-info"></i> Recommendation Insights
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Load similar products
        if (data.similar_products && data.similar_products.length > 0) {
            renderProductsScroll('similarProducts', data.similar_products);
        }

    } catch (err) {
        console.error('Product detail error:', err);
        showEmpty('productDetailContent', 'Error loading product details.', '<i class="fa-solid fa-triangle-exclamation"></i>');
    }
}


// ============================================================
// HOME PAGE SECTIONS
// ============================================================

async function loadHomePage() {
    // Load all home page sections in parallel
    await Promise.all([
        loadTrendingProducts(),
        loadRecommendedProducts(),
        loadRecentlyViewedProducts(),
        loadPopularSearches(),
        loadCategories(),
        loadHomeDiscovery()
    ]);
}

async function loadHomeDiscovery() {
    const container = document.getElementById('homeDiscoveryProducts');
    if (!container) return;
    try {
        const res = await fetch(API.recDiscover);
        const data = await res.json();
        renderProductsScroll('homeDiscoveryProducts', data.products || []);
    } catch (e) {
        console.error('Home discovery error:', e);
    }
}

async function loadCategories() {
    try {
        const res = await fetch(API.categories);
        const data = await res.json();
        const container = document.getElementById('categoriesGrid');
        if (!container || !data.categories) return;

        const icons = {
            'Smartphones': '<i class="fa-solid fa-mobile-screen-button"></i>',
            'Laptops': '<i class="fa-solid fa-laptop"></i>',
            'Headphones': '<i class="fa-solid fa-headphones"></i>',
            'Smartwatches': '<i class="fa-solid fa-clock"></i>',
            'Clothing': '<i class="fa-solid fa-shirt"></i>',
            'Shoes': '<i class="fa-solid fa-shoe-prints"></i>',
            'Home Appliances': '<i class="fa-solid fa-blender"></i>',
            'Accessories': '<i class="fa-solid fa-plug"></i>'
        };

        container.innerHTML = '';
        data.categories.forEach(c => {
            const card = document.createElement('div');
            card.className = 'category-card';
            card.onclick = () => window.location.href = `/products?category=${encodeURIComponent(c.category_name)}`;
            card.innerHTML = `
                <span class="cat-icon">${icons[c.category_name] || '<i class="fa-solid fa-box"></i>'}</span>
                <span class="cat-name">${c.category_name}</span>
            `;
            container.appendChild(card);
        });
    } catch (err) {
        console.error('Categories error:', err);
    }
}

async function loadTrendingProducts() {
    try {
        const res = await fetch(API.trending);
        const data = await res.json();
        renderProductsScroll('trendingProducts', data.products);
    } catch (err) {
        console.error('Trending error:', err);
    }
}

async function loadRecommendedProducts() {
    try {
        const res = await fetch(API.recommendations);
        const data = await res.json();
        renderProductsScroll('recommendedProducts', data.recommendations);
    } catch (err) {
        console.error('Recommendations error:', err);
    }
}

async function loadRecentlyViewedProducts() {
    try {
        const res = await fetch(API.recentlyViewed);
        const data = await res.json();
        const container = document.getElementById('recentlyViewedProducts');
        if (!container) return;

        if (!data.products || data.products.length === 0) {
            container.innerHTML = '<p style="color:var(--text-muted);padding:1rem;">No recently viewed products. Start browsing to see your history!</p>';
            return;
        }
        renderProductsScroll('recentlyViewedProducts', data.products);
    } catch (err) {
        console.error('Recently viewed error:', err);
    }
}

async function loadPopularSearches() {
    try {
        const res = await fetch(API.popularSearches);
        const data = await res.json();
        const container = document.getElementById('popularSearches');
        if (!container) return;

        if (!data.searches || data.searches.length === 0) {
            container.innerHTML = '<p style="color:rgba(255,255,255,0.7);font-size:0.9rem;">Search for products to see popular searches here!</p>';
            return;
        }

        container.innerHTML = '';
        data.searches.forEach(s => {
            const tag = document.createElement('span');
            tag.className = 'popular-search-tag';
            tag.textContent = s.search_query;
            tag.onclick = () => performSearch(s.search_query);
            container.appendChild(tag);
        });
    } catch (err) {
        console.error('Popular searches error:', err);
    }
}


// ============================================================
// RECOMMENDATIONS PAGE
// ============================================================

async function loadRecommendationsPage() {
    await Promise.all([
        loadFullRecommendations(),
        loadSimilarRecommendations(),
        loadDiscoveryRecommendations(),
        loadBecauseYouViewed(),
        loadRecentlyViewedForRecPage(),
        loadUserPreferences(),
        loadFrequentlySearched()
    ]);
}

async function loadSimilarRecommendations() {
    const container = document.getElementById('similarProducts');
    const expl = document.getElementById('similarExplanation');
    if (!container) return;
    try {
        const res = await fetch(API.recSimilar);
        const data = await res.json();
        if (expl && data.based_on) {
            expl.textContent = `${data.based_on} — ${data.explanation || ''}`;
        }
        renderProductsScroll('similarProducts', data.products || []);
    } catch (err) {
        console.error('Similar recommendations error:', err);
    }
}

async function loadDiscoveryRecommendations() {
    const container = document.getElementById('discoveryProducts');
    const expl = document.getElementById('discoveryExplanation');
    if (!container) return;
    try {
        const res = await fetch(API.recDiscover);
        const data = await res.json();
        if (expl && data.discovery_categories) {
            expl.textContent = `Discovered categories: ${data.discovery_categories.join(', ')} — ${data.explanation || ''}`;
        }
        renderProductsScroll('discoveryProducts', data.products || []);
    } catch (err) {
        console.error('Discovery recommendations error:', err);
    }
}

async function loadFullRecommendations() {
    showLoading('recProducts');
    try {
        const res = await fetch(`${API.recommendations}?limit=16`);
        const data = await res.json();
        renderProductsGrid('recProducts', data.recommendations);
    } catch (err) {
        showEmpty('recProducts', 'Error loading recommendations.', '⚠️');
    }
}

async function loadBecauseYouViewed() {
    try {
        const res = await fetch(API.becauseYouViewed);
        const data = await res.json();
        const container = document.getElementById('becauseViewedProducts');
        const section = document.getElementById('becauseViewedSection');
        if (!container) return;

        if (!data.products || data.products.length === 0) {
            if (section) section.style.display = 'none';
            return;
        }

        if (section) section.style.display = 'block';
        renderProductsScroll('becauseViewedProducts', data.products);

        const catInfo = document.getElementById('viewedCategories');
        if (catInfo && data.based_on_categories) {
            catInfo.textContent = `Based on your interest in: ${data.based_on_categories.join(', ')}`;
        }
    } catch (err) {
        console.error('Because you viewed error:', err);
    }
}

async function loadRecentlyViewedForRecPage() {
    try {
        const res = await fetch(API.recentlyViewed);
        const data = await res.json();
        const container = document.getElementById('recRecentlyViewed');
        const section = document.getElementById('recRecentSection');
        if (!container) return;

        if (!data.products || data.products.length === 0) {
            if (section) section.style.display = 'none';
            return;
        }

        if (section) section.style.display = 'block';
        renderProductsScroll('recRecentlyViewed', data.products);
    } catch (err) {
        console.error('Recently viewed error:', err);
    }
}

async function loadUserPreferences() {
    try {
        const res = await fetch(API.userPreferences);
        const data = await res.json();
        const container = document.getElementById('userPreferences');
        if (!container || !data.preferences) return;

        const maxScore = Math.max(...data.preferences.map(p => p.preference_score), 1);
        container.innerHTML = '';

        data.preferences.forEach(p => {
            const pct = Math.min((p.preference_score / maxScore) * 100, 100);
            container.innerHTML += `
                <div class="pref-bar-container">
                    <div class="pref-bar-label">
                        <span>${p.category}</span>
                        <span>${p.preference_score.toFixed(1)}</span>
                    </div>
                    <div class="pref-bar-track">
                        <div class="pref-bar-fill" style="width:${pct}%"></div>
                    </div>
                </div>
            `;
        });
    } catch (err) {
        console.error('Preferences error:', err);
    }
}

async function loadFrequentlySearched() {
    try {
        const res = await fetch(API.frequentlySearched);
        const data = await res.json();
        const container = document.getElementById('freqCategories');
        if (!container) return;

        if (!data.categories || data.categories.length === 0) {
            container.innerHTML = '<p style="color:var(--text-muted);">No search activity yet.</p>';
            return;
        }

        container.innerHTML = '';
        data.categories.forEach(c => {
            container.innerHTML += `
                <span class="badge badge-primary" style="margin:4px;padding:6px 14px;font-size:0.85rem;cursor:pointer;"
                      onclick="window.location.href='/products?category=${encodeURIComponent(c.category)}'">
                    ${c.category} (${c.preference_score.toFixed(0)})
                </span>
            `;
        });
    } catch (err) {
        console.error('Frequently searched error:', err);
    }
}


// ============================================================
// SEARCH HISTORY PAGE
// ============================================================

async function loadSearchHistory() {
    showLoading('historyList');
    try {
        const res = await fetch(API.history);
        const data = await res.json();
        const container = document.getElementById('historyList');
        if (!container) return;

        if (!data.history || data.history.length === 0) {
            showEmpty('historyList', 'No search history yet. Start searching!', '<i class="fa-solid fa-clock-rotate-left"></i>');
            return;
        }

        container.innerHTML = '';
        data.history.forEach(h => {
            const item = document.createElement('div');
            item.className = 'history-item';
            item.innerHTML = `
                <span class="query-text" style="cursor:pointer;" onclick="performSearch('${h.search_query.replace(/'/g, "\\'")}')">
                    <i class="fa-solid fa-clock-rotate-left"></i> ${h.search_query}
                </span>
                <span class="query-time">${h.searched_at}</span>
            `;
            container.appendChild(item);
        });
    } catch (err) {
        console.error('History error:', err);
        showEmpty('historyList', 'Error loading history.', '⚠️');
    }
}

async function clearSearchHistory() {
    if (!confirm('Are you sure you want to clear your search history?')) return;

    try {
        await fetch(API.clearHistory, { method: 'POST' });
        showToast('Search history cleared!');
        loadSearchHistory();
    } catch (err) {
        console.error('Clear history error:', err);
        showToast('Error clearing history.');
    }
}


// ============================================================
// NATURAL LANGUAGE (CFG) SEARCH
// ============================================================

function setSearchMode(mode) {
    currentSearchMode = mode;
    const stdBtn = document.getElementById('modeStandardBtn');
    const natBtn = document.getElementById('modeNaturalBtn');
    const input = document.getElementById('searchInput');
    const examples = document.getElementById('naturalExamples');

    if (mode === 'natural') {
        natBtn?.classList.add('active');
        stdBtn?.classList.remove('active');
        if (input) input.placeholder = 'e.g. "Show laptops under 50000" or "Find Samsung phones between 15000 and 30000"';
        if (examples) examples.style.display = 'block';
    } else {
        stdBtn?.classList.add('active');
        natBtn?.classList.remove('active');
        if (input) input.placeholder = 'Search for smartphones, laptops, headphones...';
        if (examples) examples.style.display = 'none';
    }
}

function selectNaturalExample(query) {
    const input = document.getElementById('searchInput');
    if (input) input.value = query;
    setSearchMode('natural');
    performSearch(query);
}

async function performNaturalSearch(query) {
    if (!query) return;
    currentSearchQuery = query;

    if (window.location.pathname === '/' || window.location.pathname === '') {
        window.location.href = `/products?mode=natural&q=${encodeURIComponent(query)}`;
        return;
    }

    const resultsContainer = document.getElementById('productsGrid');
    const resultsInfo = document.getElementById('resultsInfo');
    const automataInfo = document.getElementById('automataInfo');

    if (resultsContainer) showLoading('productsGrid');

    try {
        const res = await fetch(API.naturalSearch, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();

        if (!data.success) {
            if (resultsInfo) {
                resultsInfo.innerHTML = `⚠️ <span>${data.error || 'Could not parse natural language query.'}</span>`;
                resultsInfo.style.display = 'flex';
            }
            if (resultsContainer) {
                resultsContainer.innerHTML = `
                    <div class="empty-state">
                        <span class="empty-icon">💬</span>
                        <h3>Query could not be parsed with Context-Free Grammar</h3>
                        <p style="color:var(--text-secondary); max-width:500px; margin:0.5rem auto;">${data.error || ''}</p>
                        <p style="font-size:0.85rem; color:var(--text-muted); margin-bottom:1rem;">Supported syntax: "Show laptops under 50000", "Find Samsung phones between 15000 and 30000", "Show shoes above 4 stars"</p>
                        <button class="btn btn-primary" onclick="setSearchMode('standard'); performSearch('${query.replace(/'/g, "\\'")}')">
                            Try Standard Keyword & Automata Search
                        </button>
                    </div>
                `;
            }
            return;
        }

        renderProductsGrid('productsGrid', data.products, true);

        const cond = data.conditions || {};
        let condBadges = [];
        if (cond.category) condBadges.push(`<i class="fa-solid fa-layer-group"></i> Category: <strong>${cond.category}</strong>`);
        if (cond.brand) condBadges.push(`<i class="fa-solid fa-tag"></i> Brand: <strong>${cond.brand}</strong>`);
        if (cond.max_price) condBadges.push(`<i class="fa-solid fa-indian-rupee-sign"></i> Max: <strong>${formatPrice(cond.max_price)}</strong>`);
        if (cond.min_price) condBadges.push(`<i class="fa-solid fa-indian-rupee-sign"></i> Min: <strong>${formatPrice(cond.min_price)}</strong>`);
        if (cond.min_rating) condBadges.push(`<i class="fa-solid fa-star"></i> Rating: <strong>${cond.min_rating}+</strong>`);
        if (cond.specs && cond.specs.length > 0) condBadges.push(`<i class="fa-solid fa-microchip"></i> Specs: <strong>${cond.specs.join(', ')}</strong>`);

        if (resultsInfo) {
            resultsInfo.innerHTML = `
                <div>
                    <span class="count">${data.total || 0} products</span> for "<em>${query}</em>"
                    <div style="margin-top:6px; display:flex; flex-wrap:wrap; gap:6px;">
                        ${condBadges.map(b => `<span class="badge badge-primary" style="font-size:0.8rem; padding:4px 10px;">${b}</span>`).join('')}
                    </div>
                </div>
            `;
            resultsInfo.style.display = 'flex';
        }

        if (automataInfo && data.parse_result) {
            renderCFGInfo(automataInfo, data.parse_result);
        }

    } catch (err) {
        console.error('Natural search error:', err);
        showEmpty('productsGrid', 'Error executing natural language search.', '<i class="fa-solid fa-triangle-exclamation"></i>');
    }
}

function renderCFGInfo(container, parseResult) {
    if (!container || !parseResult) return;
    container.innerHTML = `
        <div class="automata-debug" style="background:#eff6ff; border-color:#bfdbfe;">
            <h4 style="color:var(--primary-dark);">💬 Context-Free Grammar (CFG) Derivation & Parse Tree</h4>
            <div style="font-size:0.8rem; margin-bottom:6px;">
                <strong>Grammar Rules Applied:</strong><br>
                ${(parseResult.grammar_rules || []).map(r => `<span class="cfg-rule-badge">${r}</span>`).join(' ')}
            </div>
            <pre style="background:#1e293b; color:#38bdf8; font-size:0.8rem; border-color:#334155;">${parseResult.text_tree || ''}</pre>
        </div>
    `;
    container.style.display = 'block';
}

// ============================================================
// BADGES & NOTIFICATIONS
// ============================================================

async function updateNavBadges() {
    try {
        const [compRes, wishRes, alertRes] = await Promise.all([
            fetch(API.compare),
            fetch(API.wishlist),
            fetch(API.alerts)
        ]);

        const compData = await compRes.json();
        const wishData = await wishRes.json();
        const alertData = await alertRes.json();

        const compBadge = document.getElementById('navCompareBadge');
        if (compBadge) {
            compBadge.textContent = compData.count || 0;
            compBadge.style.display = (compData.count > 0) ? 'inline-block' : 'none';
        }

        const wishBadge = document.getElementById('navWishlistBadge');
        if (wishBadge) {
            wishBadge.textContent = wishData.count || 0;
            wishBadge.style.display = (wishData.count > 0) ? 'inline-block' : 'none';
        }

        const alertBadge = document.getElementById('navAlertsBadge');
        if (alertBadge) {
            const trig = alertData.total_triggered || 0;
            alertBadge.textContent = trig > 0 ? `! ${trig}` : (alertData.total_active || 0);
            alertBadge.style.display = (alertData.total_active > 0 || trig > 0) ? 'inline-block' : 'none';
            if (trig > 0) alertBadge.classList.add('alert-glow');
            else alertBadge.classList.remove('alert-glow');
        }

    } catch (err) {
        console.warn('Failed to update nav badges:', err);
    }
}

// ============================================================
// PRODUCT COMPARISON WORKSPACE
// ============================================================

async function addToComparison(event, productId) {
    if (event) event.stopPropagation();
    try {
        const res = await fetch(API.compare, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId })
        });
        const data = await res.json();
        showToast(data.message || 'Updated comparison list');
        updateNavBadges();
        if (window.location.pathname === '/compare') {
            loadComparisonTable();
        }
    } catch (err) {
        showToast('Error adding to comparison');
    }
}

async function removeFromComparison(productId) {
    try {
        const res = await fetch(`${API.compare}/${productId}`, { method: 'DELETE' });
        const data = await res.json();
        showToast(data.message || 'Removed from comparison');
        updateNavBadges();
        loadComparisonTable();
    } catch (err) {
        showToast('Error removing product');
    }
}

async function clearComparison() {
    if (!confirm('Are you sure you want to clear your comparison list?')) return;
    try {
        await fetch(API.compareClear, { method: 'DELETE' });
        showToast('Comparison list cleared');
        updateNavBadges();
        loadComparisonTable();
    } catch (err) {
        showToast('Error clearing comparison');
    }
}

async function loadComparisonTable() {
    const container = document.getElementById('compareContent');
    const actions = document.getElementById('compareActions');
    if (!container) return;

    showLoading('compareContent');
    try {
        const res = await fetch(API.compare);
        const data = await res.json();

        if (!data.products || data.products.length === 0) {
            if (actions) actions.style.display = 'none';
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">⚖️</span>
                    <h3>No Products in Comparison</h3>
                    <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Select "Add to Compare" on any product card (up to 4 products) to view side-by-side specifications.</p>
                    <a href="/products" class="btn btn-primary">Browse All Products</a>
                </div>
            `;
            return;
        }

        if (actions) actions.style.display = 'flex';

        const prods = data.products;
        const lowestId = data.lowest_price_id;
        const highestId = data.highest_rated_id;

        let html = `
            <div class="compare-container">
                <table class="compare-table">
                    <thead>
                        <tr>
                            <th>Attribute</th>
                            ${prods.map(p => `
                                <th class="compare-prod-header">
                                    <button class="btn btn-secondary btn-sm" style="position:absolute; top:8px; right:8px; padding:2px 8px;" onclick="removeFromComparison(${p.product_id})" title="Remove">✕</button>
                                    <img src="${p.image_url}" alt="${p.product_name}" class="compare-prod-img" onerror="this.src='/static/images/product-placeholder.svg'">
                                    <div style="font-weight:700; font-size:0.95rem; margin-top:6px;">${p.product_name}</div>
                                    <div style="color:var(--text-muted); font-size:0.75rem;">${p.brand}</div>
                                    ${p.product_id === lowestId ? '<span class="badge-best-price"><i class="fa-solid fa-tag"></i> Lowest Price</span>' : ''}
                                    ${p.product_id === highestId ? '<span class="badge-top-rated"><i class="fa-solid fa-star"></i> Highest Rated</span>' : ''}
                                </th>
                            `).join('')}
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>Price</td>
                            ${prods.map(p => `
                                <td>
                                    <span style="font-size:1.2rem; font-weight:800; color:var(--primary-dark);">${formatPrice(p.price)}</span>
                                    ${p.product_id === lowestId ? '<br><small style="color:#10b981; font-weight:600;">Best Value</small>' : ''}
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <td>Rating</td>
                            ${prods.map(p => `
                                <td>
                                    <span style="color:#f59e0b; font-size:1rem;">${renderStars(p.rating)}</span>
                                    <strong>${p.rating}</strong> / 5.0
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <td>Category</td>
                            ${prods.map(p => `<td><span class="badge badge-primary">${p.category}</span></td>`).join('')}
                        </tr>
                        <tr>
                            <td>Brand</td>
                            ${prods.map(p => `<td><strong>${p.brand}</strong></td>`).join('')}
                        </tr>
                        <tr>
                            <td>Availability</td>
                            ${prods.map(p => `
                                <td>
                                    <span style="color:${p.stock_quantity > 0 ? '#10b981' : '#ef4444'}; font-weight:600;">
                                        ${p.stock_quantity > 0 ? `✓ In Stock (${p.stock_quantity})` : 'Out of stock'}
                                    </span>
                                </td>
                            `).join('')}
                        </tr>
                        <tr>
                            <td>Key Specifications</td>
                            ${prods.map(p => `<td style="font-size:0.85rem; line-height:1.6; color:var(--text-secondary);">${p.description || '-'}</td>`).join('')}
                        </tr>
                        <tr>
                            <td>Actions</td>
                            ${prods.map(p => `
                                <td>
                                    <div style="display:flex; flex-direction:column; gap:6px;">
                                        <a href="/product/${p.product_id}" class="btn btn-primary btn-sm">View Details</a>
                                        <button class="btn btn-secondary btn-sm" onclick="addToWishlist(event, ${p.product_id})">❤️ Wishlist</button>
                                        <button class="btn btn-secondary btn-sm" onclick="openPriceAlertModal(${p.product_id}, '${p.product_name.replace(/'/g, "\\'")}', ${p.price})">🔔 Price Alert</button>
                                    </div>
                                </td>
                            `).join('')}
                        </tr>
                    </tbody>
                </table>
            </div>
        `;

        container.innerHTML = html;

    } catch (err) {
        console.error('Comparison error:', err);
        showEmpty('compareContent', 'Error loading comparison table.', '⚠️');
    }
}

// ============================================================
// SMART WISHLIST
// ============================================================

async function addToWishlist(event, productId) {
    if (event) event.stopPropagation();
    try {
        const res = await fetch(API.wishlist, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId })
        });
        const data = await res.json();
        showToast(data.message || 'Wishlist updated');
        updateNavBadges();
        if (window.location.pathname === '/wishlist') {
            loadWishlistPage();
        }
    } catch (err) {
        showToast('Error saving to wishlist');
    }
}

async function removeFromWishlist(productId) {
    try {
        const res = await fetch(`${API.wishlist}/${productId}`, { method: 'DELETE' });
        const data = await res.json();
        showToast(data.message || 'Removed from wishlist');
        updateNavBadges();
        loadWishlistPage();
    } catch (err) {
        showToast('Error removing from wishlist');
    }
}

async function loadWishlistPage() {
    const grid = document.getElementById('wishlistGrid');
    const countBadge = document.getElementById('wishlistCountBadge');
    if (!grid) return;

    showLoading('wishlistGrid');
    try {
        const res = await fetch(API.wishlist);
        const data = await res.json();

        if (countBadge) {
            countBadge.textContent = `${data.count || 0} Items Saved`;
        }

        if (!data.products || data.products.length === 0) {
            grid.innerHTML = `
                <div class="empty-state" style="grid-column: 1 / -1;">
                    <span class="empty-icon">❤️</span>
                    <h3>Your Wishlist is Empty</h3>
                    <p style="color:var(--text-secondary); margin-bottom:1.5rem;">Save items you love so you can track prices and review them anytime.</p>
                    <a href="/products" class="btn btn-primary">Discover Products</a>
                </div>
            `;
            return;
        }

        grid.innerHTML = '';
        data.products.forEach(p => {
            const card = document.createElement('div');
            card.className = 'product-card';
            card.innerHTML = `
                <div class="product-image" onclick="window.location.href='/product/${p.product_id}'">
                    <img src="${p.image_url}" alt="${p.product_name}" onerror="this.src='/static/images/product-placeholder.svg'">
                </div>
                <div class="product-info">
                    <span class="product-brand">${p.brand}</span>
                    <h3 class="product-name" onclick="window.location.href='/product/${p.product_id}'">${p.product_name}</h3>
                    <div class="product-rating">
                        <span class="stars">${renderStars(p.rating)}</span>
                        <span class="rating-num">(${p.rating})</span>
                    </div>
                    <div class="product-price">${formatPrice(p.price)}</div>
                    ${p.target_price ? `<div style="font-size:0.8rem; color:#059669; margin:4px 0;">🔔 Alert set at: <strong>${formatPrice(p.target_price)}</strong></div>` : ''}
                    <div class="card-actions-bar" style="margin-top:auto;">
                        <button class="btn btn-secondary btn-sm" onclick="openPriceAlertModal(${p.product_id}, '${p.product_name.replace(/'/g, "\\'")}', ${p.price})" title="Set Price Drop Alert">
                            🔔 Alert
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="addToComparison(event, ${p.product_id})" title="Compare">
                            ⚖️ Compare
                        </button>
                        <button class="btn btn-danger btn-sm" onclick="removeFromWishlist(${p.product_id})" title="Remove from wishlist">
                            ✕ Remove
                        </button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });

    } catch (err) {
        console.error('Wishlist error:', err);
        showEmpty('wishlistGrid', 'Error loading wishlist.', '⚠️');
    }
}

// ============================================================
// PRICE DROP ALERTS
// ============================================================

function openPriceAlertModal(productId, productName, currentPrice) {
    const modal = document.getElementById('priceAlertModal');
    const title = document.getElementById('alertProductTitle');
    const priceText = document.getElementById('alertCurrentPrice');
    const prodIdInput = document.getElementById('alertProductId');
    const targetInput = document.getElementById('alertTargetPriceInput');

    if (!modal) return;

    if (title) title.textContent = productName;
    if (priceText) priceText.innerHTML = `Current Database Price: <strong>${formatPrice(currentPrice)}</strong>`;
    if (prodIdInput) prodIdInput.value = productId;
    if (targetInput) {
        targetInput.value = Math.round(currentPrice * 0.9);
    }

    modal.style.display = 'flex';
}

async function submitPriceAlert() {
    const productId = document.getElementById('alertProductId')?.value;
    const targetPrice = document.getElementById('alertTargetPriceInput')?.value;

    if (!productId || !targetPrice) {
        showToast('Please enter a target price');
        return;
    }

    try {
        const res = await fetch(API.alerts, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, target_price: targetPrice })
        });
        const data = await res.json();
        showToast(data.message || 'Price alert created!');
        closeModal('priceAlertModal');
        updateNavBadges();
        if (window.location.pathname === '/alerts') {
            loadAlertsPage();
        }
    } catch (err) {
        showToast('Error setting price alert');
    }
}

async function deletePriceAlert(alertId) {
    if (!confirm('Are you sure you want to delete this alert?')) return;
    try {
        const res = await fetch(`${API.alerts}/${alertId}`, { method: 'DELETE' });
        const data = await res.json();
        showToast(data.message || 'Alert deleted');
        updateNavBadges();
        loadAlertsPage();
    } catch (err) {
        showToast('Error deleting alert');
    }
}

async function loadAlertsPage() {
    const activeList = document.getElementById('activeAlertsList');
    const triggeredList = document.getElementById('triggeredAlertsList');
    const activeBadge = document.getElementById('activeCountBadge');
    const triggeredBadge = document.getElementById('triggeredCountBadge');

    if (!activeList || !triggeredList) return;

    try {
        const res = await fetch(API.alerts);
        const data = await res.json();

        if (activeBadge) activeBadge.textContent = data.total_active || 0;
        if (triggeredBadge) triggeredBadge.textContent = data.total_triggered || 0;

        if (!data.triggered_alerts || data.triggered_alerts.length === 0) {
            triggeredList.innerHTML = '<p style="color:var(--text-muted); padding:1rem; background:#fff; border-radius:var(--radius); border:1px solid var(--border);">No price drops triggered yet. Set target prices below or simulate a drop using the testing panel above.</p>';
        } else {
            triggeredList.innerHTML = `
                <div class="alerts-grid">
                    ${data.triggered_alerts.map(a => `
                        <div class="alert-card triggered">
                            <img src="${a.image_url}" alt="${a.product_name}" class="alert-card-img" onerror="this.src='/static/images/product-placeholder.svg'">
                            <div class="alert-card-info">
                                <span class="badge badge-success" style="margin-bottom:4px;"><i class="fa-solid fa-circle-check"></i> Price Dropped!</span>
                                <h4><a href="/product/${a.product_id}">${a.product_name}</a></h4>
                                <div style="font-size:0.85rem; margin:4px 0;">
                                    Current Price: <strong style="color:#059669; font-size:1.05rem;">${formatPrice(a.current_price)}</strong>
                                </div>
                                <div style="font-size:0.8rem; color:var(--text-muted);">
                                    Target was: ${formatPrice(a.target_price)} (Saved ₹${Math.abs(a.price_difference).toLocaleString('en-IN')})
                                </div>
                                <div style="margin-top:10px; display:flex; gap:8px;">
                                    <a href="/product/${a.product_id}" class="btn btn-primary btn-sm">Buy / View</a>
                                    <button class="btn btn-secondary btn-sm" onclick="deletePriceAlert(${a.alert_id})">Dismiss</button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

        if (!data.active_alerts || data.active_alerts.length === 0) {
            activeList.innerHTML = '<p style="color:var(--text-muted); padding:1rem; background:#fff; border-radius:var(--radius); border:1px solid var(--border);">No active price alerts. Browse your wishlist or product detail pages to set alerts.</p>';
        } else {
            activeList.innerHTML = `
                <div class="alerts-grid">
                    ${data.active_alerts.map(a => `
                        <div class="alert-card active-alert">
                            <img src="${a.image_url}" alt="${a.product_name}" class="alert-card-img" onerror="this.src='/static/images/product-placeholder.svg'">
                            <div class="alert-card-info">
                                <h4><a href="/product/${a.product_id}">${a.product_name}</a></h4>
                                <div style="font-size:0.85rem; margin:4px 0;">
                                    Current: <strong>${formatPrice(a.current_price)}</strong>
                                </div>
                                <div style="font-size:0.85rem; color:var(--primary); font-weight:600;">
                                    Target: <strong>${formatPrice(a.target_price)}</strong>
                                </div>
                                <div style="font-size:0.75rem; color:var(--text-muted); margin-top:2px;">
                                    Difference to drop: ₹${a.price_difference.toLocaleString('en-IN')}
                                </div>
                                <div style="margin-top:10px; display:flex; gap:8px;">
                                    <button class="btn btn-secondary btn-sm" onclick="openPriceAlertModal(${a.product_id}, '${a.product_name.replace(/'/g, "\\'")}', ${a.current_price})">Edit</button>
                                    <button class="btn btn-danger btn-sm" onclick="deletePriceAlert(${a.alert_id})">Delete</button>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            `;
        }

    } catch (err) {
        console.error('Alerts error:', err);
    }
}

async function populateSimulationDropdown() {
    const sel = document.getElementById('simProductSelect');
    if (!sel) return;
    try {
        const res = await fetch('/api/products?limit=30');
        const data = await res.json();
        if (data.products) {
            sel.innerHTML = '<option value="">Select a product to simulate...</option>';
            data.products.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.product_id;
                opt.textContent = `${p.product_name} (Current: ${formatPrice(p.price)})`;
                sel.appendChild(opt);
            });
        }
    } catch (err) {}
}

async function runPriceDropSimulation() {
    const sel = document.getElementById('simProductSelect');
    const priceInput = document.getElementById('simNewPriceInput');
    const resultBox = document.getElementById('simResult');

    const productId = sel?.value;
    const newPrice = priceInput?.value;

    if (!productId || !newPrice) {
        showToast('Please select a product and enter a simulated lower price.');
        return;
    }

    try {
        const res = await fetch(API.alertSimulateDrop, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ product_id: productId, new_price: newPrice })
        });
        const data = await res.json();

        if (resultBox) {
            resultBox.innerHTML = `
                <div style="background:#d1fae5; color:#065f46; padding:10px 14px; border-radius:var(--radius); border:1px solid #a7f3d0;">
                    ✓ <strong>Success:</strong> ${data.message}
                </div>
            `;
        }
        showToast('Database price updated!');
        updateNavBadges();
        loadAlertsPage();
        populateSimulationDropdown();
    } catch (err) {
        showToast('Simulation error');
    }
}

// ============================================================
// EXPLAINABLE RESULTS
// ============================================================

async function openExplainModal(event, productId, productName) {
    if (event) event.stopPropagation();

    const modal = document.getElementById('explainModal');
    const title = document.getElementById('explainModalTitle');
    const body = document.getElementById('explainModalBody');

    if (!modal) return;
    if (title) title.innerHTML = `💡 Explanation: <em>${productName}</em>`;
    if (body) body.innerHTML = '<div class="loading"><div class="spinner"></div> Computing explainability metrics...</div>';

    modal.style.display = 'flex';

    try {
        if (currentSearchQuery) {
            const res = await fetch(`${API.explainSearch}?product_id=${productId}&q=${encodeURIComponent(currentSearchQuery)}`);
            const data = await res.json();
            renderSearchExplanation(body, data);
        } else {
            const res = await fetch(`${API.explainRec}?product_id=${productId}`);
            const data = await res.json();
            renderRecExplanation(body, data);
        }
    } catch (err) {
        if (body) body.innerHTML = '<p style="color:var(--danger);">Error generating explanation.</p>';
    }
}

function renderSearchExplanation(container, data) {
    container.innerHTML = `
        <div style="font-size:0.9rem; line-height:1.7;">
            <div style="margin-bottom:1rem; padding:10px; background:var(--primary-50); border-radius:var(--radius); border-left:4px solid var(--primary);">
                <strong>Why this result matched:</strong><br>
                ${data.explanation}
            </div>
            <table class="transition-table" style="margin-top:1rem;">
                <tr><th style="width:140px;">Search Query</th><td>"<code>${data.query}</code>"</td></tr>
                <tr><th>Keywords Extracted</th><td>[${(data.keywords_extracted || []).join(', ')}]</td></tr>
                <tr><th>Product Name</th><td>${data.product_name}</td></tr>
                <tr><th>Category</th><td>${data.category}</td></tr>
                <tr><th>Brand</th><td>${data.brand}</td></tr>
                <tr><th>Name Matches</th><td>${data.matching_details.name_keywords.join(', ') || 'None'}</td></tr>
                <tr><th>Description Matches</th><td>${data.matching_details.description_keywords.join(', ') || 'None'}</td></tr>
            </table>
        </div>
    `;
}

function renderRecExplanation(container, data) {
    container.innerHTML = `
        <div style="font-size:0.9rem; line-height:1.7;">
            <div style="margin-bottom:1rem; padding:10px; background:#ecfdf5; border-radius:var(--radius); border-left:4px solid #10b981; color:#065f46;">
                <strong>Recommendation Reason:</strong><br>
                ${data.explanation}
            </div>
            <table class="transition-table" style="margin-top:1rem;">
                <tr><th style="width:160px;">Target Category</th><td>${data.category}</td></tr>
                <tr><th>User Interest Score</th><td><strong>${data.user_category_preference_score}</strong></td></tr>
                <tr><th>Recent Views in Category</th><td>${data.user_category_views_count} item(s)</td></tr>
                <tr><th>Product Rating</th><td>${data.rating} / 5.0</td></tr>
                <tr><th>Scoring Formula</th><td><code>${data.formula}</code></td></tr>
            </table>
        </div>
    `;
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) modal.style.display = 'none';
}

function closeModalOnOverlay(event, modalId) {
    if (event.target.id === modalId) {
        closeModal(modalId);
    }
}


// ============================================================
// NAVIGATION
// ============================================================

function toggleMobileNav() {
    const nav = document.getElementById('navLinks');
    if (nav) nav.classList.toggle('show');
}

function setActiveNav() {
    const path = window.location.pathname;
    document.querySelectorAll('.navbar-nav a').forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('href') === path) {
            link.classList.add('active');
        }
    });
}


// ============================================================
// PRODUCTS PAGE - URL PARAM HANDLING
// ============================================================

function handleProductsPageParams() {
    const urlParams = new URLSearchParams(window.location.search);
    const category = urlParams.get('category');
    const q = urlParams.get('q');
    const mode = urlParams.get('mode');

    if (mode === 'natural') {
        setSearchMode('natural');
    }

    if (category) {
        const catSelect = document.getElementById('filterCategory');
        if (catSelect) {
            setTimeout(() => {
                catSelect.value = category;
                applyFilters();
            }, 500);
        }
    } else if (q) {
        performSearch(q);
    }
}


// ============================================================
// INIT
// ============================================================

document.addEventListener('DOMContentLoaded', () => {
    setActiveNav();
    initSearch();
    updateNavBadges();
    handleProductsPageParams();
});

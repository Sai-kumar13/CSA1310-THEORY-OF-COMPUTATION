/**
 * AdaptiveShop - TOC Demonstration JavaScript
 * Handles DFA, NFA, Regex, and Search Pattern demonstrations.
 */

// ============================================================
// DFA DEMONSTRATION
// ============================================================

async function runDFADemo() {
    const demoType = document.getElementById('dfaDemoType')?.value || 'pattern';
    const pattern = document.getElementById('dfaPattern')?.value.trim() || '';
    const input = document.getElementById('dfaInput')?.value.trim() || '';
    const resultDiv = document.getElementById('dfaResult');

    if (!input) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter an input string.</p>';
        return;
    }

    if (demoType === 'pattern' && !pattern) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter a pattern for pattern matching.</p>';
        return;
    }

    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Processing...</div>';

    try {
        const res = await fetch('/api/demo/dfa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pattern, input_string: input, demo_type: demoType })
        });
        const data = await res.json();

        if (data.error) {
            resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${data.error}</p>`;
            return;
        }

        renderDFAResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderDFAResult(container, data) {
    const statusClass = data.accepted ? 'accepted' : 'rejected';
    const statusText = data.accepted ? '✓ ACCEPTED' : '✗ REJECTED';

    // Build state diagram
    let stateDiagram = '<div class="state-diagram">';
    const states = data.states || [];
    const acceptStates = new Set(data.accept_states || []);

    // Show relevant states from transitions
    const visitedStates = new Set();
    (data.transitions || []).forEach(t => {
        if (t.to_state) visitedStates.add(t.to_state);
        if (t.from_state) visitedStates.add(t.from_state);
    });

    const displayStates = states.filter(s => visitedStates.has(s) || s === data.start_state).slice(0, 12);

    displayStates.forEach((s, i) => {
        let classes = 'state-node';
        if (s === data.current_state) classes += ' active';
        if (acceptStates.has(s)) classes += ' accept';
        if (s === 'DEAD') classes += ' dead';

        if (i > 0) stateDiagram += '<span class="state-arrow">→</span>';
        stateDiagram += `<div class="${classes}">${s}</div>`;
    });
    stateDiagram += '</div>';

    // Build transition table
    let transTable = '';
    const transitions = data.transitions || [];
    if (transitions.length > 0) {
        transTable = `
            <table class="transition-table">
                <thead><tr><th>Step</th><th>Symbol</th><th>From</th><th>To</th><th>Description</th></tr></thead>
                <tbody>
                    ${transitions.slice(0, 20).map(t => `
                        <tr>
                            <td>${t.step}</td>
                            <td><code>${t.symbol}</code></td>
                            <td>${t.from_state || '-'}</td>
                            <td>${t.to_state}</td>
                            <td>${t.description}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status ${statusClass}">${statusText}</div>
            <h4>${data.demo_type || 'DFA Processing'}</h4>
            <p>${data.description || ''}</p>

            <div class="info-cards">
                <div class="info-card">
                    <div class="info-label">Input</div>
                    <div class="info-value">"${data.input_string}"</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Start State</div>
                    <div class="info-value">${data.start_state}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Final State</div>
                    <div class="info-value">${data.current_state}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Accept States</div>
                    <div class="info-value">{${(data.accept_states || []).join(', ')}}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Total Steps</div>
                    <div class="info-value">${data.total_steps}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Result</div>
                    <div class="info-value" style="color:${data.accepted ? 'var(--success)' : 'var(--danger)'}">${data.result}</div>
                </div>
            </div>

            <h4>State Transition Diagram</h4>
            ${stateDiagram}

            <h4>Transition Table (δ function)</h4>
            ${transTable}
        </div>
    `;
}


// ============================================================
// NFA DEMONSTRATION
// ============================================================

async function runNFADemo() {
    const patternsRaw = document.getElementById('nfaPatterns')?.value.trim() || '';
    const input = document.getElementById('nfaInput')?.value.trim() || '';
    const resultDiv = document.getElementById('nfaResult');

    if (!input) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter an input string.</p>';
        return;
    }

    if (!patternsRaw) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter at least one pattern.</p>';
        return;
    }

    const patterns = patternsRaw.split(',').map(p => p.trim()).filter(p => p);

    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Processing...</div>';

    try {
        const res = await fetch('/api/demo/nfa', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ patterns, input_string: input })
        });
        const data = await res.json();

        if (data.error) {
            resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${data.error}</p>`;
            return;
        }

        renderNFAResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderNFAResult(container, data) {
    const statusClass = data.accepted ? 'accepted' : 'rejected';
    const statusText = data.accepted ? '✓ ACCEPTED' : '✗ REJECTED';

    // Build NFA state diagram showing current states
    let stateDiagram = '<div class="state-diagram">';
    const finalStates = new Set(data.final_states || []);
    const acceptStates = new Set(data.accept_states || []);

    // Show up to 15 states
    const displayStates = (data.states || []).slice(0, 15);
    displayStates.forEach((s, i) => {
        let classes = 'state-node';
        if (finalStates.has(s)) classes += ' active';
        if (acceptStates.has(s)) classes += ' accept';

        if (i > 0) stateDiagram += '<span class="state-arrow">→</span>';
        stateDiagram += `<div class="${classes}" title="${s}">${s.length > 6 ? s.slice(0, 6) : s}</div>`;
    });
    stateDiagram += '</div>';

    // Build NFA transition table
    let transTable = '';
    const transitions = data.transitions || [];
    if (transitions.length > 0) {
        transTable = `
            <table class="transition-table">
                <thead><tr><th>Step</th><th>Symbol</th><th>Active States</th><th>Next States</th><th>Description</th></tr></thead>
                <tbody>
                    ${transitions.slice(0, 20).map(t => `
                        <tr>
                            <td>${t.step}</td>
                            <td><code>${t.symbol}</code></td>
                            <td>{${(t.from_states || []).join(', ')}}</td>
                            <td>{${(t.to_states || []).join(', ')}}</td>
                            <td>${t.description}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status ${statusClass}">${statusText}</div>
            <h4>${data.demo_type || 'NFA Processing'}</h4>
            <p>${data.description || ''}</p>

            <div class="info-cards">
                <div class="info-card">
                    <div class="info-label">Input</div>
                    <div class="info-value">"${data.input_string}"</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Patterns</div>
                    <div class="info-value">${(data.patterns || []).join(', ')}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Start State</div>
                    <div class="info-value">${data.start_state}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Final States</div>
                    <div class="info-value">{${(data.final_states || []).join(', ') || '∅'}}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Total Steps</div>
                    <div class="info-value">${data.total_steps}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Result</div>
                    <div class="info-value" style="color:${data.accepted ? 'var(--success)' : 'var(--danger)'}">${data.result}</div>
                </div>
            </div>

            <h4>NFA State Diagram</h4>
            ${stateDiagram}

            <h4>NFA Transition Table (Subset Construction)</h4>
            ${transTable}
        </div>
    `;
}


// ============================================================
// REGEX DEMONSTRATION
// ============================================================

async function runRegexDemo() {
    const pattern = document.getElementById('regexPattern')?.value.trim() || '';
    const input = document.getElementById('regexInput')?.value.trim() || '';
    const resultDiv = document.getElementById('regexResult');

    if (!pattern) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter a regex pattern.</p>';
        return;
    }
    if (!input) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter a test input.</p>';
        return;
    }

    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Processing...</div>';

    try {
        const res = await fetch('/api/demo/regex', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ pattern, input_string: input })
        });
        const data = await res.json();

        if (data.error && data.result === 'INVALID REGEX') {
            resultDiv.innerHTML = `<p style="color:var(--danger);">Invalid regex: ${data.error}</p>`;
            return;
        }

        renderRegexResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderRegexResult(container, data) {
    const statusClass = data.is_match ? 'accepted' : 'rejected';
    const statusText = data.is_match ? '✓ MATCH FOUND' : '✗ NO MATCH';

    // Highlight matches in the input text
    let highlightedText = data.input_text;
    if (data.matches && data.matches.length > 0) {
        // Sort matches by position descending to replace from end
        const sorted = [...data.matches].sort((a, b) => b.start_pos - a.start_pos);
        sorted.forEach(m => {
            const before = highlightedText.slice(0, m.start_pos);
            const match = highlightedText.slice(m.start_pos, m.end_pos);
            const after = highlightedText.slice(m.end_pos);
            highlightedText = `${before}<mark style="background:#bbf7d0;padding:1px 3px;border-radius:3px;">${match}</mark>${after}`;
        });
    }

    let matchDetails = '';
    if (data.matches && data.matches.length > 0) {
        matchDetails = `
            <table class="transition-table">
                <thead><tr><th>#</th><th>Matched Text</th><th>Position</th><th>Span</th></tr></thead>
                <tbody>
                    ${data.matches.map((m, i) => `
                        <tr>
                            <td>${i + 1}</td>
                            <td><code>"${m.matched_text}"</code></td>
                            <td>${m.start_pos} - ${m.end_pos}</td>
                            <td>${m.span}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status ${statusClass}">${statusText}</div>
            <h4>${data.demo_type || 'Regex Matching'}</h4>

            <div class="info-cards">
                <div class="info-card">
                    <div class="info-label">Pattern</div>
                    <div class="info-value"><code>${data.pattern}</code></div>
                </div>
                <div class="info-card">
                    <div class="info-label">Flags</div>
                    <div class="info-value">${data.regex_flags}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Match Count</div>
                    <div class="info-value">${data.match_count}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Result</div>
                    <div class="info-value" style="color:${data.is_match ? 'var(--success)' : 'var(--danger)'}">${data.result}</div>
                </div>
            </div>

            <h4>Highlighted Matches</h4>
            <div style="background:#fff;padding:1rem;border-radius:var(--radius);border:1px solid var(--border);font-size:1rem;line-height:1.8;">
                ${highlightedText}
            </div>

            ${matchDetails ? '<h4>Match Details</h4>' + matchDetails : ''}
        </div>
    `;
}


// ============================================================
// SEARCH PATTERN DEMONSTRATION
// ============================================================

async function runSearchPatternDemo() {
    const query = document.getElementById('searchPatternQuery')?.value.trim() || '';
    const resultDiv = document.getElementById('searchPatternResult');

    if (!query) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter a search query.</p>';
        return;
    }

    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Processing...</div>';

    try {
        const res = await fetch('/api/demo/search-pattern', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();

        if (data.error) {
            resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${data.error}</p>`;
            return;
        }

        renderSearchPatternResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderSearchPatternResult(container, data) {
    const matched = data.matched_products || [];
    const dfaMatches = data.dfa_matches || [];
    const regexResult = data.regex_result || {};

    let matchedProductsHtml = '';
    if (matched.length > 0) {
        matchedProductsHtml = `
            <h4>✓ Matched Products (${matched.length})</h4>
            <ul style="list-style:none;padding:0;">
                ${matched.map(p => `<li style="padding:4px 0;color:var(--success);">✓ ${p}</li>`).join('')}
            </ul>
        `;
    }

    let dfaDetailsHtml = '';
    if (dfaMatches.length > 0) {
        dfaDetailsHtml = `
            <h4>DFA Matching Details (top matches)</h4>
            <table class="transition-table">
                <thead><tr><th>Keyword</th><th>Product</th><th>Final State</th><th>Steps</th><th>Result</th></tr></thead>
                <tbody>
                    ${dfaMatches.slice(0, 10).map(d => `
                        <tr>
                            <td>${d.keyword}</td>
                            <td>${d.product}</td>
                            <td>${d.final_state || '-'}</td>
                            <td>${d.steps || '-'}</td>
                            <td style="color:var(--success);">✓ Accepted</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    let regexDetailsHtml = '';
    if (regexResult.results && regexResult.results.length > 0) {
        regexDetailsHtml = `
            <h4>Regex Matching Details</h4>
            <p><strong>Pattern used:</strong> <code>${regexResult.regex_used || regexResult.pattern}</code></p>
            <table class="transition-table">
                <thead><tr><th>Product</th><th>Matches</th><th>Keywords Found</th></tr></thead>
                <tbody>
                    ${regexResult.results.slice(0, 10).map(r => `
                        <tr>
                            <td>${r.product_name}</td>
                            <td>${r.match_count}</td>
                            <td>${r.matched_keywords.join(', ')}</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }

    container.innerHTML = `
        <div class="demo-result">
            <h4>Search Pattern Analysis for "${data.query}"</h4>

            <div class="info-cards">
                <div class="info-card">
                    <div class="info-label">Query</div>
                    <div class="info-value">"${data.query}"</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Keywords</div>
                    <div class="info-value">[${(data.keywords || []).join(', ')}]</div>
                </div>
                <div class="info-card">
                    <div class="info-label">DFA Matches</div>
                    <div class="info-value">${dfaMatches.length}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Total Matched</div>
                    <div class="info-value">${matched.length}</div>
                </div>
            </div>

            ${matchedProductsHtml}
            ${dfaDetailsHtml}
            ${regexDetailsHtml}
        </div>
    `;
}


// ============================================================
// DFA DEMO TYPE TOGGLE
// ============================================================

function toggleDFAInputs() {
    const demoType = document.getElementById('dfaDemoType')?.value;
    const patternGroup = document.getElementById('dfaPatternGroup');

    if (patternGroup) {
        patternGroup.style.display = demoType === 'pattern' ? 'block' : 'none';
    }

    // Update placeholder
    const input = document.getElementById('dfaInput');
    if (input) {
        switch (demoType) {
            case 'email':
                input.placeholder = 'e.g., user@example.com';
                break;
            case 'product_code':
                input.placeholder = 'e.g., AB123 or XYZ4567';
                break;
            default:
                input.placeholder = 'e.g., smartphone galaxy pro';
        }
    }
}


// ============================================================
// TAB SWITCHING
// ============================================================

function switchTab(tabId) {
    // Deactivate all tabs and content
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

    // Activate selected tab
    document.querySelector(`[data-tab="${tabId}"]`)?.classList.add('active');
    document.getElementById(tabId)?.classList.add('active');
}


// ============================================================
// RESET FUNCTIONS
// ============================================================

function resetDFADemo() {
    document.getElementById('dfaPattern').value = '';
    document.getElementById('dfaInput').value = '';
    document.getElementById('dfaResult').innerHTML = '';
}

function resetNFADemo() {
    document.getElementById('nfaPatterns').value = '';
    document.getElementById('nfaInput').value = '';
    document.getElementById('nfaResult').innerHTML = '';
}

function resetRegexDemo() {
    document.getElementById('regexPattern').value = '';
    document.getElementById('regexInput').value = '';
    document.getElementById('regexResult').innerHTML = '';
}

function resetSearchPatternDemo() {
    document.getElementById('searchPatternQuery').value = '';
    document.getElementById('searchPatternResult').innerHTML = '';
}


// ============================================================
// CONTEXT-FREE GRAMMAR (CFG) DEMONSTRATION
// ============================================================

function setCFGQuery(query) {
    const input = document.getElementById('cfgQueryInput');
    if (input) {
        input.value = query;
        runCFGDemo();
    }
}

async function runCFGDemo() {
    const query = document.getElementById('cfgQueryInput')?.value.trim() || '';
    const resultDiv = document.getElementById('cfgResult');

    if (!query) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter a natural language query.</p>';
        return;
    }

    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Deriving sentence with Context-Free Grammar...</div>';

    try {
        const res = await fetch('/api/demo/cfg', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();

        if (data.error) {
            resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${data.error}</p>`;
            return;
        }

        renderCFGResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderCFGResult(container, data) {
    const parse = data.parse_result || {};
    const success = parse.success;
    const cond = parse.conditions || {};
    const products = data.matching_products || [];

    const statusClass = success ? 'accepted' : 'rejected';
    const statusText = success ? '✓ PARSE SUCCESSFUL (Accepted by CFG)' : '✗ SYNTAX ERROR (Rejected by CFG)';

    // Tokens Table
    let tokensHtml = '';
    if (parse.tokens && parse.tokens.length > 0) {
        tokensHtml = `
            <h4>1. Recognized Tokens & POS Classification</h4>
            <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:1rem;">
                ${parse.tokens.map(t => `
                    <span style="background:#e0f2fe; border:1px solid #bae6fd; padding:4px 10px; border-radius:6px; font-size:0.85rem;">
                        <strong style="color:var(--primary-dark);">${t.type}</strong>: "<em>${t.text}</em>"
                    </span>
                `).join('')}
            </div>
        `;
    }

    // Rules Applied
    let rulesHtml = '';
    if (parse.grammar_rules && parse.grammar_rules.length > 0) {
        rulesHtml = `
            <h4>2. Production Rules Applied in Derivation</h4>
            <div style="margin-bottom:1rem;">
                ${parse.grammar_rules.map(r => `<span class="cfg-rule-badge">${r}</span>`).join(' ')}
            </div>
        `;
    }

    // Conditions Table
    let conditionsHtml = `
        <h4>3. Extracted Semantic Database Constraints</h4>
        <div class="cfg-condition-card">
            ${cond.category ? `<span class="badge badge-primary">📁 Category: <strong>${cond.category}</strong></span>` : ''}
            ${cond.brand ? `<span class="badge badge-primary">🏷️ Brand: <strong>${cond.brand}</strong></span>` : ''}
            ${cond.max_price ? `<span class="badge badge-success">💰 Max Price: <strong>₹${Math.round(cond.max_price).toLocaleString('en-IN')}</strong></span>` : ''}
            ${cond.min_price ? `<span class="badge badge-success">💰 Min Price: <strong>₹${Math.round(cond.min_price).toLocaleString('en-IN')}</strong></span>` : ''}
            ${cond.min_rating ? `<span class="badge badge-warning">⭐ Min Rating: <strong>${cond.min_rating}+</strong></span>` : ''}
            ${cond.specs && cond.specs.length > 0 ? `<span class="badge badge-primary">⚙️ Specs: <strong>${cond.specs.join(', ')}</strong></span>` : ''}
            ${!cond.category && !cond.brand && !cond.max_price && !cond.min_price && !cond.min_rating && (!cond.specs || cond.specs.length === 0) ? '<span style="color:var(--text-muted);">No explicit filters extracted</span>' : ''}
        </div>
    `;

    // Matched Products
    let productsHtml = '';
    if (products.length > 0) {
        productsHtml = `
            <h4 style="margin-top:1.25rem;">4. Live Database Matching Products (${products.length})</h4>
            <div style="display:grid; grid-template-columns:repeat(auto-fill, minmax(220px, 1fr)); gap:12px; margin-top:0.5rem;">
                ${products.map(p => `
                    <div style="background:#fff; border:1px solid var(--border); border-radius:var(--radius); padding:10px; display:flex; gap:10px; align-items:center;">
                        <img src="${p.image_url}" alt="${p.product_name}" style="width:48px; height:48px; object-fit:contain; border-radius:4px; background:#f8fafc;" onerror="this.src='/static/images/product-placeholder.svg'">
                        <div style="font-size:0.8rem;">
                            <a href="/product/${p.product_id}" style="font-weight:700; color:var(--text-primary); text-decoration:none;">${p.product_name}</a>
                            <div style="color:var(--primary-dark); font-weight:600;">₹${Math.round(p.price).toLocaleString('en-IN')}</div>
                            <div style="color:#f59e0b;">★ ${p.rating}</div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    } else if (success) {
        productsHtml = `
            <div style="margin-top:1rem; padding:12px; background:#fef3c7; border:1px solid #fde68a; border-radius:var(--radius); font-size:0.85rem; color:#92400e;">
                ℹ️ Query parsed successfully, but no items in the catalog currently match all criteria.
            </div>
        `;
    }

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status ${statusClass}">${statusText}</div>
            <h4 style="margin-top:0.5rem;">Input Sentence: "<em>${data.query}</em>"</h4>

            ${tokensHtml}
            ${rulesHtml}

            <h4>Parse Tree (Hierarchical Derivation Representation)</h4>
            <pre class="cfg-tree-pre">${parse.text_tree || 'No parse tree available'}</pre>

            ${conditionsHtml}
            ${productsHtml}
        </div>
    `;
}

function resetCFGDemo() {
    const input = document.getElementById('cfgQueryInput');
    const result = document.getElementById('cfgResult');
    if (input) input.value = '';
    if (result) result.innerHTML = '';
}


// ============================================================
// TAB 6: SEARCH INTENT FSM DEMONSTRATION
// ============================================================

function setIntentSequence(queries) {
    const input = document.getElementById('intentQueriesInput');
    if (input) input.value = queries.join(', ');
    runIntentDemo();
}

async function runIntentDemo() {
    const input = document.getElementById('intentQueriesInput')?.value.trim();
    const resultDiv = document.getElementById('intentResult');
    if (!resultDiv) return;

    if (!input) {
        resultDiv.innerHTML = '<p style="color:var(--danger);">Please enter a sequence of queries.</p>';
        return;
    }

    const queries = input.split(',').map(q => q.trim()).filter(Boolean);
    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Tracing Search Intent FSM Transitions...</div>';

    try {
        const res = await fetch('/api/demo/search-intent', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ queries })
        });
        const data = await res.json();
        renderIntentResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderIntentResult(container, data) {
    const journey = data.journey || [];
    const fsm = data.fsm_definition || {};

    const stateNodesHtml = journey.map((step, idx) => {
        const isCurrent = idx === journey.length - 1;
        return `
            <div class="fsm-step-card ${isCurrent ? 'active-step' : ''}">
                <div class="fsm-step-header">
                    <span class="fsm-step-num">Step ${idx + 1}</span>
                    <span class="fsm-state-badge">${step.current_state}</span>
                </div>
                <div class="fsm-query-text">"${step.query}"</div>
                <div class="fsm-transition-tag">Transition: <strong>${step.transition}</strong> (${step.previous_state} ➔ ${step.current_state})</div>
                <div class="fsm-step-desc">${step.transition_description}</div>
                <div class="fsm-attributes-detail">
                    ${step.attributes.categories.length ? `<span class="attr-pill cat">📁 ${step.attributes.categories.join(', ')}</span>` : ''}
                    ${step.attributes.brands.length ? `<span class="attr-pill brand">🏷️ ${step.attributes.brands.join(', ')}</span>` : ''}
                    ${step.attributes.specs.length ? `<span class="attr-pill spec">🔧 ${step.attributes.specs.join(', ')}</span>` : ''}
                    ${step.attributes.has_price ? `<span class="attr-pill price">💰 Price Filter</span>` : ''}
                </div>
            </div>
        `;
    }).join('<div class="fsm-arrow">➔</div>');

    const tableRows = (fsm.transitions || []).slice(0, 15).map(t => `
        <tr>
            <td><code>${t.from}</code></td>
            <td><strong>${t.input}</strong></td>
            <td><code>${t.to}</code></td>
        </tr>
    `).join('');

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status accepted">✓ FSM SIMULATION COMPLETE — FINAL STATE: ${data.current_state}</div>
            <p style="margin: 0.5rem 0 1.25rem 0; color:var(--text-secondary);">${data.state_description}</p>

            <h4>Search Progression State Trace</h4>
            <div class="fsm-timeline-container">
                ${stateNodesHtml}
            </div>

            <h4 style="margin-top:1.5rem;">Finite-State Automaton Transition Matrix (Sample)</h4>
            <table class="transition-table">
                <thead><tr><th>Current State \(q\)</th><th>Input Symbol / Action \(\sigma\)</th><th>Next State \(\delta(q, \sigma)\)</th></tr></thead>
                <tbody>${tableRows}</tbody>
            </table>
        </div>
    `;
}

function resetIntentDemo() {
    const input = document.getElementById('intentQueriesInput');
    const result = document.getElementById('intentResult');
    if (input) input.value = '';
    if (result) result.innerHTML = '';
}


// ============================================================
// TAB 7: TYPO CORRECTION & LEVENSHTEIN DEMO
// ============================================================

function setTypoPair(src, tgt) {
    const srcInput = document.getElementById('typoSourceInput');
    const tgtInput = document.getElementById('typoTargetInput');
    if (srcInput) srcInput.value = src;
    if (tgtInput) tgtInput.value = tgt;
    runTypoDemo();
}

async function runTypoDemo() {
    const source = document.getElementById('typoSourceInput')?.value.trim() || 'samsng';
    const target = document.getElementById('typoTargetInput')?.value.trim() || 'Samsung';
    const resultDiv = document.getElementById('typoResult');

    if (!resultDiv) return;
    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Computing Levenshtein Matrix...</div>';

    try {
        const res = await fetch('/api/demo/typo-correction', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ source, target })
        });
        const data = await res.json();
        renderTypoResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderTypoResult(container, data) {
    const matrix = data.matrix || [];
    const rows = data.matrix_labels?.rows || [];
    const cols = data.matrix_labels?.cols || [];

    let matrixHtml = '<table class="dp-matrix-table">';
    // Header row
    matrixHtml += '<thead><tr><th></th><th>ε</th>';
    for (let j = 1; j < cols.length; j++) {
        matrixHtml += `<th>${cols[j]}</th>`;
    }
    matrixHtml += '</tr></thead><tbody>';

    // Body rows
    for (let i = 0; i < matrix.length; i++) {
        matrixHtml += `<tr><th>${i === 0 ? 'ε' : rows[i]}</th>`;
        for (let j = 0; j < matrix[i].length; j++) {
            const isFinal = (i === matrix.length - 1 && j === matrix[i].length - 1);
            matrixHtml += `<td class="${isFinal ? 'dp-final-cell' : ''}">${matrix[i][j]}</td>`;
        }
        matrixHtml += '</tr>';
    }
    matrixHtml += '</tbody></table>';

    // Operations list
    const ops = data.operations || [];
    const opsHtml = ops.map(op => {
        let badgeClass = 'badge-primary';
        let symbol = '✓';
        if (op.type === 'substitute') { badgeClass = 'badge-warning'; symbol = '✏️ Sub'; }
        else if (op.type === 'insert') { badgeClass = 'badge-success'; symbol = '+ Ins'; }
        else if (op.type === 'delete') { badgeClass = 'badge-danger'; symbol = '- Del'; }
        else { badgeClass = 'badge-info'; symbol = '= Match'; }

        return `
            <div class="dp-op-item">
                <span class="dp-op-badge ${op.type}">${symbol}</span>
                <span>${op.type.toUpperCase()}: <code>'${op.from_char || ''}'</code> ➔ <code>'${op.to_char || ''}'</code></span>
            </div>
        `;
    }).join('');

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status accepted">
                EDIT DISTANCE: ${data.distance} | SIMILARITY: ${(data.similarity * 100).toFixed(1)}%
            </div>
            <p style="margin:0.5rem 0 1.25rem 0; color:var(--text-secondary);">${data.explanation}</p>

            <div class="info-cards" style="margin-bottom:1.5rem;">
                <div class="info-card">
                    <div class="info-label">Substitutions</div>
                    <div class="info-value">${data.operation_summary.substitutions}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Insertions</div>
                    <div class="info-value">${data.operation_summary.insertions}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Deletions</div>
                    <div class="info-value">${data.operation_summary.deletions}</div>
                </div>
                <div class="info-card">
                    <div class="info-label">Character Matches</div>
                    <div class="info-value">${data.operation_summary.matches}</div>
                </div>
            </div>

            <h4>Dynamic Programming Edit Distance Matrix</h4>
            <div style="overflow-x:auto; margin-bottom:1.5rem;">
                ${matrixHtml}
            </div>

            <h4>Optimal Alignment Operations</h4>
            <div class="dp-ops-container">
                ${opsHtml}
            </div>

            <div class="automata-debug" style="margin-top:1.5rem;">
                <h4>🔬 Theory of Computation Connection: Finite Transducers</h4>
                <p style="margin:0; font-size:0.88rem; line-height:1.6;">
                    ${data.toc_context?.relation_to_automata || ''}
                </p>
            </div>
        </div>
    `;
}

function resetTypoDemo() {
    const src = document.getElementById('typoSourceInput');
    const tgt = document.getElementById('typoTargetInput');
    const res = document.getElementById('typoResult');
    if (src) src.value = '';
    if (tgt) tgt.value = '';
    if (res) res.innerHTML = '';
}


// ============================================================
// TAB 8: ADAPTIVE FILTER AUTOMATON DEMO
// ============================================================

async function runFilterDemo() {
    const category = document.getElementById('filterDemoCategory')?.value || 'Laptops';
    const brand = document.getElementById('filterDemoBrand')?.value.trim() || '';
    const resultDiv = document.getElementById('filterResult');

    if (!resultDiv) return;
    resultDiv.innerHTML = '<div class="loading"><div class="spinner"></div> Computing Adaptive Filter Automaton...</div>';

    try {
        const applied = { category };
        if (brand) applied.brand = brand;

        const res = await fetch('/api/demo/filter-advisor', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ category, applied_filters: applied })
        });
        const data = await res.json();
        renderFilterResult(resultDiv, data);
    } catch (err) {
        resultDiv.innerHTML = `<p style="color:var(--danger);">Error: ${err.message}</p>`;
    }
}

function renderFilterResult(container, data) {
    const aut = data.automaton || {};
    const catAttrs = data.category_attributes || {};
    const transitions = aut.transitions || [];

    const transRows = transitions.slice(0, 12).map(t => `
        <tr>
            <td><code>${t.from_state}</code></td>
            <td><strong>${t.action}</strong></td>
            <td><code>${t.to_state}</code></td>
        </tr>
    `).join('');

    let specGroupsHtml = '';
    if (catAttrs.filter_keywords) {
        specGroupsHtml = Object.entries(catAttrs.filter_keywords).map(([group, keywords]) => `
            <div style="margin-bottom:8px;">
                <strong>${group}:</strong>
                <span style="color:var(--text-secondary); font-size:0.85rem;">[${keywords.join(', ')}]</span>
            </div>
        `).join('');
    }

    container.innerHTML = `
        <div class="demo-result">
            <div class="result-status accepted">✓ MEALY MACHINE FILTER STATE ACTIVE</div>
            <p style="margin:0.5rem 0 1rem 0; color:var(--text-secondary);">
                Active Context: <strong>Category = ${data.category}</strong> | Simulated Applied Filters = <code>${JSON.stringify(data.applied_filters)}</code>
            </p>

            <h4>Extracted Specifications for Context (${data.category})</h4>
            <div style="background:var(--card-bg); padding:1rem; border-radius:var(--radius); border:1px solid var(--border); margin-bottom:1.5rem;">
                ${specGroupsHtml}
            </div>

            <h4>Adaptive Filter Automaton Transition Table</h4>
            <table class="transition-table">
                <thead><tr><th>Current Filter State</th><th>User Action / Applied Filter</th><th>Next Filter State</th></tr></thead>
                <tbody>${transRows}</tbody>
            </table>

            <div class="automata-debug" style="margin-top:1.5rem;">
                <h4>🔬 Formal Automata Description</h4>
                <p style="margin:0; font-size:0.88rem; line-height:1.6;">
                    ${data.toc_context?.description || ''}
                </p>
            </div>
        </div>
    `;
}

function resetFilterDemo() {
    const res = document.getElementById('filterResult');
    if (res) res.innerHTML = '';
}

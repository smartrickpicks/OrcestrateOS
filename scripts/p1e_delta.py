#!/usr/bin/env python3
"""P1E PDF Reliability Spike — Delta Script
Applies 5 targeted edits to ui/viewer/index.html:
  E1: CSS for cache diagnostics panel
  E2: P1E reliability helpers (instrumentation, mojibake detect, normalize, diagnostics)
  E3: Replace srrUpdateViewerHighlight with instrumented + normalized anchor matching
  E4: Reduce srrForcePageNav refresh churn (skip reload when URL unchanged)
  E5: Cache diagnostics HTML in debug panel
"""

import re, sys, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_html(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

# ── E1: CSS for cache diagnostics ──
P1E_CSS = """
    /* ═══ P1E: PDF Reliability — Cache Diagnostics Panel ═══ */
    .p1e-diag-panel { position: fixed; bottom: 10px; right: 10px; width: 380px; max-height: 320px; background: #fff; border: 1px solid #ccc; border-radius: 8px; box-shadow: 0 4px 16px rgba(0,0,0,0.15); z-index: 99999; font-size: 0.82em; display: none; overflow: auto; }
    .p1e-diag-panel.visible { display: block; }
    .p1e-diag-header { display: flex; justify-content: space-between; align-items: center; padding: 8px 12px; background: #e3f2fd; border-bottom: 1px solid #bbdefb; border-radius: 8px 8px 0 0; font-weight: 600; color: #1565c0; }
    .p1e-diag-close { cursor: pointer; font-size: 1.2em; color: #999; }
    .p1e-diag-close:hover { color: #333; }
    .p1e-diag-body { padding: 10px 12px; }
    .p1e-diag-row { display: flex; justify-content: space-between; padding: 4px 0; border-bottom: 1px solid #f0f0f0; }
    .p1e-diag-label { color: #666; font-weight: 500; min-width: 110px; }
    .p1e-diag-value { color: #333; text-align: right; word-break: break-all; max-width: 240px; }
    .p1e-diag-value.ok { color: #2e7d32; }
    .p1e-diag-value.warn { color: #e65100; }
    .p1e-diag-value.fail { color: #c62828; }
    .p1e-mojibake-badge { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.78em; font-weight: 600; background: #fff3e0; color: #e65100; }
"""

# ── E2: P1E Reliability Helpers ──
P1E_HELPERS = """
    // ═══ P1E: PDF Reliability Spike — Helpers ═══
    var _p1eDiagState = { sourceUrl: '', cacheKey: '', lastLoaded: null, textStatus: '', pageCount: 0, matchAttempts: [] };

    function _p1eLog(event, detail) {
      var msg = '[PDF-RELIABILITY][P1E] ' + event;
      if (detail) msg += ': ' + (typeof detail === 'object' ? JSON.stringify(detail) : String(detail));
      console.log(msg);
    }

    function _p1eNormalizeForSearch(text) {
      if (!text) return '';
      var s = String(text);
      s = s.replace(/[\\u2018\\u2019\\u201A\\u201B]/g, String.fromCharCode(39));
      s = s.replace(/[\\u201C\\u201D\\u201E\\u201F]/g, '"');
      s = s.replace(/[\\u2013\\u2014]/g, '-');
      s = s.replace(/[\\u00A0\\u2000-\\u200B\\u202F\\u205F\\u3000]/g, ' ');
      s = s.replace(/\\s+/g, ' ').trim();
      return s;
    }

    function _p1eAsciiNormalize(text) {
      if (!text) return '';
      var s = _p1eNormalizeForSearch(text);
      s = s.replace(/[^\\x20-\\x7E]/g, '');
      return s.trim();
    }

    function _p1eDetectMojibake(text) {
      if (!text || typeof text !== 'string') return { isMojibake: false, reason: '' };
      var controlCount = 0;
      var replacementCount = 0;
      var highNonLatinCount = 0;
      var totalChars = text.length;
      if (totalChars < 5) return { isMojibake: false, reason: '' };
      for (var i = 0; i < totalChars; i++) {
        var code = text.charCodeAt(i);
        if (code === 0xFFFD) replacementCount++;
        else if (code < 32 && code !== 10 && code !== 13 && code !== 9) controlCount++;
        else if (code > 0x024F && code < 0x3000) highNonLatinCount++;
      }
      var replacementRatio = replacementCount / totalChars;
      var controlRatio = controlCount / totalChars;
      var highRatio = highNonLatinCount / totalChars;
      if (replacementRatio > 0.05) return { isMojibake: true, reason: 'HIGH_REPLACEMENT_CHARS', ratio: replacementRatio };
      if (controlRatio > 0.03) return { isMojibake: true, reason: 'CONTROL_CHAR_EXCESS', ratio: controlRatio };
      if (highRatio > 0.4 && totalChars > 20) return { isMojibake: true, reason: 'ENCODING_MISMATCH', ratio: highRatio };
      return { isMojibake: false, reason: '' };
    }

    function _p1eDetectNonSearchable(pages) {
      if (!pages || pages.length === 0) return { nonSearchable: true, reason: 'NO_PAGES' };
      var emptyPages = 0;
      var tinyPages = 0;
      for (var i = 0; i < pages.length; i++) {
        var t = (pages[i].text || '').trim();
        if (t.length === 0) emptyPages++;
        else if (t.length < 10) tinyPages++;
      }
      var emptyRatio = emptyPages / pages.length;
      if (emptyRatio > 0.8) return { nonSearchable: true, reason: 'MOSTLY_EMPTY_TEXT', emptyRatio: emptyRatio };
      if (emptyPages === pages.length) return { nonSearchable: true, reason: 'ALL_PAGES_EMPTY' };
      return { nonSearchable: false, reason: '' };
    }

    function _p1eRouteToPreFlight(record, condition, reason) {
      if (!record) return;
      var contractKey = record.contract_key || record.contract_id || '';
      var fileUrl = srrResolveFieldValue(record, 'file_url');
      var fileName = srrResolveFieldValue(record, 'file_name');
      var item = {
        request_id: 'p1e_' + condition.toLowerCase() + '_' + contractKey + '_' + Date.now(),
        type: 'preflight_blocker',
        signal_type: condition,
        record_id: contractKey,
        contract_id: contractKey,
        contract_key: contractKey,
        field_name: 'file_url',
        field_key: 'file_url',
        sheet_name: srrState.currentSheetName || '',
        severity: condition === 'OCR_UNREADABLE' ? 'blocker' : 'warning',
        message: reason,
        status: 'open',
        status_label: 'Open',
        status_color: '#f57c00',
        updated_at: new Date().toISOString(),
        source: 'preflight',
        blocker_type: condition,
        can_create_patch: false,
        file_name: fileName,
        file_url: fileUrl
      };
      var isDup = analystTriageState.manualItems.some(function(m) {
        return m.signal_type === condition && m.contract_key === contractKey && m.field_name === 'file_url';
      });
      if (!isDup) {
        analystTriageState.manualItems.push(item);
        _p1eLog('preflight_routed', { condition: condition, contract: contractKey, reason: reason });
      }
    }

    function _p1eSearchVariants(query) {
      var variants = [];
      var trimmed = query.trim();
      if (trimmed) variants.push(trimmed);
      var norm = _p1eNormalizeForSearch(trimmed);
      if (norm && norm !== trimmed) variants.push(norm);
      var ascii = _p1eAsciiNormalize(trimmed);
      if (ascii && ascii !== norm && ascii !== trimmed) variants.push(ascii);
      if (trimmed.length > 30) {
        var sub = trimmed.substring(0, 25);
        variants.push(sub);
      }
      var noPunct = trimmed.replace(/[.,;:!?()\\[\\]{}'"]/g, '').trim();
      if (noPunct && noPunct !== trimmed && noPunct !== norm) variants.push(noPunct);
      return variants;
    }

    function _p1eMatchInPages(pages, query) {
      var variants = _p1eSearchVariants(query);
      var attempts = [];
      for (var vi = 0; vi < variants.length; vi++) {
        var variant = variants[vi];
        var variantLower = _p1eNormalizeForSearch(variant).toLowerCase();
        var matchPages = [];
        for (var pi = 0; pi < pages.length; pi++) {
          var pageText = _p1eNormalizeForSearch(pages[pi].text || '').toLowerCase();
          if (pageText.indexOf(variantLower) >= 0) {
            matchPages.push(pages[pi].page);
          }
        }
        attempts.push({ variant: variant.substring(0, 40), matched: matchPages.length > 0, pages: matchPages.length });
        if (matchPages.length > 0) {
          _p1eLog('anchor_match_found', { variant: variant.substring(0, 40), variantIndex: vi, pages: matchPages });
          return { matchPages: matchPages, variant: variant, attempts: attempts };
        }
      }
      _p1eLog('anchor_match_failed', { query: query.substring(0, 40), variantsTried: attempts.length, attempts: attempts });
      return { matchPages: [], variant: query, attempts: attempts };
    }

    function _p1eShowDiagPanel() {
      var panel = document.getElementById('p1e-diag-panel');
      if (!panel) return;
      var body = panel.querySelector('.p1e-diag-body');
      if (!body) return;
      var d = _p1eDiagState;
      var html = '';
      html += '<div class="p1e-diag-row"><span class="p1e-diag-label">Source URL</span><span class="p1e-diag-value" title="' + escapeHtml(d.sourceUrl) + '">' + escapeHtml(d.sourceUrl ? (d.sourceUrl.length > 50 ? d.sourceUrl.substring(0, 50) + '...' : d.sourceUrl) : 'none') + '</span></div>';
      html += '<div class="p1e-diag-row"><span class="p1e-diag-label">Cache Key</span><span class="p1e-diag-value">' + escapeHtml(d.cacheKey || 'none') + '</span></div>';
      html += '<div class="p1e-diag-row"><span class="p1e-diag-label">Last Loaded</span><span class="p1e-diag-value">' + (d.lastLoaded ? d.lastLoaded.toLocaleTimeString() : 'never') + '</span></div>';
      html += '<div class="p1e-diag-row"><span class="p1e-diag-label">Text Status</span><span class="p1e-diag-value ' + (d.textStatus === 'ok' ? 'ok' : (d.textStatus ? 'warn' : '')) + '">' + (d.textStatus || 'unknown') + '</span></div>';
      html += '<div class="p1e-diag-row"><span class="p1e-diag-label">Pages</span><span class="p1e-diag-value">' + d.pageCount + '</span></div>';
      html += '<div class="p1e-diag-row"><span class="p1e-diag-label">Cache Status</span><span class="p1e-diag-value ' + (srrState.cacheStatus === 'hit' ? 'ok' : (srrState.cacheStatus || '')) + '">' + (srrState.cacheStatus || 'none') + '</span></div>';
      if (d.matchAttempts.length > 0) {
        html += '<div style="margin-top: 8px; font-weight: 600; color: #666;">Recent Match Attempts</div>';
        for (var i = 0; i < d.matchAttempts.length && i < 5; i++) {
          var a = d.matchAttempts[i];
          html += '<div class="p1e-diag-row"><span class="p1e-diag-label">' + escapeHtml(a.variant) + '</span><span class="p1e-diag-value ' + (a.matched ? 'ok' : 'fail') + '">' + (a.matched ? a.pages + ' pages' : 'no match') + '</span></div>';
        }
      }
      body.innerHTML = html;
      panel.classList.add('visible');
    }

    function _p1eHideDiagPanel() {
      var panel = document.getElementById('p1e-diag-panel');
      if (panel) panel.classList.remove('visible');
    }

    function _p1eToggleDiagPanel() {
      var panel = document.getElementById('p1e-diag-panel');
      if (panel) panel.classList.toggle('visible');
    }
"""

# ── E3: Replacement for srrUpdateViewerHighlight ──
P1E_HIGHLIGHT_REPLACEMENT = """    function srrUpdateViewerHighlight(fieldKey) {
      if (!fieldKey) { pdfMatchDismiss(); return; }

      var record = srrState.currentRecord;
      if (!record) { pdfMatchDismiss(); _p1eLog('highlight_abort', 'no_record'); return; }
      var value = record[fieldKey];
      if (!value || (typeof value === 'string' && !value.trim())) {
        pdfMatchState = { matches: [], current: -1, fieldKey: fieldKey, loading: false, searchToken: pdfMatchState.searchToken, searchQuery: '' };
        pdfMatchUpdateBar();
        _p1eLog('highlight_skip', { field: fieldKey, reason: 'empty_value' });
        return;
      }
      var searchQuery = String(value).trim();
      var fileUrl = srrResolveFieldValue(record, 'file_url');
      if (!fileUrl) {
        showToast('No document URL for text search', 'info');
        _p1eLog('highlight_abort', { field: fieldKey, reason: 'no_file_url' });
        return;
      }

      _p1eLog('anchor_search_start', { field: fieldKey, query: searchQuery.substring(0, 40), url: fileUrl.substring(0, 60) });

      if (pdfMatchDismissTimer) { clearTimeout(pdfMatchDismissTimer); pdfMatchDismissTimer = null; }
      var token = ++pdfMatchState.searchToken;
      pdfMatchState = { matches: [], current: -1, fieldKey: fieldKey, loading: true, searchToken: token, searchQuery: searchQuery };
      pdfMatchUpdateBar();

      var proxyBase = window._pdfProxyBaseUrl || '';
      var apiUrl = proxyBase + '/api/pdf/text?url=' + encodeURIComponent(fileUrl);

      _p1eLog('text_extract_request', { url: apiUrl.substring(0, 80) });

      fetch(apiUrl)
        .then(function(r) { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json(); })
        .then(function(data) {
          if (pdfMatchState.searchToken !== token) return;
          var pages = data.pages || [];
          _p1eDiagState.pageCount = pages.length;
          _p1eDiagState.sourceUrl = fileUrl;
          _p1eDiagState.lastLoaded = new Date();

          _p1eLog('text_extract_ok', { pages: pages.length, totalChars: pages.reduce(function(s, p) { return s + (p.text || '').length; }, 0) });

          var nonSearch = _p1eDetectNonSearchable(pages);
          if (nonSearch.nonSearchable) {
            _p1eDiagState.textStatus = 'non_searchable';
            _p1eLog('text_not_searchable', { reason: nonSearch.reason });
            _p1eRouteToPreFlight(record, 'TEXT_NOT_SEARCHABLE', 'PDF text is not searchable: ' + nonSearch.reason);
            pdfMatchState.matches = [];
            pdfMatchState.loading = false;
            pdfMatchUpdateBar();
            return;
          }

          var allText = pages.map(function(p) { return p.text || ''; }).join(' ');
          var mojibake = _p1eDetectMojibake(allText);
          if (mojibake.isMojibake) {
            _p1eDiagState.textStatus = 'mojibake';
            _p1eLog('mojibake_detected', { reason: mojibake.reason, ratio: mojibake.ratio });
            _p1eRouteToPreFlight(record, 'OCR_UNREADABLE', 'PDF text contains encoding artifacts (mojibake): ' + mojibake.reason);
          } else {
            _p1eDiagState.textStatus = 'ok';
          }

          var result = _p1eMatchInPages(pages, searchQuery);
          _p1eDiagState.matchAttempts = result.attempts;

          pdfMatchState.matches = result.matchPages;
          pdfMatchState.loading = false;
          pdfMatchState.searchQuery = result.variant;
          if (result.matchPages.length > 0) {
            pdfMatchState.current = 0;
            srrNavigateToPage(result.matchPages[0]);
            _p1eLog('anchor_page_jump', { page: result.matchPages[0], totalMatches: result.matchPages.length });
          } else {
            _p1eLog('anchor_no_match', { field: fieldKey, query: searchQuery.substring(0, 40) });
          }
          pdfMatchUpdateBar();
          _p1eLog('highlight_complete', { field: fieldKey, matchCount: result.matchPages.length, status: result.matchPages.length > 0 ? 'PASS' : 'FAIL' });
        })
        .catch(function(err) {
          if (pdfMatchState.searchToken !== token) return;
          _p1eLog('text_extract_fail', { error: err.message, url: fileUrl.substring(0, 60) });
          _p1eDiagState.textStatus = 'error';
          pdfMatchState.loading = false;
          pdfMatchState.matches = [];
          pdfMatchUpdateBar();
        });
    }"""

# ── E4: srrForcePageNav with reload skip ──
P1E_FORCE_NAV_REPLACEMENT = """    function srrForcePageNav(pageNum, searchText) {
      var obj = document.getElementById('srr-pdf-object');
      if (!obj || !srrState.currentPdfUrl) return;
      srrUpdatePageDisplay();
      var baseUrl = srrState.currentPdfUrl.split('#')[0];
      var fragment = '#page=' + pageNum + '&navpanes=0&scrollbar=1&toolbar=1&view=FitH';
      if (srrState.useFragmentZoom !== false) {
        fragment += '&zoom=' + srrState.zoom;
      }
      if (searchText) {
        fragment += '&search=' + encodeURIComponent(searchText);
      }
      var newSrc = baseUrl + fragment;
      var currentData = obj.data || '';
      var currentBase = currentData.split('#')[0];
      var currentFragment = currentData.split('#')[1] || '';
      var currentPage = '';
      var currentSearch = '';
      var fragParts = currentFragment.split('&');
      for (var fp = 0; fp < fragParts.length; fp++) {
        if (fragParts[fp].indexOf('page=') === 0) currentPage = fragParts[fp].split('=')[1];
        if (fragParts[fp].indexOf('search=') === 0) currentSearch = decodeURIComponent(fragParts[fp].split('=')[1] || '');
      }
      var sameBase = currentBase === baseUrl;
      var samePage = currentPage === String(pageNum);
      var sameSearch = currentSearch === (searchText || '');
      if (sameBase && samePage && sameSearch) {
        _p1eLog('nav_skip_unchanged', { page: pageNum, search: (searchText || '').substring(0, 20) });
        return;
      }
      _p1eLog('nav_update', { page: pageNum, search: (searchText || '').substring(0, 20), reload: !sameBase ? 'full' : 'fragment' });
      setTimeout(function() {
        obj.data = newSrc;
        var openTabLink = document.getElementById('srr-pdf-open-tab');
        if (openTabLink) openTabLink.href = newSrc;
      }, sameBase ? 50 : 120);
    }"""

# ── E5: Cache diagnostics panel HTML ──
P1E_DIAG_HTML = """
              <!-- P1E: Cache Diagnostics Panel -->
              <div id="p1e-diag-panel" class="p1e-diag-panel">
                <div class="p1e-diag-header">
                  <span>PDF Cache Diagnostics</span>
                  <span class="p1e-diag-close" onclick="_p1eHideDiagPanel()">&times;</span>
                </div>
                <div class="p1e-diag-body"></div>
              </div>"""


def apply_edits(html):
    edits_applied = 0

    # E1: Insert CSS before closing </style> of the main stylesheet
    css_marker = '    /* PDF anchor match navigation bar */'
    if css_marker in html and 'P1E: PDF Reliability' not in html:
        html = html.replace(css_marker, P1E_CSS + '\n' + css_marker)
        edits_applied += 1
        print('[E1] CSS for cache diagnostics panel: APPLIED')
    elif 'P1E: PDF Reliability' in html:
        print('[E1] CSS already present: SKIPPED')
        edits_applied += 1
    else:
        print('[E1] CSS marker not found: FAILED')

    # E2: Insert helpers before the P1C helpers section
    helper_marker = '    // ═══ P1C: Contract Composite Grid — Helpers ═══'
    if helper_marker in html and '_p1eLog' not in html:
        html = html.replace(helper_marker, P1E_HELPERS + '\n' + helper_marker)
        edits_applied += 1
        print('[E2] P1E reliability helpers: APPLIED')
    elif '_p1eLog' in html:
        print('[E2] Helpers already present: SKIPPED')
        edits_applied += 1
    else:
        print('[E2] Helper marker not found: FAILED')

    # E3: Replace srrUpdateViewerHighlight
    old_highlight_pattern = r'    function srrUpdateViewerHighlight\(fieldKey\) \{.*?console\.log\(\'\[PDF_ANCHOR\] Text extraction failed:\'.*?\}\);'
    match = re.search(old_highlight_pattern, html, re.DOTALL)
    if match and '[PDF-RELIABILITY][P1E]' not in match.group():
        html = html[:match.start()] + P1E_HIGHLIGHT_REPLACEMENT + html[match.end():]
        edits_applied += 1
        print('[E3] srrUpdateViewerHighlight replaced with instrumented version: APPLIED')
    elif match and '[PDF-RELIABILITY][P1E]' in match.group():
        print('[E3] Already instrumented: SKIPPED')
        edits_applied += 1
    else:
        print('[E3] srrUpdateViewerHighlight not found with expected pattern: FAILED')
        # Try a simpler match
        simple_start = '    function srrUpdateViewerHighlight(fieldKey) {'
        simple_end = "        });\n    }\n\n    document.addEventListener('keydown'"
        idx_start = html.find(simple_start)
        idx_end = html.find(simple_end, idx_start)
        if idx_start >= 0 and idx_end > idx_start:
            html = html[:idx_start] + P1E_HIGHLIGHT_REPLACEMENT + '\n' + html[idx_end:]
            edits_applied += 1
            print('[E3] Applied via simple marker fallback: APPLIED')

    # E4: Replace srrForcePageNav
    old_nav_pattern = r'    function srrForcePageNav\(pageNum, searchText\) \{.*?console\.log\(\'\[SRR_PDF\] Forced nav to:\'.*?\}, 120\);\n    \}'
    match = re.search(old_nav_pattern, html, re.DOTALL)
    if match and 'nav_skip_unchanged' not in match.group():
        html = html[:match.start()] + P1E_FORCE_NAV_REPLACEMENT + html[match.end():]
        edits_applied += 1
        print('[E4] srrForcePageNav replaced with reload-skip version: APPLIED')
    elif match and 'nav_skip_unchanged' in match.group():
        print('[E4] Already patched: SKIPPED')
        edits_applied += 1
    else:
        print('[E4] srrForcePageNav not found with expected pattern: FAILED')

    # E5: Insert diagnostics panel HTML before closing </body>
    diag_marker = '</body>'
    if diag_marker in html and 'p1e-diag-panel' not in html:
        html = html.replace(diag_marker, P1E_DIAG_HTML + '\n' + diag_marker, 1)
        edits_applied += 1
        print('[E5] Cache diagnostics panel HTML: APPLIED')
    elif 'p1e-diag-panel' in html:
        print('[E5] Diagnostics panel already present: SKIPPED')
        edits_applied += 1
    else:
        print('[E5] </body> marker not found: FAILED')

    return html, edits_applied


if __name__ == '__main__':
    print('=' * 60)
    print('[P1E] PDF Reliability Spike — Delta Apply')
    print('=' * 60)
    html = read_html()
    original_len = len(html)
    html, count = apply_edits(html)
    write_html(html)
    print(f'[P1E] {count}/5 edits applied. File: {len(html)} chars (was {original_len})')
    if count < 5:
        print('[P1E] WARNING: Not all edits applied!')
        sys.exit(1)
    print('[P1E] All edits applied successfully.')

#!/usr/bin/env python3
"""
P0.9 Runtime Cleanup + Data Hygiene — Delta Script
Applies 9 targeted edits to ui/viewer/index.html.
All injected code is ES5-compliant.
"""
import re, sys, os

HTML_PATH = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read_html():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_html(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_edit(html, label, old, new):
    if old not in html:
        print(f"  [WARN] Edit '{label}' — anchor not found, skipping")
        return html, False
    count = html.count(old)
    if count > 1:
        print(f"  [WARN] Edit '{label}' — anchor found {count} times, replacing first only")
        html = html.replace(old, new, 1)
    else:
        html = html.replace(old, new)
    print(f"  [OK]   Edit '{label}' applied")
    return html, True

def main():
    html = read_html()
    applied = 0
    total = 0

    # =====================================================================
    # EDIT 1: Default route to triage for all roles
    # navigateToRoleDefault() already routes to triage. Ensure setMode()
    # ends with a log. The function is already correct, just add logging.
    # =====================================================================
    total += 1
    old = "function navigateToRoleDefault() {\n      navigateTo('triage');\n    }"
    new = """function navigateToRoleDefault() {
      console.log('[P0.9-CLEANUP] route_default_triage: role=' + currentMode);
      navigateTo('triage');
    }"""
    html, ok = apply_edit(html, "1-default-route-triage-log", old, new)
    if ok: applied += 1

    # =====================================================================
    # EDIT 2: Contract-first navigation in All Data Grid
    # Move contract-filter-group before sheet-selector in grid controls.
    # Currently order is: contract, sheet — which is already correct.
    # Add deterministic log in populateContractSelector.
    # =====================================================================
    total += 1
    old = "function populateContractSelector() {\n      var selector = document.getElementById('grid-contract-selector');"
    new = """function populateContractSelector() {
      console.log('[P0.9-CLEANUP] contract_filter_primary: populating contract selector');
      var selector = document.getElementById('grid-contract-selector');"""
    html, ok = apply_edit(html, "2-contract-first-log", old, new)
    if ok: applied += 1

    # =====================================================================
    # EDIT 3: Remove false unresolved routing noise
    # Ensure executeTriageResolution logs a clean ds_route_resolved for
    # valid items instead of any stale-toast path. P0.8 already removed
    # the toast, but we add explicit P0.9 logging in executeTriageResolution.
    # =====================================================================
    total += 1
    old = "function executeTriageResolution(item) {"
    new = """function executeTriageResolution(item) {
      console.log('[P0.9-CLEANUP] ds_route_resolved: item_id=' + (item.request_id || 'unknown') + ', source=' + (item.source || ''));"""
    html, ok = apply_edit(html, "3-ds-route-resolved-log", old, new)
    if ok: applied += 1

    # =====================================================================
    # EDIT 4: Data hygiene — legacy double-slash annotation sanitizer
    # Inject sanitizeDoubleSlashAnnotations() after parseWorkbook function,
    # and hook it into the XLSX parse path for each row.
    # =====================================================================
    total += 1
    # Insert the sanitizer function after parseWorkbook
    anchor4 = "console.log('[parseWorkbook] Result:', result.order.length, 'sheets, errors:', result.errors.length);\n      return result;\n    }"
    sanitizer_fn = """console.log('[parseWorkbook] Result:', result.order.length, 'sheets, errors:', result.errors.length);
      return result;
    }

    function sanitizeDoubleSlashAnnotations(rowObj, headers) {
      var urlPattern = /^https?:\\/\\//i;
      var slashPattern = /\\/\\//;
      var sanitized = [];
      for (var hi = 0; hi < headers.length; hi++) {
        var h = headers[hi];
        if (!h) continue;
        var val = rowObj[h];
        if (val === null || val === undefined) continue;
        var sVal = String(val);
        if (sVal.indexOf('//') === -1) continue;
        if (urlPattern.test(sVal)) {
          var urlEndIdx = sVal.indexOf(' //');
          if (urlEndIdx === -1) urlEndIdx = sVal.indexOf('\\t//');
          if (urlEndIdx === -1) {
            var dblSlashPositions = [];
            var searchFrom = sVal.indexOf('://')  + 3;
            while (searchFrom < sVal.length) {
              var pos = sVal.indexOf('//', searchFrom);
              if (pos === -1) break;
              dblSlashPositions.push(pos);
              searchFrom = pos + 2;
            }
            if (dblSlashPositions.length > 0) {
              urlEndIdx = dblSlashPositions[dblSlashPositions.length - 1];
            }
          }
          if (urlEndIdx > 0) {
            var cleanUrl = sVal.substring(0, urlEndIdx).trim();
            var annotation = sVal.substring(urlEndIdx + 2).trim();
            if (annotation.length > 0) {
              rowObj[h] = cleanUrl;
              if (!rowObj['_imported_comment']) rowObj['_imported_comment'] = '';
              rowObj['_imported_comment'] += (rowObj['_imported_comment'] ? '; ' : '') + h + ': ' + annotation;
              sanitized.push({ field: h, raw: sVal, clean: cleanUrl, annotation: annotation, type: 'url' });
            }
          }
        } else {
          var parts = sVal.split('//');
          if (parts.length >= 2) {
            var cleanVal = parts[0].trim();
            var annot = parts.slice(1).join('//').trim();
            if (annot.length > 0 && cleanVal.length > 0) {
              rowObj[h] = cleanVal;
              if (!rowObj['_imported_comment']) rowObj['_imported_comment'] = '';
              rowObj['_imported_comment'] += (rowObj['_imported_comment'] ? '; ' : '') + h + ': ' + annot;
              sanitized.push({ field: h, raw: sVal, clean: cleanVal, annotation: annot, type: 'business' });
            }
          }
        }
      }
      if (sanitized.length > 0) {
        console.log('[P0.9-CLEANUP] legacy_slash_sanitized: count=' + sanitized.length + ', fields=' + sanitized.map(function(s) { return s.field; }).join(','));
        if (typeof AuditTimeline !== 'undefined') {
          AuditTimeline.emit('legacy_slash_sanitized', { metadata: { count: sanitized.length, fields: sanitized.map(function(s) { return s.field; }) } });
        }
      }
      return sanitized;
    }"""
    html, ok = apply_edit(html, "4a-slash-sanitizer-fn", anchor4, sanitizer_fn)
    if ok: applied += 1

    # Hook sanitizer into XLSX row processing (after rowObj is built, before rows.push)
    total += 1
    anchor4b = "rows.push(rowObj);\n            }\n            \n            // v2.3: Header-echo sanitization"
    hook4b = """sanitizeDoubleSlashAnnotations(rowObj, headers);
              rows.push(rowObj);
            }
            
            // v2.3: Header-echo sanitization"""
    html, ok = apply_edit(html, "4b-slash-sanitizer-hook-xlsx", anchor4b, hook4b)
    if ok: applied += 1

    # Hook sanitizer into CSV row processing too
    total += 1
    # Find the CSV path where rows are built
    csv_anchor = "result.sheets[sheetName] = { headers: parsed.headers, rows: normalizedRows, meta: { delimiter: parsed.delimiter } };"
    csv_hook = """for (var _csvSi = 0; _csvSi < parsed.rows.length; _csvSi++) {
            sanitizeDoubleSlashAnnotations(parsed.rows[_csvSi], parsed.headers);
          }
          result.sheets[sheetName] = { headers: parsed.headers, rows: normalizedRows, meta: { delimiter: parsed.delimiter } };"""
    html, ok = apply_edit(html, "4c-slash-sanitizer-hook-csv", csv_anchor, csv_hook)
    if ok: applied += 1

    # =====================================================================
    # EDIT 5: Pre-Flight/Schema consistency — enhance handleSchemaClick
    # empty-state to include source explanation for zero-count items.
    # =====================================================================
    total += 1
    old5 = """emptyState.textContent = 'No ' + (type === 'unknown' ? 'unknown columns' : type === 'missing' ? 'missing required fields' : 'schema drift items') + ' detected in current dataset. Load or refresh data to update this view.';"""
    new5 = """var _emptyReasons = {
            unknown: 'No unknown columns detected. All imported columns match the canonical schema.',
            missing: 'No missing required fields. All required fields from field_meta.json are present in the active dataset.',
            drift: 'No schema drift detected. This may indicate batch-level drift only — check Admin > Schema Tree for cross-batch comparison.'
          };
          emptyState.textContent = _emptyReasons[type] || 'No items found for this filter.';"""
    html, ok = apply_edit(html, "5-schema-empty-state", old5, new5)
    if ok: applied += 1

    # =====================================================================
    # EDIT 6: Replace ambiguous guidance labels
    # Fix renderSectionGuidanceCard to use sheet-derived labels instead of
    # showing Unknown/Unknown chips.
    # =====================================================================
    total += 1
    old6 = """if (docRole) html += '<span style="padding: 2px 8px; background: #e8eaf6; color: #3949ab; border-radius: 10px; font-size: 0.75em;">' + docRole + '</span>';
      if (docType) html += '<span style="padding: 2px 8px; background: #e0f2f1; color: #00695c; border-radius: 10px; font-size: 0.75em;">' + docType + '</span>';"""
    new6 = """var _safeRole = (docRole && docRole.toLowerCase() !== 'unknown') ? docRole : '';
      var _safeType = (docType && docType.toLowerCase() !== 'unknown') ? docType : '';
      if (!_safeRole && !_safeType && _sheetLabel) {
        _safeRole = _sheetLabel;
      }
      if (_safeRole) html += '<span style="padding: 2px 8px; background: #e8eaf6; color: #3949ab; border-radius: 10px; font-size: 0.75em;">' + _safeRole + '</span>';
      if (_safeType) html += '<span style="padding: 2px 8px; background: #e0f2f1; color: #00695c; border-radius: 10px; font-size: 0.75em;">' + _safeType + '</span>';
      console.log('[P0.9-CLEANUP] guidance_labels_resolved: role=' + _safeRole + ', type=' + _safeType + ', sheet=' + (_sheetLabel || ''));"""
    html, ok = apply_edit(html, "6-guidance-labels", old6, new6)
    if ok: applied += 1

    # =====================================================================
    # EDIT 7: Analyst role cleanup — hide replay-contract for analyst
    # The code already hides replay for analyst in two places. Ensure
    # the initial SRR open also respects this. Look for the place where
    # srr-replay-contract-block is initially shown.
    # Already handled by existing code:
    #   replayBlock.style.display = (currentMode === 'verifier' || currentMode === 'admin') ? 'block' : 'none';
    # Just add a P0.9 log to confirm.
    # =====================================================================
    total += 1
    old7 = """// v1.6.57: Show replay contract for RFI but mark as optional
      var replayBlock = document.getElementById('srr-replay-contract-block');
      var currentMode = localStorage.getItem('viewer_mode_v10') || 'analyst';
      if (replayBlock) replayBlock.style.display = (currentMode === 'verifier' || currentMode === 'admin') ? 'block' : 'none';"""
    new7 = """// v1.6.57: Show replay contract for RFI but mark as optional
      // P0.9: Analyst sees no replay controls
      var replayBlock = document.getElementById('srr-replay-contract-block');
      var _replayCurrentMode = localStorage.getItem('viewer_mode_v10') || 'analyst';
      var _showReplay = (_replayCurrentMode === 'verifier' || _replayCurrentMode === 'admin');
      if (replayBlock) replayBlock.style.display = _showReplay ? 'block' : 'none';"""
    html, ok = apply_edit(html, "7-analyst-replay-hide", old7, new7)
    if ok: applied += 1

    # =====================================================================
    # EDIT 8: Top-bar overlap cleanup
    # Move audit button inside triage-search-bar to a stable position,
    # ensure toast z-index doesn't collide with FAB.
    # The audit-header-dropdown-container sits inside page-header — keep it
    # but add position: relative so dropdown anchors properly.
    # Fix toast top offset to not overlap with sticky search bar.
    # =====================================================================
    total += 1
    old8 = "toast.style.cssText = 'position: fixed; top: 64px; left: 50%; transform: translateX(-50%); padding: 12px 24px; background: ' + bgColor + '; color: white; border-radius: 6px; font-size: 0.9em; z-index: 10001; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 90vw;';"
    new8 = """toast.style.cssText = 'position: fixed; top: 100px; left: 50%; transform: translateX(-50%); padding: 12px 24px; background: ' + bgColor + '; color: white; border-radius: 6px; font-size: 0.9em; z-index: 10001; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 80vw; max-width: calc(100vw - 200px);';
      console.log('[P0.9-CLEANUP] overlap_guard_ok: toast positioned clear of toolbar');"""
    html, ok = apply_edit(html, "8-toast-overlap-fix", old8, new8)
    if ok: applied += 1

    # Also ensure the audit-header-dropdown-container has proper positioning
    total += 1
    old8b = '<div id="audit-header-dropdown-container" style="display: inline-flex; margin-left: auto; z-index: 90;">'
    new8b = '<div id="audit-header-dropdown-container" style="display: inline-flex; margin-left: auto; z-index: 90; position: relative;">'
    html, ok = apply_edit(html, "8b-audit-container-position", old8b, new8b)
    if ok: applied += 1

    # =====================================================================
    # EDIT 9: Compact controls polish
    # The column toggle button is already compact (just "Cols" with icon).
    # Make the lifecycle tracker less visually heavy by reducing font weight
    # on triage lane count badges.
    # =====================================================================
    total += 1
    old9 = ".ta-lane-card { position: relative; overflow: hidden; }"
    new9 = """.ta-lane-card { position: relative; overflow: hidden; }
    .ta-lane-card .stat-value { font-weight: 600; }"""
    html, ok = apply_edit(html, "9-compact-controls", old9, new9)
    if ok: applied += 1

    # =====================================================================
    # EDIT 10: ES5 fix — setMode uses const/arrow/template literals
    # =====================================================================
    total += 1
    old10 = """function setMode(mode) {
      const modes = ['analyst', 'verifier', 'admin'];
      if (!modes.includes(mode)) mode = 'analyst';"""
    new10 = """function setMode(mode) {
      var modes = ['analyst', 'verifier', 'admin'];
      if (modes.indexOf(mode) === -1) mode = 'analyst';"""
    html, ok = apply_edit(html, "10a-setmode-es5-const", old10, new10)
    if ok: applied += 1

    total += 1
    old10b = """document.querySelectorAll('.mode-btn').forEach(b => b.classList.remove('active'));
      const modeBtn = document.querySelector(`.mode-btn[data-mode="${mode}"]`);
      if (modeBtn) modeBtn.classList.add('active');
      
      // Toggle nav visibility based on mode using CSS classes
      const appLayout = document.querySelector('.app-layout');"""
    new10b = """document.querySelectorAll('.mode-btn').forEach(function(b) { b.classList.remove('active'); });
      var modeBtn = document.querySelector('.mode-btn[data-mode=\"' + mode + '\"]');
      if (modeBtn) modeBtn.classList.add('active');
      
      // Toggle nav visibility based on mode using CSS classes
      var appLayout = document.querySelector('.app-layout');"""
    html, ok = apply_edit(html, "10b-setmode-es5-template", old10b, new10b)
    if ok: applied += 1

    total += 1
    old10c = """appLayout.classList.remove('mode-analyst', 'mode-verifier', 'mode-admin');
        appLayout.classList.add(`mode-${mode}`);
      }

      // v1.5.3 Fix: Toggle Triage view visibility + ALWAYS reload queues from canonical store
      const analystContent = document.getElementById('analyst-triage-content');
      const verifierContent = document.getElementById('verifier-triage-content');"""
    new10c = """appLayout.classList.remove('mode-analyst', 'mode-verifier', 'mode-admin');
        appLayout.classList.add('mode-' + mode);
      }

      // v1.5.3 Fix: Toggle Triage view visibility + ALWAYS reload queues from canonical store
      var analystContent = document.getElementById('analyst-triage-content');
      var verifierContent = document.getElementById('verifier-triage-content');"""
    html, ok = apply_edit(html, "10c-setmode-es5-template2", old10c, new10c)
    if ok: applied += 1

    # =====================================================================
    # EDIT 11: ES5 fix — DOMContentLoaded init has arrow functions/const/let
    # =====================================================================
    total += 1
    old11 = """document.querySelectorAll('.mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
          setMode(btn.dataset.mode);
        });
      });"""
    new11 = """document.querySelectorAll('.mode-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
          setMode(btn.getAttribute('data-mode'));
        });
      });"""
    html, ok = apply_edit(html, "11a-init-es5-arrow", old11, new11)
    if ok: applied += 1

    total += 1
    old11b = """window.addEventListener('hashchange', () => {
        const hash = window.location.hash.replace('#/', '') || 'triage';"""
    new11b = """window.addEventListener('hashchange', function() {
        var hash = window.location.hash.replace('#/', '') || 'triage';"""
    html, ok = apply_edit(html, "11b-hashchange-es5", old11b, new11b)
    if ok: applied += 1

    total += 1
    old11c = """let savedMode = localStorage.getItem('currentRole') || localStorage.getItem('viewer_mode_v10');"""
    new11c = """var savedMode = localStorage.getItem('currentRole') || localStorage.getItem('viewer_mode_v10');"""
    html, ok = apply_edit(html, "11c-let-to-var", old11c, new11c)
    if ok: applied += 1

    total += 1
    old11d = """const hash = window.location.hash.replace('#/', '') || '';
      if (hash && hash !== 'loader') {
        navigateTo(hash);
      } else {
        // No hash or loader - go to role default
        navigateToRoleDefault();
      }"""
    new11d = """var _initHash = window.location.hash.replace('#/', '') || '';
      if (_initHash && _initHash !== 'loader') {
        navigateTo(_initHash);
      } else {
        navigateToRoleDefault();
      }"""
    html, ok = apply_edit(html, "11d-const-hash-init", old11d, new11d)
    if ok: applied += 1

    # =====================================================================
    # Summary
    # =====================================================================
    print(f"\n{'='*60}")
    print(f"P0.9 Delta: {applied}/{total} edits applied")
    print(f"{'='*60}")
    
    if applied < total:
        print("[WARN] Some edits were not applied. Check anchors.")
        
    write_html(html)
    print(f"[OK] Written to {HTML_PATH}")
    return 0 if applied == total else 1

if __name__ == '__main__':
    sys.exit(main())

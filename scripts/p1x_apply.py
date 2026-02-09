#!/usr/bin/env python3
"""Apply P1X Canonical Contract Triage View changes to ui/viewer/index.html"""

import sys

FILE = 'ui/viewer/index.html'

def read_file():
    with open(FILE, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(content):
    with open(FILE, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_replace(content, label, old, new, replace_all=False):
    count = content.count(old)
    if count == 0:
        print(f'FAIL [{label}]: target string not found')
        return content, False
    if not replace_all and count > 1:
        print(f'WARN [{label}]: found {count} occurrences, replacing all')
    if replace_all:
        result = content.replace(old, new)
    else:
        result = content.replace(old, new, 1)
    print(f'SUCCESS [{label}]: replaced ({count} occurrence(s))')
    return result, True

def apply_insert_after(content, label, anchor, insertion):
    idx = content.find(anchor)
    if idx == -1:
        print(f'FAIL [{label}]: anchor string not found')
        return content, False
    pos = idx + len(anchor)
    result = content[:pos] + insertion + content[pos:]
    print(f'SUCCESS [{label}]: inserted after anchor')
    return result, True

def main():
    content = read_file()
    all_ok = True

    # 1. Add OPERATIONAL_SHEET_ALLOWLIST after REFERENCE_SHEET_PATTERNS
    anchor1 = "      'field_catalog', 'field catalog', 'reference', 'lookup'\n    ];\n"
    insert1 = """
    var OPERATIONAL_SHEET_ALLOWLIST = ['Accounts', 'Opportunities', 'Financials', 'Catalog', 'Schedule', 'Schedule Catalog', 'V2 Add Ons', 'Contacts'];

    function isOperationalSheet(sheetName) {
      if (!sheetName) return false;
      var lower = sheetName.toLowerCase().trim();
      return OPERATIONAL_SHEET_ALLOWLIST.some(function(op) { return lower === op.toLowerCase(); });
    }
"""
    content, ok = apply_insert_after(content, '1-OPERATIONAL_SHEET_ALLOWLIST', anchor1, insert1)
    all_ok = all_ok and ok

    # 2. Update batch_summary record counting
    old2 = "            if (sh && sh.rows && !(typeof isMetaSheet === 'function' && isMetaSheet(sn))) {"
    new2 = "            if (sh && sh.rows && (typeof isOperationalSheet === 'function' ? isOperationalSheet(sn) : !(typeof isMetaSheet === 'function' && isMetaSheet(sn)))) {"
    content, ok = apply_replace(content, '2-RECORD_COUNTING', old2, new2)
    all_ok = all_ok and ok

    # 3a. Add affected_contracts and records_impacted to batch_summary
    old3a = """        cache.batch_summary = {
          contracts_total: cache.total_contracts,
          records_total: totalRecords,
          completed: 0,
          needs_review: 0,
          pending: 0,
          unassigned_rows: cache._orphan_row_count || 0,
          updated_at: cache.refreshed_at
        };"""
    new3a = """        cache.batch_summary = {
          contracts_total: cache.total_contracts,
          records_total: totalRecords,
          completed: 0,
          needs_review: 0,
          pending: 0,
          affected_contracts: 0,
          records_impacted: 0,
          unassigned_rows: cache._orphan_row_count || 0,
          updated_at: cache.refreshed_at
        };"""
    content, ok = apply_replace(content, '3a-BATCH_SUMMARY_FIELDS', old3a, new3a)
    all_ok = all_ok and ok

    # 3b. Add affected_contracts computation before batch_summary_recomputed log
    anchor3b = "        console.log('[TRIAGE-ANALYTICS][P0.2] batch_summary_recomputed: contracts='"
    insert3b = """        var _affectedCk = {};
        var _impactedRecords = 0;
        (analystTriageState.manualItems || []).forEach(function(item) {
          if (item.contract_key || item.contract_id) _affectedCk[item.contract_key || item.contract_id] = true;
          if (item.record_id) _impactedRecords++;
        });
        (typeof _p1fBatchScanItems !== 'undefined' ? _p1fBatchScanItems : []).forEach(function(item) {
          if (item.contract_key || item.contract_id) _affectedCk[item.contract_key || item.contract_id] = true;
        });
        cache.batch_summary.affected_contracts = Object.keys(_affectedCk).length;
        cache.batch_summary.records_impacted = _impactedRecords;
        console.log('[TRIAGE-CANONICAL][P1X] counts_computed: contracts=' + cache.batch_summary.contracts_total + ', records=' + cache.batch_summary.records_total + ', affected=' + cache.batch_summary.affected_contracts + ', impacted=' + cache.batch_summary.records_impacted);
"""
    idx = content.find(anchor3b)
    if idx == -1:
        print('FAIL [3b-AFFECTED_CONTRACTS]: anchor not found')
        all_ok = False
    else:
        content = content[:idx] + insert3b + content[idx:]
        print('SUCCESS [3b-AFFECTED_CONTRACTS]: inserted before log line')

    # 4. Add Pre-Flight metrics to header HTML
    anchor4 = '                  <span id="ta-preflight-total" style="background: #ffebee; color: #c62828; padding: 2px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600;">0</span>'
    insert4 = """
                  <div style="display: flex; justify-content: space-between; margin-top: 4px;"><span style="color: #666;">Affected Contracts</span><span id="ta-pf-affected" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Records Impacted</span><span id="ta-pf-impacted" style="font-weight: 600;">0</span></div>"""
    content, ok = apply_insert_after(content, '4-PREFLIGHT_METRICS_HTML', anchor4, insert4)
    all_ok = all_ok and ok

    # 5. Wire up new metrics in renderHeader
    anchor5 = "        if (el('ta-pf-doctype')) el('ta-pf-doctype').textContent = cache.lanes.preflight.document_type || 0;"
    insert5 = """
        if (el('ta-pf-affected')) el('ta-pf-affected').textContent = cache.batch_summary ? cache.batch_summary.affected_contracts : 0;
        if (el('ta-pf-impacted')) el('ta-pf-impacted').textContent = cache.batch_summary ? cache.batch_summary.records_impacted : 0;"""
    content, ok = apply_insert_after(content, '5-WIRE_METRICS', anchor5, insert5)
    all_ok = all_ok and ok

    # 6. Replace "Sheet" with "Contract Section" in P1D pre-flight table header
    old6 = "html += '<th>Sheet</th><th>Field</th><th>Reason</th><th>Severity</th><th>Status</th><th>Actions</th>';"
    new6 = "html += '<th>Contract Section</th><th>Field</th><th>Reason</th><th>Severity</th><th>Status</th><th>Actions</th>';"
    content, ok = apply_replace(content, '6-P1D_TABLE_HEADER', old6, new6)
    all_ok = all_ok and ok

    # 7. Add P1X log after P1D-PREFLIGHT total_groups log
    anchor7 = "      console.log('[P1D-PREFLIGHT] total_groups=' + groupOrder.length + ' total_items=' + items.length);"
    insert7 = "\n      console.log('[TRIAGE-CANONICAL][P1X] grouping_rendered: groups=' + groupOrder.length + ', items=' + items.length);"
    content, ok = apply_insert_after(content, '7-P1D_GROUPING_LOG', anchor7, insert7)
    all_ok = all_ok and ok

    # 8a. Replace { key: 'sheet', label: 'Sheet' } with Contract Section (all occurrences)
    old8a = "{ key: 'sheet', label: 'Sheet' }"
    new8a = "{ key: 'sheet', label: 'Contract Section' }"
    content, ok = apply_replace(content, '8a-SHEET_COLUMN_LABELS', old8a, new8a, replace_all=True)
    all_ok = all_ok and ok

    # 8b. Replace Sheet th in admin table
    old8b = '<th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Sheet</th>'
    new8b = '<th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Contract Section</th>'
    content, ok = apply_replace(content, '8b-ADMIN_TABLE_TH', old8b, new8b)
    all_ok = all_ok and ok

    # 9. Replace "Sheet:" label in grid area
    old9 = '<label style="font-size: 0.85em; color: #666;">Sheet:</label>'
    new9 = '<label style="font-size: 0.85em; color: #666;">Contract Section:</label>'
    content, ok = apply_replace(content, '9-GRID_LABEL', old9, new9)
    all_ok = all_ok and ok

    # 10. Add OCR parent bucket rollup log after preflight total line
    anchor10 = "        cache.lanes.preflight.total = cache.lanes.preflight.unknown_columns + cache.lanes.preflight.ocr_unreadable + cache.lanes.preflight.low_confidence + (cache.lanes.preflight.document_type || 0);"
    insert10 = "\n        console.log('[TRIAGE-CANONICAL][P1X] ocr_parent_rollup: total=' + cache.lanes.preflight.ocr_unreadable);"
    content, ok = apply_insert_after(content, '10-OCR_ROLLUP_LOG', anchor10, insert10)
    all_ok = all_ok and ok

    # 11. Add batch-level explainer log
    anchor11 = "            emptyState.textContent = count + ' ' + type + ' item(s) found. This is batch-level drift; no individual record row available. Items are listed in the Pre-Flight queue below.';"
    insert11 = "\n            console.log('[TRIAGE-CANONICAL][P1X] batch_level_explainer_shown: type=' + type + ', count=' + count);"
    content, ok = apply_insert_after(content, '11-BATCH_EXPLAINER_LOG', anchor11, insert11)
    all_ok = all_ok and ok

    # 12. Add route_decision log to openPreflightItem
    anchor12 = "    function openPreflightItem(requestId, recordId, contractId, fieldName) {"
    insert12 = "\n      console.log('[TRIAGE-CANONICAL][P1X] route_decision: request_id=' + requestId + ', contract=' + (contractId || 'none'));"
    content, ok = apply_insert_after(content, '12-ROUTE_DECISION_LOG', anchor12, insert12)
    all_ok = all_ok and ok

    write_file(content)

    if all_ok:
        print('\n=== ALL 12 CHANGES APPLIED SUCCESSFULLY ===')
    else:
        print('\n=== SOME CHANGES FAILED - SEE ABOVE ===')
        sys.exit(1)

if __name__ == '__main__':
    main()

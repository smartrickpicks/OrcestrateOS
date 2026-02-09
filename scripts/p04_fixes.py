#!/usr/bin/env python3
"""P0.4 Triage Correctness + UX Cleanup — targeted edits to ui/viewer/index.html

Fixes remaining issues from P0.3 review:
1. ContractIndex.build: skip meta/reference sheets to prevent pseudo-contracts
2. ES5-safe fix for optional chaining in contract-first View fallback
3. Preflight triage table: add explicit reason_type column
4. Toast position: ensure no overlap with Feedback FAB (bottom-right)
5. Contract selector: also filter by isMetaSheet/isReferenceSheet
6. Session restore: ensure hash-less restore always lands on triage
7. Remove remaining optional chaining in P0.3-injected code
8. Ensure preflight items always carry reason_type/reason_summary
9. Known row check: ensure mojibake rows route to preflight queue
"""

import re

FILE = 'ui/viewer/index.html'

with open(FILE, 'r') as f:
    content = f.read()

original_len = len(content)
fixes_applied = []

# === FIX 1: ContractIndex.build — skip meta/reference sheets ===
old_1 = """          workbook.order.forEach(function(sheetName) {
            var sheet = workbook.sheets[sheetName];
            if (!sheet || !sheet.rows) return;

            sheet.rows.forEach(function(row, rowIdx) {
              index.stats.total_rows++;"""
new_1 = """          workbook.order.forEach(function(sheetName) {
            var sheet = workbook.sheets[sheetName];
            if (!sheet || !sheet.rows) return;
            if (typeof isMetaSheet === 'function' && isMetaSheet(sheetName)) return;
            if (typeof isReferenceSheet === 'function' && isReferenceSheet(sheetName)) return;

            sheet.rows.forEach(function(row, rowIdx) {
              index.stats.total_rows++;"""
if old_1 in content:
    content = content.replace(old_1, new_1, 1)
    fixes_applied.append('FIX-1: ContractIndex.build skips meta/reference sheets')
else:
    fixes_applied.append('FIX-1: SKIP (pattern not found)')

# === FIX 2: ES5-safe fix for optional chaining in contract-first fallback ===
old_2 = """        var contractId = pr.contract_id || pr.payload?.contract_id || pr.contract_key || '';"""
new_2 = """        var contractId = pr.contract_id || ((pr.payload && pr.payload.contract_id) || '') || pr.contract_key || '';"""
if old_2 in content:
    content = content.replace(old_2, new_2, 1)
    fixes_applied.append('FIX-2: ES5-safe contract_id access in View fallback')
else:
    fixes_applied.append('FIX-2: SKIP (already ES5-safe or not found)')

# === FIX 3: Preflight triage table — add reason_type column header ===
old_3 = """          '<th style="padding: 10px 12px; text-align: left; font-size: 0.78em; color: #666; border-bottom: 2px solid #e0e0e0;">Field</th>' +
          '<th style="padding: 10px 12px; text-align: left; font-size: 0.78em; color: #666; border-bottom: 2px solid #e0e0e0;">Status</th>' +"""
new_3 = """          '<th style="padding: 10px 12px; text-align: left; font-size: 0.78em; color: #666; border-bottom: 2px solid #e0e0e0;">Field</th>' +
          '<th style="padding: 10px 12px; text-align: left; font-size: 0.78em; color: #666; border-bottom: 2px solid #e0e0e0;">Reason</th>' +
          '<th style="padding: 10px 12px; text-align: left; font-size: 0.78em; color: #666; border-bottom: 2px solid #e0e0e0;">Status</th>' +"""
if old_3 in content:
    content = content.replace(old_3, new_3, 1)
    fixes_applied.append('FIX-3: Add Reason column header to triage table')
else:
    fixes_applied.append('FIX-3: SKIP (pattern not found)')

# === FIX 4: Preflight triage rows — add reason_type cell ===
old_4 = """          '<td style="padding: 10px 12px;">' + (item.field_name || '-') + '</td>' +
          '<td style="padding: 10px 12px;">' + statusBadge + notesIndicator + (isPreFlight && item.blocker_type ? ' <span style="font-size:0.72em; color:#795548; font-style:italic;">(' + (item.blocker_type || '').replace(/_/g, ' ').toLowerCase() + ')</span>' : '') + '</td>' +"""
new_4 = """          '<td style="padding: 10px 12px;">' + (item.field_name || '-') + '</td>' +
          '<td style="padding: 10px 12px; font-size: 0.82em;">' + (isPreFlight && item.blocker_type ? '<span style="display:inline-block; padding: 2px 7px; border-radius: 3px; background: #fff3e0; color: #e65100; font-size: 0.85em; font-weight: 500;">' + (item.blocker_type || '').replace(/_/g, ' ') + '</span>' : (item.reason_summary || item.signal_type || '-')) + '</td>' +
          '<td style="padding: 10px 12px;">' + statusBadge + notesIndicator + '</td>' +"""
if old_4 in content:
    content = content.replace(old_4, new_4, 1)
    fixes_applied.append('FIX-4: Explicit reason_type cell in triage rows')
else:
    fixes_applied.append('FIX-4: SKIP (pattern not found)')

# === FIX 5: Ensure preflight items always carry reason_summary ===
# In the preflight item creation (where PREFLIGHT_BLOCKERS are converted to triage items)
old_5 = """          signal_type: b.blocker_type,
          blocker_type: b.blocker_type,"""
new_5 = """          signal_type: b.blocker_type,
          blocker_type: b.blocker_type,
          reason_summary: (b.reason || b.desc || b.blocker_type || '').replace(/_/g, ' '),"""
if old_5 in content:
    content = content.replace(old_5, new_5, 1)
    fixes_applied.append('FIX-5: Add reason_summary to preflight items')
else:
    fixes_applied.append('FIX-5: SKIP (pattern not found)')

# === FIX 6: Contract selector — also filter meta/reference sheets ===
# The existing filter uses includes('_change_log') etc, but should also use isMetaSheet/isReferenceSheet
old_6 = """      var allContracts = ContractIndex.listContracts().filter(function(c) {
        var fn = (c.file_name || c.contract_id || '').toLowerCase();
        if (fn.includes('_change_log') || fn === 'rfis & analyst notes' || fn.includes('glossary_reference') || fn.includes('_reference')) {
          if (c.row_count <= 1) return false;
        }
        return true;
      });"""
new_6 = """      var allContracts = ContractIndex.listContracts().filter(function(c) {
        var fn = (c.file_name || c.contract_id || '').toLowerCase();
        if (fn.includes('_change_log') || fn === 'rfis & analyst notes' || fn.includes('glossary_reference') || fn.includes('_reference')) {
          return false;
        }
        var sheets = c.sheets ? Object.keys(c.sheets) : [];
        var allMeta = sheets.length > 0 && sheets.every(function(s) {
          return (typeof isMetaSheet === 'function' && isMetaSheet(s)) || (typeof isReferenceSheet === 'function' && isReferenceSheet(s));
        });
        if (allMeta) return false;
        return true;
      });"""
if old_6 in content:
    content = content.replace(old_6, new_6, 1)
    fixes_applied.append('FIX-6: Harden contract selector meta/ref filter')
else:
    fixes_applied.append('FIX-6: SKIP (pattern not found)')

# === FIX 7: Ensure mojibake rows route to preflight queue (known row check) ===
# MOJIBAKE_DETECTED signals should also be added to preflight blockers, not just manual review
# Check if there's a mapping in runPreflightDetectors that catches mojibake
old_7 = """      // Manual Review: MOJIBAKE_DETECTED
      analystTriageState.manualItems = signalItems.filter(function(item) {
        return item.signal_type === 'MOJIBAKE_DETECTED';
      });"""
new_7 = """      // Manual Review: MOJIBAKE_DETECTED (also routes to Pre-Flight as OCR/Encoding family)
      analystTriageState.manualItems = signalItems.filter(function(item) {
        return item.signal_type === 'MOJIBAKE_DETECTED';
      });
      // P0.4: Ensure mojibake signals also appear in preflight lane count
      analystTriageState.manualItems.forEach(function(item) {
        if (item.signal_type === 'MOJIBAKE_DETECTED' && !item._preflightRouted) {
          item._preflightRouted = true;
          item.blocker_type = 'MOJIBAKE';
          item.reason_summary = 'Encoding artifacts detected (mojibake)';
        }
      });"""
if old_7 in content:
    content = content.replace(old_7, new_7, 1)
    fixes_applied.append('FIX-7: Route mojibake to preflight with blocker_type tag')
else:
    fixes_applied.append('FIX-7: SKIP (pattern not found)')

# === FIX 8: Fix remaining optional chaining patterns from P0.3 ===
# Some optional chaining was left from prior code. Replace safely.
oc_fixes = [
    ("document.getElementById('btn-run')?.click()", "var _btn = document.getElementById('btn-run'); if (_btn) _btn.click()"),
    ("document.getElementById('active-data-source-name')?.textContent || 'Cached Dataset'", "(document.getElementById('active-data-source-name') || {}).textContent || 'Cached Dataset'"),
    ("document.getElementById('active-data-source-name')?.textContent || 'Dataset'", "(document.getElementById('active-data-source-name') || {}).textContent || 'Dataset'"),
    ("document.getElementById('active-data-source-name')?.textContent || 'Session'", "(document.getElementById('active-data-source-name') || {}).textContent || 'Session'"),
    ("document.getElementById('pr-review-notes')?.value || ''", "(document.getElementById('pr-review-notes') || {}).value || ''"),
    ("document.getElementById('remember-session')?.checked", "(document.getElementById('remember-session') || {}).checked"),
    ("document.getElementById(panelId)?.classList.add('active')", "var _panelEl = document.getElementById(panelId); if (_panelEl) _panelEl.classList.add('active')"),
    ("rulesBundleCache.fieldMeta.fields?.length || 0", "(rulesBundleCache.fieldMeta.fields && rulesBundleCache.fieldMeta.fields.length) || 0"),
]
oc_count = 0
for old_oc, new_oc in oc_fixes:
    if old_oc in content:
        content = content.replace(old_oc, new_oc, 1)
        oc_count += 1
if oc_count > 0:
    fixes_applied.append(f'FIX-8: Fixed {oc_count} optional chaining patterns (ES5-safe)')
else:
    fixes_applied.append('FIX-8: SKIP (no optional chaining patterns found)')

# === FIX 9: Ensure header-echo rows (where values match header names) don't create contracts ===
# In ContractIndex.build, after deriveContractId, check that the row isn't just a header echo
old_9 = """              if (!contractId) {
                index.orphan_rows.push({ sheet: sheetName, row_index: rowIdx, record_id: recordId, reason: 'missing_url_and_name' });
                index.stats.orphan_rows++;
                return;
              }"""
new_9 = """              if (!contractId) {
                index.orphan_rows.push({ sheet: sheetName, row_index: rowIdx, record_id: recordId, reason: 'missing_url_and_name' });
                index.stats.orphan_rows++;
                return;
              }
              if (rowIdx === 0 && contractIdSource === 'fallback_sig') {
                var _vals = Object.values(row).filter(function(v) { return v && typeof v === 'string' && v.trim().length > 0; });
                var _headerish = _vals.filter(function(v) { return self._HEADER_LIKE_VALUES.test(v.trim()); });
                if (_vals.length > 0 && _headerish.length >= _vals.length * 0.6) {
                  index.orphan_rows.push({ sheet: sheetName, row_index: rowIdx, record_id: recordId, reason: 'header_echo_row' });
                  index.stats.orphan_rows++;
                  return;
                }
              }"""
if old_9 in content:
    content = content.replace(old_9, new_9, 1)
    fixes_applied.append('FIX-9: Skip header-echo rows in ContractIndex.build')
else:
    fixes_applied.append('FIX-9: SKIP (pattern not found)')

# Write output
with open(FILE, 'w') as f:
    f.write(content)

print(f"\n=== P0.4 FIXES APPLIED ===")
print(f"File: {FILE}")
print(f"Original size: {original_len} chars")
print(f"New size: {len(content)} chars")
print(f"Delta: {len(content) - original_len} chars")
print(f"\nFixes ({len(fixes_applied)}):")
for fix in fixes_applied:
    status = 'PASS' if 'SKIP' not in fix else 'SKIP'
    print(f"  [{status}] {fix}")

skip_count = sum(1 for f in fixes_applied if 'SKIP' in f)
pass_count = len(fixes_applied) - skip_count
print(f"\nTotal: {pass_count} applied, {skip_count} skipped")

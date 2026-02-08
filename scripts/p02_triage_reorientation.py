#!/usr/bin/env python3
"""P0.2 Triage Reorientation Patch Script.

Applies all P0.2 changes to ui/viewer/index.html:
1. Header IA reorder (Batch Summary -> Contract Summary -> Lane Cards -> Lifecycle -> Schema)
2. Batch Summary compact strip (new)
3. Contract count reconciliation check
4. Route hardening (warning toast on final fallback)
5. Metadata leak guard hardening (per-refresh exclusion counters)
6. Schema snapshot empty-state helper
7. Layout polish stability
8. [TRIAGE-ANALYTICS][P0.2] logging
"""

import re
import sys

FILE = 'ui/viewer/index.html'

with open(FILE, 'r') as f:
    content = f.read()

lines = content.split('\n')
original_count = len(lines)

def find_line(pattern, start=0):
    for i in range(start, len(lines)):
        if pattern in lines[i]:
            return i
    return -1

def find_line_regex(pattern, start=0):
    rx = re.compile(pattern)
    for i in range(start, len(lines)):
        if rx.search(lines[i]):
            return i
    return -1

changes = []

# ============================================================
# FIX 1: Header IA reorder
# Current order: Lane Cards (A) -> Lifecycle (B) -> Contract Summary (C) -> Schema (D)
# Target order:  Batch Summary (NEW) -> Contract Summary (C) -> Lane Cards (A) -> Lifecycle (B) -> Schema (D)
# ============================================================

# Find the triage-analytics-header div
header_start = find_line('id="triage-analytics-header"')
assert header_start >= 0, "Cannot find triage-analytics-header"

# Find sections by their comments/markers
lane_cards_comment = find_line('<!-- A) 3 Lanes -->', header_start)
assert lane_cards_comment >= 0, "Cannot find Lane Cards comment"

# Find the lane cards section end - it's the grid div that contains all 3 cards
# The lane cards are in a grid div right after the comment
lane_cards_grid_start = lane_cards_comment + 1

# Find lifecycle section - look for the lifecycle heading
lifecycle_heading = find_line('Lifecycle Progression', header_start)
assert lifecycle_heading >= 0, "Cannot find Lifecycle heading"

# The lifecycle section starts a few lines before the heading (the wrapping div)
# Let's find the div that wraps lifecycle
lifecycle_wrap_start = find_line_regex(r'<!-- B\) Lifecycle|Lifecycle Progression', header_start)

# Find contract summary section
contract_summary_start = find_line('ta-contract-toggle', header_start)
assert contract_summary_start >= 0, "Cannot find contract summary toggle"

# Find schema snapshot
schema_snapshot_comment = find_line('<!-- D) Schema Snapshot -->', header_start)
assert schema_snapshot_comment >= 0, "Cannot find Schema Snapshot comment"

# Find the end of the header div (before queue sections)
queue_start = find_line('<!-- QUEUE 1: Pre-Flight -->', header_start)
assert queue_start >= 0, "Cannot find queue start"

# Strategy: Extract the full header content between header_start+1 and the line before queue_start
# that has </div> closing the triage-analytics-header
# Then rebuild it in the new order

# Let me identify exact line ranges for each section
# First, find boundaries more precisely

print(f"header_start={header_start}")
print(f"lane_cards_comment={lane_cards_comment}")
print(f"lifecycle_heading={lifecycle_heading}")
print(f"contract_summary_start={contract_summary_start}")
print(f"schema_snapshot_comment={schema_snapshot_comment}")
print(f"queue_start={queue_start}")

# Find the end of lane cards section (the closing </div> of the grid)
# Lane cards is: comment line, then <div style="display: grid; grid-template-columns: repeat(3, 1fr)...">
# followed by 3 card divs, then closing </div>
# We need to find where the lane cards grid ends and lifecycle begins

# Find "<!-- B)" comment or the lifecycle wrapper div
lifecycle_comment = find_line_regex(r'<!--.*Lifecycle', header_start)
if lifecycle_comment < 0:
    # No comment, find the div with margin-bottom that has "Lifecycle Progression" heading nearby
    # Look for the div wrapping lifecycle
    pass

# Actually let's do this differently - extract the raw sections by looking at the structure
# The header has child divs at the same nesting level

# Let me find the exact content between header open tag and close tag
# Parse the header content as sections

# Inside triage-analytics-header, the sections are:
# 1. Lane Cards grid (comment "A) 3 Lanes" + grid div)  
# 2. Lifecycle div (with heading "Lifecycle Progression")
# 3. Contract Summary div (with ta-contract-toggle)
# 4. Schema Snapshot div (comment "D) Schema Snapshot")

# Strategy: Rather than reordering DOM sections (error-prone with line manipulation),
# I'll replace the entire header inner content with the new structure

# Extract each section's content by finding the boundaries

# Section A: Lane Cards - from comment to just before lifecycle
# Need to find where lane cards end
# Lane cards comment is followed by a grid div

# Let me find the div boundaries more carefully by looking at indent levels

# Find the closing </div> of the header
header_end = None
for i in range(queue_start - 1, header_start, -1):
    stripped = lines[i].strip()
    if stripped == '</div>':
        header_end = i
        break
assert header_end is not None, "Cannot find header end"

print(f"header_end={header_end}")

# Now extract content between header_start+1 and header_end (exclusive)
header_inner = lines[header_start + 1:header_end]

# Join into single string for easier section extraction
header_text = '\n'.join(header_inner)

# Split into sections using comment markers and known patterns
# Section A: from <!-- A) 3 Lanes --> to just before the lifecycle wrapper
# Section B+C: lifecycle div then contract summary div
# Section D: schema snapshot

# Let me use regex to find section boundaries in the header_text

# Find section A (Lane Cards)
a_match = re.search(r'(            <!-- A\) 3 Lanes -->.*?)(?=            <!--|\s*<div[^>]*margin-bottom[^>]*>\s*\n\s*<div[^>]*display:\s*flex[^>]*justify-content:\s*space-between)', header_text, re.DOTALL)

# This is getting complex. Let me use a simpler approach: 
# Just rebuild the entire header from the existing pieces

# I know the exact structure. Let me extract using line numbers relative to header_start

# Content between header_start+1 and header_end-1
# 
# Let me identify each top-level child div of the header

depth = 0
sections = []
current_section_start = None

for i in range(header_start + 1, header_end):
    stripped = lines[i].strip()
    
    # Track opening/closing div tags
    opens = len(re.findall(r'<div[ >]', lines[i]))
    closes = len(re.findall(r'</div>', lines[i]))
    
    if depth == 0 and (stripped.startswith('<div') or stripped.startswith('<!--')):
        if stripped.startswith('<!--') and not stripped.startswith('<div'):
            # Comment line - part of next section
            current_section_start = i
            continue
        current_section_start = current_section_start if current_section_start else i
    
    depth += opens
    depth -= closes
    
    if depth == 0 and current_section_start is not None and opens + closes > 0:
        sections.append((current_section_start, i))
        current_section_start = None

print(f"Found {len(sections)} sections in header:")
for idx, (s, e) in enumerate(sections):
    preview = lines[s].strip()[:80]
    print(f"  Section {idx}: lines {s}-{e}: {preview}")

assert len(sections) >= 4, f"Expected at least 4 sections, found {len(sections)}"

# Identify which section is which
section_map = {}
for idx, (s, e) in enumerate(sections):
    section_text = '\n'.join(lines[s:e+1])
    if '3 Lanes' in section_text or 'ta-lane-card' in section_text:
        section_map['lanes'] = idx
    elif 'Lifecycle Progression' in section_text or 'ta-lifecycle' in section_text:
        section_map['lifecycle'] = idx
    elif 'ta-contract-toggle' in section_text or 'Contract Summary' in section_text or 'ta-contract-count' in section_text:
        section_map['contract'] = idx
    elif 'Schema Snapshot' in section_text or 'ta-schema' in section_text:
        section_map['schema'] = idx

print(f"Section map: {section_map}")
assert 'lanes' in section_map, "Cannot identify lanes section"
assert 'lifecycle' in section_map, "Cannot identify lifecycle section"
assert 'contract' in section_map, "Cannot identify contract section"
assert 'schema' in section_map, "Cannot identify schema section"

# Extract each section's lines
def get_section_lines(name):
    idx = section_map[name]
    s, e = sections[idx]
    return lines[s:e+1]

lanes_lines = get_section_lines('lanes')
lifecycle_lines = get_section_lines('lifecycle')
contract_lines = get_section_lines('contract')
schema_lines = get_section_lines('schema')

# ============================================================
# BUILD NEW HEADER CONTENT
# Order: Batch Summary -> Contract Summary -> Lane Cards -> Lifecycle -> Schema
# ============================================================

batch_summary_html = """            <!-- 1) Batch Summary -->
            <div id="ta-batch-summary" style="display: flex; gap: 20px; align-items: center; padding: 12px 16px; background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 10px; margin-bottom: 16px; flex-wrap: wrap;">
              <div style="text-align: center; min-width: 60px;">
                <div style="font-size: 0.7em; color: #666; text-transform: uppercase; font-weight: 600;">Contracts</div>
                <div id="ta-bs-contracts" style="font-size: 1.3em; font-weight: 700; color: #1565c0;">0</div>
              </div>
              <div style="width: 1px; height: 28px; background: #ddd;"></div>
              <div style="text-align: center; min-width: 60px;">
                <div style="font-size: 0.7em; color: #666; text-transform: uppercase; font-weight: 600;">Records</div>
                <div id="ta-bs-records" style="font-size: 1.3em; font-weight: 700; color: #333;">0</div>
              </div>
              <div style="width: 1px; height: 28px; background: #ddd;"></div>
              <div style="text-align: center; min-width: 60px;">
                <div style="font-size: 0.7em; color: #666; text-transform: uppercase; font-weight: 600;">Completed</div>
                <div id="ta-bs-completed" style="font-size: 1.3em; font-weight: 700; color: #2e7d32;">0</div>
              </div>
              <div style="text-align: center; min-width: 60px;">
                <div style="font-size: 0.7em; color: #666; text-transform: uppercase; font-weight: 600;">Needs Review</div>
                <div id="ta-bs-review" style="font-size: 1.3em; font-weight: 700; color: #e65100;">0</div>
              </div>
              <div style="text-align: center; min-width: 60px;">
                <div style="font-size: 0.7em; color: #666; text-transform: uppercase; font-weight: 600;">Pending</div>
                <div id="ta-bs-pending" style="font-size: 1.3em; font-weight: 700; color: #555;">0</div>
              </div>
              <div style="width: 1px; height: 28px; background: #ddd;"></div>
              <div style="text-align: center; min-width: 80px;">
                <div style="font-size: 0.7em; color: #666; text-transform: uppercase; font-weight: 600;">Updated</div>
                <div id="ta-bs-updated" style="font-size: 0.8em; color: #999;">--</div>
              </div>
              <div id="ta-bs-unassigned" style="display: none;">
                <span style="padding: 2px 10px; border-radius: 8px; background: #fff3e0; color: #e65100; font-size: 0.75em; cursor: help;" title="Rows without a contract assignment. Excluded from lifecycle tracking by policy.">&#9888; <span id="ta-bs-unassigned-count">0</span> Unassigned rows</span>
              </div>
              <div id="ta-reconcile-warn" style="display: none;">
                <span style="padding: 2px 10px; border-radius: 8px; background: #ffebee; color: #c62828; font-size: 0.75em; cursor: help;" title="Contract count mismatch detected. See console for details.">&#9888; Count mismatch</span>
              </div>
            </div>"""

# Add comment labels to reordered sections
contract_section_text = '\n'.join(contract_lines)
# Replace any old comment with new section number
contract_section_text = contract_section_text.replace('<!-- C) Contract Summary -->', '<!-- 2) Contract Summary -->')
if '<!-- 2) Contract Summary -->' not in contract_section_text:
    # Prepend comment
    contract_section_text = '            <!-- 2) Contract Summary -->\n' + contract_section_text

lanes_section_text = '\n'.join(lanes_lines)
lanes_section_text = lanes_section_text.replace('<!-- A) 3 Lanes -->', '<!-- 3) Lane Health -->')

lifecycle_section_text = '\n'.join(lifecycle_lines)
lifecycle_section_text = lifecycle_section_text.replace('<!-- B) Lifecycle Progression -->', '<!-- 4) Lifecycle Progression -->')
if '<!-- 4) Lifecycle Progression -->' not in lifecycle_section_text:
    # Check for other comment variants
    if '<!--' not in lifecycle_section_text.split('\n')[0]:
        lifecycle_section_text = '            <!-- 4) Lifecycle Progression -->\n' + lifecycle_section_text

schema_section_text = '\n'.join(schema_lines)
schema_section_text = schema_section_text.replace('<!-- D) Schema Snapshot -->', '<!-- 5) Schema Snapshot -->')

# Add schema empty-state helper div at end of schema section (before closing </div>)
# Find last </div> in schema section and insert before it
schema_section_lines = schema_section_text.split('\n')
# Find the last closing div line
last_close_idx = None
for i in range(len(schema_section_lines) - 1, -1, -1):
    if '</div>' in schema_section_lines[i]:
        last_close_idx = i
        break

empty_state_html = '              <div id="ta-schema-empty-state" style="display: none; padding: 12px; text-align: center; color: #999; font-size: 0.8em; border-top: 1px solid #eee; margin-top: 12px;">No matching items found for this filter. Try loading a dataset with more columns.</div>'

if last_close_idx is not None:
    schema_section_lines.insert(last_close_idx, empty_state_html)
    schema_section_text = '\n'.join(schema_section_lines)

# Build new header inner content
new_header_inner = '\n'.join([
    batch_summary_html,
    contract_section_text,
    lanes_section_text,
    lifecycle_section_text,
    schema_section_text
])

# Replace old header inner content
old_header_start_line = header_start + 1
old_header_end_line = header_end  # exclusive

new_lines = lines[:old_header_start_line] + new_header_inner.split('\n') + lines[old_header_end_line:]
lines = new_lines

print(f"FIX 1: Header reordered. Old lines {old_header_start_line}-{old_header_end_line}, new content inserted.")

# ============================================================
# FIX 2: Add renderBatchSummary to TriageAnalytics JS
# ============================================================

# Find TriageAnalytics object
ta_start = find_line('var TriageAnalytics = {')
assert ta_start >= 0, "Cannot find TriageAnalytics"

# Find the end of the refresh() method (where it returns cache)
refresh_return = find_line("return cache;", ta_start)
assert refresh_return >= 0, "Cannot find refresh return"

# Add batch summary computation + reconciliation before return
batch_compute_js = """
        // P0.2: Compute batch summary
        var totalRecords = 0;
        if (typeof workbook !== 'undefined' && workbook.order) {
          workbook.order.forEach(function(sn) {
            var sh = workbook.sheets[sn];
            if (sh && sh.rows && !(typeof isMetaSheet === 'function' && isMetaSheet(sn))) {
              totalRecords += sh.rows.length;
            }
          });
        }
        cache.batch_summary = {
          contracts_total: cache.total_contracts,
          records_total: totalRecords,
          completed: 0,
          needs_review: 0,
          pending: 0,
          unassigned_rows: cache._orphan_row_count || 0,
          updated_at: cache.refreshed_at
        };
        cache.contracts.forEach(function(c) {
          if (c.current_stage === 'applied') cache.batch_summary.completed++;
          else if (c.preflight_alerts > 0 || c.semantic_alerts > 0 || c.patch_alerts > 0) cache.batch_summary.needs_review++;
          else cache.batch_summary.pending++;
        });
        console.log('[TRIAGE-ANALYTICS][P0.2] batch_summary_recomputed: contracts=' + cache.batch_summary.contracts_total + ', records=' + cache.batch_summary.records_total + ', completed=' + cache.batch_summary.completed + ', review=' + cache.batch_summary.needs_review + ', pending=' + cache.batch_summary.pending + ', unassigned=' + cache.batch_summary.unassigned_rows);

        // P0.2: Reconciliation check
        var lifecycleTotal = 0;
        Object.keys(cache.lifecycle).forEach(function(k) { lifecycleTotal += cache.lifecycle[k].count; });
        var contractSummaryTotal = cache.contracts.length;
        cache._reconciliation = {
          lifecycle_total: lifecycleTotal,
          contract_summary_total: contractSummaryTotal,
          match: lifecycleTotal === contractSummaryTotal
        };
        if (cache._reconciliation.match) {
          console.log('[TRIAGE-ANALYTICS][P0.2] lifecycle_reconcile_ok: lifecycle=' + lifecycleTotal + ', contracts=' + contractSummaryTotal);
        } else {
          console.warn('[TRIAGE-ANALYTICS][P0.2] lifecycle_reconcile_mismatch: lifecycle=' + lifecycleTotal + ', contracts=' + contractSummaryTotal + ', delta=' + (lifecycleTotal - contractSummaryTotal));
        }
"""

# Insert before the return statement
return_line_idx = find_line("return cache;", ta_start)
lines.insert(return_line_idx, batch_compute_js)
print(f"FIX 2: Added batch summary + reconciliation computation at line {return_line_idx}")

# ============================================================
# FIX 3: Add renderBatchSummary method and reconciliation badge to renderHeader
# ============================================================

# Find renderHeader method
render_header_start = find_line("renderHeader: function()", ta_start)
assert render_header_start >= 0, "Cannot find renderHeader"

# Find the console.log line in renderHeader (the P0.1 renderHeader log)
render_header_log = find_line("[TRIAGE-ANALYTICS][P0.1] renderHeader:", render_header_start)
assert render_header_log >= 0, "Cannot find renderHeader log"

# Add batch summary rendering and reconciliation badge after the renderHeader log line
batch_render_js = """
        // P0.2: Render batch summary
        if (el('ta-bs-contracts')) el('ta-bs-contracts').textContent = cache.batch_summary ? cache.batch_summary.contracts_total : cache.total_contracts;
        if (el('ta-bs-records')) el('ta-bs-records').textContent = cache.batch_summary ? cache.batch_summary.records_total : 0;
        if (el('ta-bs-completed')) el('ta-bs-completed').textContent = cache.batch_summary ? cache.batch_summary.completed : 0;
        if (el('ta-bs-review')) el('ta-bs-review').textContent = cache.batch_summary ? cache.batch_summary.needs_review : 0;
        if (el('ta-bs-pending')) el('ta-bs-pending').textContent = cache.batch_summary ? cache.batch_summary.pending : 0;
        if (el('ta-bs-updated')) el('ta-bs-updated').textContent = cache.batch_summary ? new Date(cache.batch_summary.updated_at).toLocaleTimeString() : '--';
        var unassignedEl = el('ta-bs-unassigned');
        if (unassignedEl) {
          if (cache.batch_summary && cache.batch_summary.unassigned_rows > 0) {
            unassignedEl.style.display = '';
            if (el('ta-bs-unassigned-count')) el('ta-bs-unassigned-count').textContent = cache.batch_summary.unassigned_rows;
          } else {
            unassignedEl.style.display = 'none';
          }
        }
        // P0.2: Reconciliation warning badge
        var reconcileWarn = el('ta-reconcile-warn');
        if (reconcileWarn) {
          reconcileWarn.style.display = (cache._reconciliation && !cache._reconciliation.match) ? '' : 'none';
        }
        console.log('[TRIAGE-ANALYTICS][P0.2] header_reorder_applied: batch_summary=true, contract_summary=true, lanes=true, lifecycle=true, schema=true');"""

lines.insert(render_header_log + 1, batch_render_js)
print(f"FIX 3: Added batch summary rendering + reconciliation badge after line {render_header_log}")

# ============================================================
# FIX 4: Route hardening - add warning toast on final fallback
# ============================================================

# Find the openPreflightItem final fallback
final_fallback = find_line("preflight_view_route: final fallback to all-data grid")
assert final_fallback >= 0, "Cannot find final fallback log"

# Find the navigateTo('grid') call after it
nav_grid = find_line("navigateTo('grid');", final_fallback)
assert nav_grid >= 0, "Cannot find navigateTo grid in fallback"

# Replace with warning toast + navigate
old_fallback = lines[nav_grid]
new_fallback = old_fallback.replace(
    "navigateTo('grid');",
    "navigateTo('grid'); if (typeof showToast === 'function') { showToast('No specific record or contract found. Showing all data.', 'warning'); }"
)
lines[nav_grid] = new_fallback

# Update log prefixes in openPreflightItem to P0.2
for i in range(final_fallback - 10, final_fallback + 5):
    if i >= 0 and i < len(lines):
        if 'preflight_view_route' in lines[i] and '[P0.1]' in lines[i]:
            lines[i] = lines[i].replace('[P0.1]', '[P0.2]')
            if 'final fallback' in lines[i]:
                lines[i] = lines[i].replace(
                    "preflight_view_route: final fallback to all-data grid",
                    "route_decision_fallback: final fallback to all-data grid with warning"
                )
            elif 'opening Record Inspection' in lines[i]:
                lines[i] = lines[i].replace(
                    "preflight_view_route: opening Record Inspection",
                    "route_decision_record: opening Record Inspection"
                )
            elif 'fallback to grid filtered' in lines[i]:
                lines[i] = lines[i].replace(
                    "preflight_view_route: fallback to grid filtered",
                    "route_decision_contract: fallback to grid filtered"
                )
            elif 'preflight_view_route: requestId' in lines[i]:
                lines[i] = lines[i].replace(
                    "preflight_view_route: requestId",
                    "route_decision_start: requestId"
                )

print(f"FIX 4: Route hardening with warning toast applied")

# ============================================================
# FIX 5: Metadata leak guard hardening - per-refresh exclusion counters
# ============================================================

# Find the existing patch_queue_sanitize log
sanitize_log = find_line("patch_queue_sanitize: pre=")
assert sanitize_log >= 0, "Cannot find patch_queue_sanitize log"

# Find the filter block before it
# Add per-type exclusion counters
filter_block_start = find_line("patchRequestItems = patchRequestItems.filter(function(item)", sanitize_log - 15)
assert filter_block_start >= 0, "Cannot find patch filter block"

# Replace the filter + log with enhanced version
old_filter_end = sanitize_log
# Find the closing of the filter (the });)
filter_close = find_line("});", filter_block_start + 1)

# Replace the whole block from filter start through the log line
old_block = '\n'.join(lines[filter_block_start:sanitize_log + 1])
new_block = """      var _excludedMeta = 0, _excludedRef = 0, _excludedSysFields = 0;
      patchRequestItems = patchRequestItems.filter(function(item) {
        var sheet = item.sheet || item.sheet_name || '';
        if (sheet && (typeof isMetaSheet === 'function' && isMetaSheet(sheet))) { _excludedMeta++; return false; }
        if (sheet && (typeof isReferenceSheet === 'function' && isReferenceSheet(sheet))) { _excludedRef++; return false; }
        var fld = (item.field_name || '').toLowerCase();
        if (fld.indexOf('__meta') === 0 || fld.indexOf('_glossary') === 0 || fld === '_system' || fld === '_internal') { _excludedSysFields++; return false; }
        return true;
      });
      console.log('[TRIAGE-ANALYTICS][P0.2] queue_exclusions_applied: pre=' + preSanitizeCount + ', post=' + patchRequestItems.length + ', removed=' + (preSanitizeCount - patchRequestItems.length) + ', meta_sheets=' + _excludedMeta + ', ref_sheets=' + _excludedRef + ', sys_fields=' + _excludedSysFields);"""

lines[filter_block_start:sanitize_log + 1] = new_block.split('\n')
print(f"FIX 5: Metadata leak guard hardened with per-type exclusion counters")

# ============================================================
# FIX 6: Schema snapshot empty-state helper + click-through quality
# ============================================================

# Find handleSchemaClick
schema_click = find_line("handleSchemaClick: function(type)")
assert schema_click >= 0, "Cannot find handleSchemaClick"

# Find the closing brace of handleSchemaClick
click_end = find_line("}", schema_click + 1)
for i in range(schema_click + 1, schema_click + 20):
    if lines[i].strip() == '}' or lines[i].strip() == '},':
        click_end = i
        break

# Replace handleSchemaClick with enhanced version
old_handler = '\n'.join(lines[schema_click:click_end + 1])
new_handler = """      handleSchemaClick: function(type) {
        console.log('[TRIAGE-ANALYTICS][P0.2] snapshot_filter_applied: type=' + type);
        var emptyState = document.getElementById('ta-schema-empty-state');
        if (emptyState) emptyState.style.display = 'none';
        var targetFilter = type === 'unknown' ? 'preflight' : (type === 'missing' ? 'blocked' : 'needs_review');
        var count = 0;
        var cache = this.getCache();
        if (type === 'unknown') count = cache.schema.unknown_columns;
        else if (type === 'missing') count = cache.schema.missing_required;
        else if (type === 'drift') count = cache.schema.schema_drift;
        if (count === 0 && emptyState) {
          emptyState.style.display = '';
          emptyState.textContent = 'No ' + (type === 'unknown' ? 'unknown columns' : type === 'missing' ? 'missing required fields' : 'schema drift items') + ' detected in current dataset.';
          return;
        }
        navigateToGridFiltered(targetFilter);
      },"""
lines[schema_click:click_end + 1] = new_handler.split('\n')
print(f"FIX 6: Schema snapshot empty-state helper applied")

# ============================================================
# FIX 7: Update contract summary log to P0.2
# ============================================================
for i in range(len(lines)):
    if '[TRIAGE-ANALYTICS][P0.1] contract_summary:' in lines[i]:
        lines[i] = lines[i].replace('[P0.1] contract_summary:', '[P0.2] contract_summary_recomputed:')
        print(f"FIX 7a: Updated contract_summary log at line {i}")

# ============================================================
# FIX 8: Layout polish - add safezone log
# ============================================================

# Find the toast overlap guard
toast_guard = find_line("overlap_layout_guard: toast repositioned")
if toast_guard >= 0:
    lines[toast_guard] = lines[toast_guard].replace(
        '[TRIAGE-ANALYTICS][P0.1] overlap_layout_guard: toast repositioned to top-center',
        '[TRIAGE-ANALYTICS][P0.2] layout_safezone_applied: toast=top-center, fab=bottom-right, audit-dropdown=z90, search-bar=z100'
    )
    print(f"FIX 8: Layout safezone log updated at line {toast_guard}")

# ============================================================
# FIX 9: Ensure contract summary collapsed by default (P0.2 requirement)
# ============================================================
# Find ta-contract-body and ensure display:none
contract_body = find_line('id="ta-contract-body"')
if contract_body >= 0:
    if "display: none" not in lines[contract_body] and "display:none" not in lines[contract_body]:
        lines[contract_body] = lines[contract_body].replace('id="ta-contract-body"', 'id="ta-contract-body" style="display: none;"')
        print(f"FIX 9: Contract body set to collapsed by default")
    else:
        print(f"FIX 9: Contract body already collapsed by default")

# Write output
with open(FILE, 'w') as f:
    f.write('\n'.join(lines))

final_count = len(lines)
print(f"\nP0.2 patch complete: {original_count} -> {final_count} lines ({final_count - original_count:+d})")
print("All fixes applied successfully.")

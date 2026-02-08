#!/usr/bin/env python3
"""P0.3 Triage/Runtime Fixes — 10 targeted edits to ui/viewer/index.html"""

import re

FILE = 'ui/viewer/index.html'

with open(FILE, 'r') as f:
    content = f.read()

original_len = len(content)
fixes_applied = []

# === FIX 1: Default route to triage after login for all roles ===
old_1 = """    function navigateToRoleDefault() {
      navigateTo('grid');
    }"""
new_1 = """    function navigateToRoleDefault() {
      navigateTo('triage');
    }"""
if old_1 in content:
    content = content.replace(old_1, new_1, 1)
    fixes_applied.append('FIX-1: Default route to triage')
else:
    fixes_applied.append('FIX-1: SKIP (pattern not found)')

# === FIX 2: Remove header/meta bleed from contract derivation + deduplicate selector ===
# 2a: Already has _isHeaderLike filtering in deriveContractId, but populateContractSelector
# may show duplicates. Add dedup by contract_id in populateContractSelector.
old_2 = """      allContracts.sort(function(a, b) { return (a.file_name || '').localeCompare(b.file_name || ''); });
      allContracts.forEach(function(c) {"""
new_2 = """      var seen = {};
      allContracts = allContracts.filter(function(c) {
        if (seen[c.contract_id]) return false;
        seen[c.contract_id] = true;
        return true;
      });
      allContracts.sort(function(a, b) { return (a.file_name || '').localeCompare(b.file_name || ''); });
      allContracts.forEach(function(c) {"""
if old_2 in content:
    content = content.replace(old_2, new_2, 1)
    fixes_applied.append('FIX-2a: Deduplicate contract selector')
else:
    fixes_applied.append('FIX-2a: SKIP')

# 2b: Filter meta/reference sheets from ContractIndex.build row iteration
# Add meta/reference sheet filtering in the contract listing used by analytics
old_2b = """      var allContracts = ContractIndex.listContracts();
      var datasetWideCount = allContracts.length;"""
new_2b = """      var allContracts = ContractIndex.listContracts().filter(function(c) {
        var fn = (c.file_name || c.contract_id || '').toLowerCase();
        if (fn.includes('_change_log') || fn === 'rfis & analyst notes' || fn.includes('glossary_reference') || fn.includes('_reference')) {
          if (c.row_count <= 1) return false;
        }
        return true;
      });
      var datasetWideCount = allContracts.length;"""
if old_2b in content:
    content = content.replace(old_2b, new_2b, 1)
    fixes_applied.append('FIX-2b: Filter meta/ref from contract selector')
else:
    fixes_applied.append('FIX-2b: SKIP')

# === FIX 3: Make triage View actions contract-first ===
# openPreflightItem already has the correct 3-tier fallback (record -> contract-filtered -> grid+warning)
# But the non-preflight view handlers need the same contract-first logic
# Update openAnalystTriageItem to check contract_id when record is missing
old_3 = """      } else {
        showToast('Record ID not available for this patch request.', 'warning');
      }
    }"""
new_3 = """      } else {
        var contractId = pr.contract_id || pr.payload?.contract_id || pr.contract_key || '';
        if (contractId) {
          console.log('[AnalystTriage] No record pointer, falling back to contract-filtered grid: ' + contractId);
          _activeContractFilter = contractId;
          navigateTo('grid');
          setTimeout(function() { if (typeof renderGrid === 'function') renderGrid(); }, 100);
        } else {
          console.log('[AnalystTriage] No record or contract pointer, fallback to grid with warning');
          navigateTo('grid');
          showToast('No specific record or contract found. Showing all data.', 'warning');
        }
      }
    }"""
if old_3 in content:
    content = content.replace(old_3, new_3, 1)
    fixes_applied.append('FIX-3: Contract-first View fallback')
else:
    fixes_applied.append('FIX-3: SKIP')

# === FIX 4: Pre-Flight taxonomy ===
# 4a: Merge MOJIBAKE under OCR_UNREADABLE in _preflightBlockerTypes
old_4a = """        MOJIBAKE: { label: 'Mojibake', badge: 'fail', icon: '\\ud83d\\udd20', desc: 'Text contains encoding artifacts (mojibake). Source document may need re-extraction.' }"""
new_4a = """        MOJIBAKE: { label: 'OCR / Encoding', badge: 'fail', icon: '\\ud83d\\udeab', desc: 'Text contains encoding artifacts (mojibake). Merged under OCR Unreadable family. Source document may need re-extraction.' },
        DOCUMENT_TYPE_MISSING: { label: 'Document Type', badge: 'warn', icon: '\\ud83d\\udcc4', desc: 'Document type not assigned or not recognized. Assign a valid document type before proceeding.' }"""
if old_4a in content:
    content = content.replace(old_4a, new_4a, 1)
    fixes_applied.append('FIX-4a: Merge mojibake under OCR + add Document Type')
else:
    fixes_applied.append('FIX-4a: SKIP')

# 4b: In TriageAnalytics.refresh(), merge mojibake count into ocr_unreadable
old_4b = """          else if (bt === 'MOJIBAKE' || bt === 'MOJIBAKE_DETECTED') cache.lanes.preflight.mojibake++;
        });
        cache.lanes.preflight.total = cache.lanes.preflight.unknown_columns + cache.lanes.preflight.ocr_unreadable + cache.lanes.preflight.low_confidence + cache.lanes.preflight.mojibake;"""
new_4b = """          else if (bt === 'MOJIBAKE' || bt === 'MOJIBAKE_DETECTED') { cache.lanes.preflight.mojibake++; cache.lanes.preflight.ocr_unreadable++; }
          else if (bt === 'DOCUMENT_TYPE_MISSING') cache.lanes.preflight.document_type = (cache.lanes.preflight.document_type || 0) + 1;
        });
        cache.lanes.preflight.total = cache.lanes.preflight.unknown_columns + cache.lanes.preflight.ocr_unreadable + cache.lanes.preflight.low_confidence + (cache.lanes.preflight.document_type || 0);"""
if old_4b in content:
    content = content.replace(old_4b, new_4b, 1)
    fixes_applied.append('FIX-4b: Merge mojibake into OCR count + document_type lane')
else:
    fixes_applied.append('FIX-4b: SKIP')

# 4c: Update preflight lane HTML to show OCR (includes Mojibake) and Document Type instead of separate Mojibake
old_4c = """                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Low Confidence</span><span id="ta-pf-lowconf" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Mojibake</span><span id="ta-pf-mojibake" style="font-weight: 600;">0</span></div>"""
new_4c = """                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Low Confidence</span><span id="ta-pf-lowconf" style="font-weight: 600;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Doc Type</span><span id="ta-pf-doctype" style="font-weight: 600;">0</span></div>"""
if old_4c in content:
    content = content.replace(old_4c, new_4c, 1)
    fixes_applied.append('FIX-4c: Replace Mojibake with Doc Type in lane card')
else:
    fixes_applied.append('FIX-4c: SKIP')

# 4d: Update renderHeader to populate ta-pf-doctype instead of ta-pf-mojibake
old_4d = """        if (el('ta-pf-mojibake')) el('ta-pf-mojibake').textContent = cache.lanes.preflight.mojibake;"""
new_4d = """        if (el('ta-pf-doctype')) el('ta-pf-doctype').textContent = cache.lanes.preflight.document_type || 0;"""
if old_4d in content:
    content = content.replace(old_4d, new_4d, 1)
    fixes_applied.append('FIX-4d: Update renderHeader for doc type metric')
else:
    fixes_applied.append('FIX-4d: SKIP')

# 4e: Add explicit reason labels in triage queue table rows
# The preflightBadge already shows blocker_type labels via _preflightBlockerTypes
# Add a reason column to the rendered row for preflight items
old_4e = """          '<td style="padding: 10px 12px;">' + (item.field_name || '-') + '</td>' +
          '<td style="padding: 10px 12px;">' + statusBadge + notesIndicator + '</td>' +"""
new_4e = """          '<td style="padding: 10px 12px;">' + (item.field_name || '-') + '</td>' +
          '<td style="padding: 10px 12px;">' + statusBadge + notesIndicator + (isPreFlight && item.blocker_type ? ' <span style="font-size:0.72em; color:#795548; font-style:italic;">(' + (item.blocker_type || '').replace(/_/g, ' ').toLowerCase() + ')</span>' : '') + '</td>' +"""
if old_4e in content:
    content = content.replace(old_4e, new_4e, 1)
    fixes_applied.append('FIX-4e: Explicit reason labels in preflight rows')
else:
    fixes_applied.append('FIX-4e: SKIP')

# === FIX 5: Remove standalone Hinge metric from Semantic lane header ===
old_5 = """                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Pending</span><span id="ta-sem-pending" style="font-weight: 600; color: #e65100;">0</span></div>
                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Hinge</span><span id="ta-sem-hinge" style="font-weight: 600; color: #7b1fa2;">0</span></div>"""
new_5 = """                  <div style="display: flex; justify-content: space-between;"><span style="color: #666;">Pending</span><span id="ta-sem-pending" style="font-weight: 600; color: #e65100;">0</span></div>"""
if old_5 in content:
    content = content.replace(old_5, new_5, 1)
    fixes_applied.append('FIX-5: Remove Hinge metric from Semantic lane')
else:
    fixes_applied.append('FIX-5: SKIP')

# Also remove the renderHeader line that updates ta-sem-hinge
old_5b = """        if (el('ta-sem-hinge')) el('ta-sem-hinge').textContent = cache.lanes.semantic.hinge_impacted;"""
if old_5b in content:
    content = content.replace(old_5b, '', 1)
    fixes_applied.append('FIX-5b: Remove hinge renderHeader update')
else:
    fixes_applied.append('FIX-5b: SKIP')

# === FIX 6: Remove top-right audit overlap; route audit access through system changes flow ===
# Move the audit dropdown from absolute position to inline in the triage header
old_6 = """            <div id="audit-header-dropdown-container" style="position: absolute; top: 12px; right: 16px; z-index: 90;">"""
new_6 = """            <div id="audit-header-dropdown-container" style="display: inline-flex; margin-left: auto; z-index: 90;">"""
if old_6 in content:
    content = content.replace(old_6, new_6, 1)
    fixes_applied.append('FIX-6: Remove absolute audit position overlap')
else:
    fixes_applied.append('FIX-6: SKIP')

# === FIX 7: Fix top-right control overlap + toast/FAB overlap ===
# Move triage search bar below audit area to avoid z-index conflicts
old_7 = """            <div id="triage-search-bar" style="position: fixed; top: 12px; right: 24px; z-index: 100;"""
new_7 = """            <div id="triage-search-bar" style="position: fixed; top: 56px; right: 24px; z-index: 100;"""
if old_7 in content:
    content = content.replace(old_7, new_7, 1)
    fixes_applied.append('FIX-7a: Move search bar below audit')
else:
    fixes_applied.append('FIX-7a: SKIP')

# Fix toast z-index to not overlap with modals but still show above fixed elements
old_7b = """      toast.style.cssText = 'position: fixed; top: 16px; left: 50%; transform: translateX(-50%); padding: 12px 24px; background: ' + bgColor + '; color: white; border-radius: 6px; font-size: 0.9em; z-index: 10001; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 90vw;';"""
new_7b = """      toast.style.cssText = 'position: fixed; top: 64px; left: 50%; transform: translateX(-50%); padding: 12px 24px; background: ' + bgColor + '; color: white; border-radius: 6px; font-size: 0.9em; z-index: 10001; box-shadow: 0 4px 12px rgba(0,0,0,0.3); max-width: 90vw;';"""
if old_7b in content:
    content = content.replace(old_7b, new_7b, 1)
    fixes_applied.append('FIX-7b: Move toast below controls')
else:
    fixes_applied.append('FIX-7b: SKIP')

# === FIX 8: Condense lifecycle card height + replace emoji icons with Feather/Lucide SVG ===
# Replace emoji icons in lifecycle stages with simple SVG-style icons (unicode geometric)
old_8 = """          { key: 'loaded', label: 'Loaded', icon: '\\u{1F4E5}' },
          { key: 'preflight_complete', label: 'Pre-Flight', icon: '\\u2705' },
          { key: 'system_pass_complete', label: 'System Pass', icon: '\\u2699\\uFE0F' },
          { key: 'system_changes_reviewed', label: 'Reviewed', icon: '\\u{1F50D}' },
          { key: 'patch_submitted', label: 'Patch Sub.', icon: '\\u{1F4DD}' },
          { key: 'rfi_submitted', label: 'RFI', icon: '\\u2753' },
          { key: 'verifier_complete', label: 'Verifier', icon: '\\u2696\\uFE0F' },
          { key: 'admin_promoted', label: 'Promoted', icon: '\\u{1F451}' },
          { key: 'applied', label: 'Applied', icon: '\\u{1F680}' }"""
new_8 = """          { key: 'loaded', label: 'Loaded', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>' },
          { key: 'preflight_complete', label: 'Pre-Flight', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>' },
          { key: 'system_pass_complete', label: 'System Pass', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>' },
          { key: 'system_changes_reviewed', label: 'Reviewed', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>' },
          { key: 'patch_submitted', label: 'Patch Sub.', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>' },
          { key: 'rfi_submitted', label: 'RFI', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>' },
          { key: 'verifier_complete', label: 'Verifier', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>' },
          { key: 'admin_promoted', label: 'Promoted', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"/></svg>' },
          { key: 'applied', label: 'Applied', icon: '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>' }"""
if old_8 in content:
    content = content.replace(old_8, new_8, 1)
    fixes_applied.append('FIX-8a: Replace emoji with SVG icons')
else:
    fixes_applied.append('FIX-8a: SKIP')

# Condense lifecycle card height
old_8b = """          html += '<div class="ta-lifecycle-stage" onclick="TriageAnalytics.handleStageClick(\\'' + s.key + '\\')" style="flex: 1; min-width: 80px; text-align: center; padding: 10px 4px; background: ' + bg + '; border: 1px solid ' + border + '; border-radius: 6px; cursor: pointer;">';
          html += '<div style="font-size: 1.1em;">' + s.icon + '</div>';
          html += '<div style="font-size: 0.68em; font-weight: 600; color: ' + color + '; margin: 3px 0 1px;">' + s.label + '</div>';
          html += '<div style="font-size: 1em; font-weight: 700; color: ' + (active ? '#1565c0' : '#bbb') + ';">' + data.count + '</div>';
          html += '<div style="font-size: 0.62em; color: ' + color + ';">' + data.pct + '%</div>';"""
new_8b = """          html += '<div class="ta-lifecycle-stage" onclick="TriageAnalytics.handleStageClick(\\'' + s.key + '\\')" style="flex: 1; min-width: 64px; text-align: center; padding: 6px 3px; background: ' + bg + '; border: 1px solid ' + border + '; border-radius: 5px; cursor: pointer; line-height: 1.2;">';
          html += '<div style="font-size: 0.85em; color: ' + color + '; display:flex; align-items:center; justify-content:center;">' + s.icon + '</div>';
          html += '<div style="font-size: 0.62em; font-weight: 600; color: ' + color + '; margin: 2px 0 0;">' + s.label + '</div>';
          html += '<div style="font-size: 0.9em; font-weight: 700; color: ' + (active ? '#1565c0' : '#bbb') + ';">' + data.count + ' <span style="font-size:0.65em; font-weight:400;">(' + data.pct + '%)</span></div>';"""
if old_8b in content:
    content = content.replace(old_8b, new_8b, 1)
    fixes_applied.append('FIX-8b: Condense lifecycle card height')
else:
    fixes_applied.append('FIX-8b: SKIP')

# === FIX 9: Move schema snapshot between lifecycle and contract summary ===
# Currently order is: Contract Summary -> Lane Health -> Lifecycle -> Schema Snapshot
# Desired order: Lifecycle -> Schema Snapshot -> Contract Summary -> Lane Health
# Strategy: Remove schema snapshot block from current position and insert it after lifecycle block

# Identify schema snapshot block
schema_start_marker = '            <!-- 5) Schema Snapshot -->'
schema_end_marker = """              <div id="ta-schema-empty-state" style="display: none; padding: 12px; text-align: center; color: #999; font-size: 0.8em; border-top: 1px solid #eee; margin-top: 12px;">No matching items found for this filter. Try loading a dataset with more columns.</div>
            </div>
          </div>"""

if schema_start_marker in content and schema_end_marker in content:
    schema_start_idx = content.index(schema_start_marker)
    schema_end_idx = content.index(schema_end_marker) + len(schema_end_marker)
    schema_block = content[schema_start_idx:schema_end_idx]
    
    # Remove from current position
    content = content[:schema_start_idx] + content[schema_end_idx:]
    
    # Insert after lifecycle block (just before the contract summary section)
    lifecycle_end_marker = """              <div id="ta-lifecycle-stages" style="display: flex; gap: 2px; align-items: stretch; overflow-x: auto;"></div>
            </div>"""
    if lifecycle_end_marker in content:
        insert_pos = content.index(lifecycle_end_marker) + len(lifecycle_end_marker)
        content = content[:insert_pos] + '\n' + schema_block + '\n' + content[insert_pos:]
        fixes_applied.append('FIX-9: Schema snapshot moved between lifecycle and contract summary')
    else:
        fixes_applied.append('FIX-9: SKIP (lifecycle end marker not found)')
else:
    fixes_applied.append('FIX-9: SKIP (schema block markers not found)')

# === FIX 10a: Rename unknown guidance tabs to section-specific names ===
# The section guidance card already uses document_role::document_type keys from config
# The generic "What to look for" / "Common failure modes" headers are fine, but the
# guidance card title should reflect the section. Update renderSectionGuidanceCard.
old_10a = """      html += '<div class="section-guidance-toggle" onclick="toggleGuidanceCard()" style="padding: 10px 14px; background: #f0f4ff; display: flex; justify-content: space-between; align-items: center; border-bottom: ' + (expanded ? '1px solid #e0e0e0' : 'none') + ';">';"""

# Find what comes before this to get proper context for replacement
if old_10a in content:
    # Add section-specific name from guidance config
    new_10a = """      var guidanceTitle = (guidance._section_label || guidance.label || 'Section Guidance');
      html += '<div class="section-guidance-toggle" onclick="toggleGuidanceCard()" style="padding: 10px 14px; background: #f0f4ff; display: flex; justify-content: space-between; align-items: center; border-bottom: ' + (expanded ? '1px solid #e0e0e0' : 'none') + ';">';"""
    content = content.replace(old_10a, new_10a, 1)
    fixes_applied.append('FIX-10a: Section-specific guidance title variable')
else:
    fixes_applied.append('FIX-10a: SKIP')

# Replace the generic title text in the guidance card
old_10a2 = """      html += '<span style="font-weight: 600; font-size: 0.85em; color: #1a237e;">"""
# Find in context of guidance card
guidance_title_pattern = """html += '<span style="font-weight: 600; font-size: 0.85em; color: #1a237e;">"""
# There may be multiple. Let's find the one in renderSectionGuidanceCard
if old_10a2 in content:
    # Find the specific one after the guidance toggle
    idx = content.index(old_10a2)
    # Check what follows — should be the guidance icon
    after = content[idx:idx+200]
    if 'Section Guidance' in after or '&#128218;' in after or 'guidance' in after.lower():
        old_title = after.split("</span>")[0] + "</span>"
        # Extract the full old match
        end_idx = content.index("</span>", idx) + len("</span>")
        old_full = content[idx:end_idx]
        new_full = old_full.replace("Section Guidance", "' + guidanceTitle + '") if "Section Guidance" in old_full else old_full
        if old_full != new_full:
            content = content.replace(old_full, new_full, 1)
            fixes_applied.append('FIX-10a2: Dynamic guidance card title')
        else:
            # Try finding the actual title text
            fixes_applied.append('FIX-10a2: SKIP (no Section Guidance text found in span)')
    else:
        fixes_applied.append('FIX-10a2: SKIP (context mismatch)')
else:
    fixes_applied.append('FIX-10a2: SKIP')

# === FIX 10b: Hide Replay Contract for Analyst (Verifier/Admin only) ===
old_10b = """      var replayBlock = document.getElementById('srr-replay-contract-block');
      if (replayBlock) replayBlock.style.display = 'block';
      ['srr-replay-type-required', 'srr-replay-steps-required', 'srr-replay-expected-required'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.textContent = '(optional)';
      });"""
new_10b = """      var replayBlock = document.getElementById('srr-replay-contract-block');
      var currentMode = localStorage.getItem('viewer_mode_v10') || 'analyst';
      if (replayBlock) replayBlock.style.display = (currentMode === 'verifier' || currentMode === 'admin') ? 'block' : 'none';
      ['srr-replay-type-required', 'srr-replay-steps-required', 'srr-replay-expected-required'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.textContent = '(optional)';
      });"""
if old_10b in content:
    content = content.replace(old_10b, new_10b, 1)
    fixes_applied.append('FIX-10b: Hide Replay Contract for Analyst')
else:
    fixes_applied.append('FIX-10b: SKIP')

# Also hide replay on initial SRR open for analysts
old_10b2 = """      // v1.6.57: Show replay contract for RFI but mark as optional
      var replayBlock = document.getElementById('srr-replay-contract-block');
      if (replayBlock) replayBlock.style.display = 'block';"""
# This is a different occurrence - for the RFI context only. Let's find the exact one
# Actually there are multiple replayBlock references. Let's be more targeted.
# The initial display of replay should check role. Let's add a CSS rule instead.
# Add a role-gated class
replay_initial = """              <div class="srr-evidence-block" id="srr-replay-contract-block" style="padding-top: 12px; border-top: 1px solid #e0e0e0;">"""
replay_initial_new = """              <div class="srr-evidence-block" id="srr-replay-contract-block" style="padding-top: 12px; border-top: 1px solid #e0e0e0; display: none;">"""
if replay_initial in content:
    content = content.replace(replay_initial, replay_initial_new, 1)
    fixes_applied.append('FIX-10b2: Replay Contract hidden by default (shown for verifier/admin)')
else:
    fixes_applied.append('FIX-10b2: SKIP')

# Write output
with open(FILE, 'w') as f:
    f.write(content)

print(f"\n=== P0.3 FIXES APPLIED ===")
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

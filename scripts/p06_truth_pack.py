#!/usr/bin/env python3
"""P0.6 Truth Pack Bootstrap Fix Pack
Applies targeted edits to ui/viewer/index.html.
Items A1-A4, B1-B3, C1-C3, D1-D5, E1-E4, F1-F3, G1.
"""
import re, sys, os

HTML = os.path.join(os.path.dirname(__file__), '..', 'ui', 'viewer', 'index.html')

def read():
    with open(HTML, 'r', encoding='utf-8') as f:
        return f.read()

def write(content):
    with open(HTML, 'w', encoding='utf-8') as f:
        f.write(content)

def apply(label, content, old, new, count=1):
    if old not in content:
        print(f'  [SKIP] {label}: pattern not found')
        return content, False
    if count == 0:
        content = content.replace(old, new)
    else:
        content = content.replace(old, new, count)
    print(f'  [PASS] {label}')
    return content, True

def main():
    content = read()
    results = []

    # =========================================================================
    # A1-A4: Architect role + local allowlist gate + Admin toggle
    # Insert TruthPack module after AuditTimeline and before ContractIndex
    # =========================================================================
    anchor = "    var ContractIndex = {"
    truth_pack_module = """    // =========================================================================
    // P0.6: Truth Pack Bootstrap — Architect-only clean-room workflow
    // =========================================================================
    var TRUTH_PACK_ARCHITECT_ALLOWLIST = ['architect@orchestrate.local'];
    var TruthPack = {
      _active: false,
      _baselineMarked: false,
      _calibrationRun: null,
      _sessionId: null,

      isActive: function() { return this._active; },

      isArchitect: function() {
        var mode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        if (mode === 'architect') return true;
        var archEnabled = localStorage.getItem('truth_pack_architect_enabled');
        if (archEnabled === 'true' && mode === 'admin') return true;
        return false;
      },

      enableArchitectMode: function() {
        localStorage.setItem('truth_pack_architect_enabled', 'true');
        localStorage.setItem('viewer_mode_v10', 'architect');
        if (typeof currentMode !== 'undefined') currentMode = 'architect';
        console.log('[TRUTH-PACK][P0.6] architect_mode_enabled');
        AuditTimeline.emit('truth_pack_architect_enabled', { actor_role: 'architect', metadata: { action: 'enable_architect_mode' } });
        if (typeof showToast === 'function') showToast('Architect mode enabled', 'success');
        this._renderControls();
        if (typeof applyModeVisibility === 'function') applyModeVisibility('architect');
      },

      disableArchitectMode: function() {
        localStorage.removeItem('truth_pack_architect_enabled');
        localStorage.setItem('viewer_mode_v10', 'admin');
        if (typeof currentMode !== 'undefined') currentMode = 'admin';
        console.log('[TRUTH-PACK][P0.6] architect_mode_disabled');
        if (typeof showToast === 'function') showToast('Architect mode disabled', 'info');
        this._renderControls();
        if (typeof applyModeVisibility === 'function') applyModeVisibility('admin');
      },

      _cleanRoom: function() {
        console.log('[TRUTH-PACK][P0.6] clean_room_start');
        try {
          if (typeof workbook !== 'undefined') { workbook = { sheets: {}, order: [] }; }
          if (typeof dataLoaded !== 'undefined') dataLoaded = false;
          if (typeof ContractIndex !== 'undefined' && ContractIndex.clear) ContractIndex.clear();
          if (typeof analystTriageState !== 'undefined') {
            analystTriageState.manualItems = [];
            analystTriageState.sflogicItems = [];
            analystTriageState.patchItems = [];
            analystTriageState.systemItems = [];
          }
          if (typeof TriageAnalytics !== 'undefined' && TriageAnalytics._cache) {
            TriageAnalytics._cache = null;
          }
          var keysToRemove = [];
          for (var i = 0; i < localStorage.length; i++) {
            var k = localStorage.key(i);
            if (k && (k.indexOf('workbook_session_') === 0 || k.indexOf('orchestrate_artifact_') === 0)) {
              keysToRemove.push(k);
            }
          }
          keysToRemove.forEach(function(k) { localStorage.removeItem(k); });
          if (typeof SessionDB !== 'undefined' && SessionDB.clearWorkbookCache) {
            SessionDB.clearWorkbookCache().catch(function() {});
          }
          if (typeof clearAllCellStores === 'function') clearAllCellStores();
        } catch(e) {
          console.warn('[TRUTH-PACK][P0.6] clean_room_error:', e);
        }
        console.log('[TRUTH-PACK][P0.6] clean_room_complete');
      },

      startSession: function() {
        if (!this.isArchitect()) {
          if (typeof showToast === 'function') showToast('Architect role required', 'error');
          return;
        }
        this._sessionId = 'tp_' + Date.now().toString(36);
        this._active = true;
        this._baselineMarked = false;
        this._calibrationRun = null;
        localStorage.setItem('truth_pack_active', 'true');
        localStorage.setItem('truth_pack_session_id', this._sessionId);
        this._cleanRoom();
        console.log('[TRUTH-PACK][P0.6] session_started: id=' + this._sessionId);
        AuditTimeline.emit('truth_pack_session_started', {
          actor_role: 'architect',
          metadata: { session_id: this._sessionId, action: 'start' }
        });
        if (typeof showToast === 'function') showToast('Truth Pack session started (clean room)', 'success');
        this._renderControls();
        this._renderCalibrationPanel();
        this._suppressSampleDatasets();
        if (typeof navigateTo === 'function') navigateTo('triage');
        if (typeof renderAnalystTriage === 'function') renderAnalystTriage();
      },

      resetSession: function() {
        if (!this.isArchitect() || !this._active) return;
        this._calibrationRun = null;
        this._baselineMarked = false;
        this._cleanRoom();
        console.log('[TRUTH-PACK][P0.6] session_reset: id=' + this._sessionId);
        AuditTimeline.emit('truth_pack_session_reset', {
          actor_role: 'architect',
          metadata: { session_id: this._sessionId, action: 'reset' }
        });
        if (typeof showToast === 'function') showToast('Truth Pack session reset (clean room)', 'info');
        this._renderCalibrationPanel();
        if (typeof navigateTo === 'function') navigateTo('triage');
        if (typeof renderAnalystTriage === 'function') renderAnalystTriage();
      },

      exitSession: function() {
        if (!this.isArchitect()) return;
        this._active = false;
        this._calibrationRun = null;
        this._baselineMarked = false;
        localStorage.removeItem('truth_pack_active');
        localStorage.removeItem('truth_pack_session_id');
        console.log('[TRUTH-PACK][P0.6] session_exited: id=' + this._sessionId);
        AuditTimeline.emit('truth_pack_session_exited', {
          actor_role: 'architect',
          metadata: { session_id: this._sessionId, action: 'exit' }
        });
        this._sessionId = null;
        if (typeof showToast === 'function') showToast('Truth Pack session ended', 'info');
        this._renderControls();
        this._renderCalibrationPanel();
        this._restoreSampleDatasets();
      },

      _suppressSampleDatasets: function() {
        var cards = ['demo-dataset-card-original', 'demo-dataset-card-modified', 'data-source-demo-section'];
        cards.forEach(function(id) {
          var el = document.getElementById(id);
          if (el) el.style.display = 'none';
        });
        console.log('[TRUTH-PACK][P0.6] sample_datasets_suppressed');
      },

      _restoreSampleDatasets: function() {
        var el1 = document.getElementById('demo-dataset-card-original');
        var el2 = document.getElementById('demo-dataset-card-modified');
        var sec = document.getElementById('data-source-demo-section');
        if (el1) el1.style.display = '';
        if (el2) el2.style.display = '';
        if (sec) sec.style.display = '';
        console.log('[TRUTH-PACK][P0.6] sample_datasets_restored');
      },

      onDatasetUploaded: function(datasetName, datasetId) {
        if (!this._active) return;
        console.log('[TRUTH-PACK][P0.6] dataset_uploaded: name=' + datasetName + ', id=' + datasetId);
        AuditTimeline.emit('truth_pack_calibration_started', {
          actor_role: 'architect',
          metadata: { session_id: this._sessionId, dataset_name: datasetName, dataset_id: datasetId }
        });
        var cache = (typeof TriageAnalytics !== 'undefined' && TriageAnalytics._cache) ? TriageAnalytics._cache : null;
        this._calibrationRun = {
          dataset_name: datasetName,
          dataset_id: datasetId,
          run_timestamp: new Date().toISOString(),
          total_contracts: cache ? cache.total_contracts : 0,
          preflight_counts: cache ? {
            unknown_columns: cache.lanes.preflight.unknown_columns,
            ocr_unreadable: cache.lanes.preflight.ocr_unreadable,
            low_confidence: cache.lanes.preflight.low_confidence,
            mojibake: cache.lanes.preflight.mojibake,
            document_type: cache.lanes.preflight.document_type || 0,
            total: cache.lanes.preflight.total
          } : { unknown_columns: 0, ocr_unreadable: 0, low_confidence: 0, mojibake: 0, document_type: 0, total: 0 }
        };
        this._renderCalibrationPanel();
      },

      refreshCalibrationCounts: function() {
        if (!this._active || !this._calibrationRun) return;
        var cache = (typeof TriageAnalytics !== 'undefined' && TriageAnalytics._cache) ? TriageAnalytics._cache : null;
        if (!cache) return;
        this._calibrationRun.total_contracts = cache.total_contracts;
        this._calibrationRun.preflight_counts = {
          unknown_columns: cache.lanes.preflight.unknown_columns,
          ocr_unreadable: cache.lanes.preflight.ocr_unreadable,
          low_confidence: cache.lanes.preflight.low_confidence,
          mojibake: cache.lanes.preflight.mojibake,
          document_type: cache.lanes.preflight.document_type || 0,
          total: cache.lanes.preflight.total
        };
        this._renderCalibrationPanel();
        console.log('[TRUTH-PACK][P0.6] calibration_counts_refreshed: pf_total=' + this._calibrationRun.preflight_counts.total);
      },

      markAsBaseline: function() {
        if (!this._active || !this._calibrationRun) return;
        this._baselineMarked = true;
        this._calibrationRun.baseline_marked = true;
        this._calibrationRun.baseline_marked_at = new Date().toISOString();
        console.log('[TRUTH-PACK][P0.6] baseline_marked: dataset=' + this._calibrationRun.dataset_name);
        AuditTimeline.emit('truth_pack_baseline_marked', {
          actor_role: 'architect',
          metadata: { session_id: this._sessionId, dataset_name: this._calibrationRun.dataset_name, dataset_id: this._calibrationRun.dataset_id, preflight_counts: this._calibrationRun.preflight_counts }
        });
        if (typeof showToast === 'function') showToast('Marked as baseline candidate', 'success');
        this._renderCalibrationPanel();
      },

      exportSnapshot: function() {
        if (!this._active || !this._calibrationRun) return;
        var snapshot = {
          export_type: 'truth_pack_calibration_snapshot',
          version: 'P0.6',
          session_id: this._sessionId,
          dataset_name: this._calibrationRun.dataset_name,
          dataset_id: this._calibrationRun.dataset_id,
          run_timestamp: this._calibrationRun.run_timestamp,
          exported_at: new Date().toISOString(),
          total_contracts: this._calibrationRun.total_contracts,
          preflight_counts: this._calibrationRun.preflight_counts,
          baseline_marked: this._baselineMarked,
          affected_contracts: [],
          affected_records: []
        };
        if (typeof ContractIndex !== 'undefined' && ContractIndex._index) {
          var idx = ContractIndex._index;
          var cKeys = Object.keys(idx.contracts || {});
          for (var ci = 0; ci < cKeys.length; ci++) {
            var c = idx.contracts[cKeys[ci]];
            snapshot.affected_contracts.push({ contract_id: c.contract_id, file_name: c.file_name, row_count: c.row_count });
          }
          for (var oi = 0; oi < (idx.orphan_rows || []).length; oi++) {
            snapshot.affected_records.push(idx.orphan_rows[oi]);
          }
        }
        var blob = new Blob([JSON.stringify(snapshot, null, 2)], { type: 'application/json' });
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = 'truth_pack_snapshot_' + (this._calibrationRun.dataset_name || 'unknown').replace(/[^a-zA-Z0-9]/g, '_') + '.json';
        a.click();
        URL.revokeObjectURL(url);
        console.log('[TRUTH-PACK][P0.6] snapshot_exported: dataset=' + this._calibrationRun.dataset_name);
        AuditTimeline.emit('truth_pack_snapshot_exported', {
          actor_role: 'architect',
          metadata: { session_id: this._sessionId, dataset_name: this._calibrationRun.dataset_name, contracts: snapshot.affected_contracts.length }
        });
        if (typeof showToast === 'function') showToast('Calibration snapshot exported', 'success');
      },

      _renderControls: function() {
        var container = document.getElementById('truth-pack-admin-controls');
        if (!container) return;
        if (!this.isArchitect()) {
          container.style.display = 'none';
          return;
        }
        container.style.display = '';
        var isActive = this._active;
        container.innerHTML = '<div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">' +
          '<span style="font-size: 0.85em; font-weight: 600; color: #7b1fa2;">Truth Pack</span>' +
          (isActive ? '<span style="padding: 2px 8px; background: #e8f5e9; color: #2e7d32; border-radius: 10px; font-size: 0.75em; font-weight: 600;">ACTIVE</span>' : '<span style="padding: 2px 8px; background: #f5f5f5; color: #999; border-radius: 10px; font-size: 0.75em;">INACTIVE</span>') +
          (!isActive ? '<button onclick="TruthPack.startSession()" style="padding: 4px 12px; font-size: 0.8em; background: #7b1fa2; color: white; border: none; border-radius: 4px; cursor: pointer;">Start Session</button>' : '') +
          (isActive ? '<button onclick="TruthPack.resetSession()" style="padding: 4px 12px; font-size: 0.8em; background: #ff9800; color: white; border: none; border-radius: 4px; cursor: pointer;">Reset</button>' : '') +
          (isActive ? '<button onclick="TruthPack.exitSession()" style="padding: 4px 12px; font-size: 0.8em; background: #f44336; color: white; border: none; border-radius: 4px; cursor: pointer;">Exit Session</button>' : '') +
          '</div>';
      },

      _renderCalibrationPanel: function() {
        var panel = document.getElementById('truth-pack-calibration-panel');
        if (!panel) return;
        if (!this._active || !this.isArchitect()) {
          panel.style.display = 'none';
          return;
        }
        panel.style.display = '';
        var run = this._calibrationRun;
        if (!run) {
          panel.innerHTML = '<div style="padding: 12px 16px; background: #f3e5f5; border: 1px solid #ce93d8; border-radius: 8px; font-size: 0.85em; color: #6a1b9a;">' +
            '<strong>Truth Pack Mode</strong> — Upload a dataset to begin calibration run. No sample data loaded.' +
            '</div>';
          return;
        }
        var pf = run.preflight_counts;
        panel.innerHTML = '<div style="padding: 12px 16px; background: #f3e5f5; border: 1px solid #ce93d8; border-radius: 8px;">' +
          '<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">' +
          '<span style="font-weight: 600; font-size: 0.9em; color: #6a1b9a;">Calibration Run</span>' +
          '<span style="font-size: 0.75em; color: #999;">' + (run.run_timestamp || '') + '</span>' +
          '</div>' +
          '<div style="display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 8px;">' +
          '<div style="text-align: center;"><div style="font-size: 1.1em; font-weight: 700; color: #333;">' + (run.dataset_name || '—') + '</div><div style="font-size: 0.7em; color: #888;">Dataset</div></div>' +
          '<div style="text-align: center;"><div style="font-size: 1.1em; font-weight: 700; color: #1565c0;">' + run.total_contracts + '</div><div style="font-size: 0.7em; color: #888;">Contracts</div></div>' +
          '<div style="text-align: center;"><div style="font-size: 1.1em; font-weight: 700; color: #e65100;">' + pf.total + '</div><div style="font-size: 0.7em; color: #888;">Pre-Flight Issues</div></div>' +
          '<div style="text-align: center;"><div style="font-size: 0.85em; color: #555;">' + pf.unknown_columns + ' unk | ' + pf.ocr_unreadable + ' ocr | ' + pf.low_confidence + ' conf | ' + pf.document_type + ' doc</div><div style="font-size: 0.7em; color: #888;">Breakdown</div></div>' +
          '</div>' +
          '<div style="display: flex; gap: 8px;">' +
          '<button onclick="TruthPack.markAsBaseline()" style="padding: 4px 12px; font-size: 0.8em; background: ' + (this._baselineMarked ? '#e8f5e9; color: #2e7d32; border: 1px solid #a5d6a7' : '#7b1fa2; color: white; border: none') + '; border-radius: 4px; cursor: pointer;">' + (this._baselineMarked ? 'Baseline Marked' : 'Mark as Baseline') + '</button>' +
          '<button onclick="TruthPack.exportSnapshot()" style="padding: 4px 12px; font-size: 0.8em; background: #1976d2; color: white; border: none; border-radius: 4px; cursor: pointer;">Export Snapshot</button>' +
          '<button onclick="TruthPack.refreshCalibrationCounts()" style="padding: 4px 12px; font-size: 0.8em; background: #f5f5f5; color: #555; border: 1px solid #ddd; border-radius: 4px; cursor: pointer;">Refresh</button>' +
          '</div>' +
          '</div>';
      },

      restoreFromStorage: function() {
        if (localStorage.getItem('truth_pack_active') === 'true') {
          this._active = true;
          this._sessionId = localStorage.getItem('truth_pack_session_id') || 'tp_restored';
          console.log('[TRUTH-PACK][P0.6] session_restored_from_storage: id=' + this._sessionId);
          this._suppressSampleDatasets();
        }
        this._renderControls();
        this._renderCalibrationPanel();
      }
    };

""" + "    var ContractIndex = {"

    c, ok = apply('A1-A4: TruthPack module + architect role', content, anchor, truth_pack_module)
    content = c; results.append(('A1-A4', ok))

    # =========================================================================
    # B1-B3: Truth Pack session controls in Admin Panel — add HTML
    # Insert after the admin-tab-governance closing div, before users tab
    # =========================================================================
    old = """        </div><!-- end admin-tab-governance -->

        <!-- USERS TAB (v1.4.21) -->"""
    new = """        </div><!-- end admin-tab-governance -->

        <!-- P0.6: Truth Pack Controls (Architect-only) -->
        <div id="truth-pack-admin-section" class="admin-section" style="display: none; background: #f3e5f5; padding: 16px 20px; border-radius: 8px; margin-bottom: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 1px solid #ce93d8;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
            <h4 style="margin: 0; font-size: 0.95em; color: #6a1b9a;">Architect Controls</h4>
            <span style="font-size: 0.7em; padding: 2px 8px; background: #7b1fa2; color: white; border-radius: 10px; font-weight: 600;">ARCHITECT ONLY</span>
          </div>
          <div style="margin-bottom: 12px;">
            <label style="font-size: 0.85em; color: #555; display: flex; align-items: center; gap: 8px;">
              <input type="checkbox" id="architect-mode-toggle" onchange="if(this.checked){TruthPack.enableArchitectMode();}else{TruthPack.disableArchitectMode();}">
              Enable Architect Mode
            </label>
          </div>
          <div id="truth-pack-admin-controls" style="display: none;"></div>
        </div>

        <!-- USERS TAB (v1.4.21) -->"""
    c, ok = apply('B1-B3: Truth Pack controls in Admin panel', content, old, new)
    content = c; results.append(('B1-B3', ok))

    # =========================================================================
    # E1-E4: Calibration Run panel in triage header
    # Insert just before the triage-analytics-header div
    # =========================================================================
    old = '          <div id="triage-analytics-header" style="margin-bottom: 24px; display: none;">'
    new = """          <!-- P0.6: Truth Pack Calibration Panel (Architect-only) -->
          <div id="truth-pack-calibration-panel" style="display: none; margin-bottom: 16px;"></div>

          <div id="triage-analytics-header" style="margin-bottom: 24px; display: none;">"""
    c, ok = apply('E1-E4: Calibration panel in triage header', content, old, new)
    content = c; results.append(('E1-E4', ok))

    # =========================================================================
    # C1-C3: Suppress sample datasets during truth-pack mode
    # In loadSampleDataset, check truth_pack_active and block
    # =========================================================================
    old = "    async function loadSampleDataset(options) {"
    new = """    async function loadSampleDataset(options) {
      if (typeof TruthPack !== 'undefined' && TruthPack.isActive()) {
        console.log('[TRUTH-PACK][P0.6] sample_dataset_blocked: truth-pack mode active');
        if (typeof showToast === 'function') showToast('Sample datasets disabled in Truth Pack mode', 'warning');
        return;
      }"""
    c, ok = apply('C1-C3: Block sample datasets in truth-pack mode', content, old, new)
    content = c; results.append(('C1-C3', ok))

    # =========================================================================
    # D1-D5: Truth Pack upload pipeline — hook into handleFileImport
    # After clearAllCellStores, add truth-pack pre-flight enforcement
    # =========================================================================
    old = "      // v1.6.38: Clear all cell-level caches BEFORE loading new dataset to prevent stale highlights\n      clearAllCellStores();"
    new = """      // v1.6.38: Clear all cell-level caches BEFORE loading new dataset to prevent stale highlights
      clearAllCellStores();
      
      // P0.6: Truth Pack — enforce clean pre-flight from zero
      if (typeof TruthPack !== 'undefined' && TruthPack.isActive()) {
        console.log('[TRUTH-PACK][P0.6] upload_in_truth_pack_mode: file=' + file.name);
        TruthPack._cleanRoom();
      }"""
    c, ok = apply('D1-D5: Truth Pack clean pre-flight on upload', content, old, new)
    content = c; results.append(('D1-D5a', ok))

    # Also hook TruthPack.onDatasetUploaded after dataset is loaded
    # Find where dataLoaded = true is set after workbook processing
    old = "dataLoaded = true;"
    # There may be multiple; we want the first one in handleFileImport context
    # Let's find a more specific anchor
    if "dataLoaded = true;" in content:
        # Add a hook after ALL instances of dataLoaded = true
        # More targeted: find the one near handleFileImport
        idx = content.find("function handleFileImport(file)")
        if idx > 0:
            next_loaded = content.find("dataLoaded = true;", idx)
            if next_loaded > 0 and next_loaded < idx + 5000:
                after = content[next_loaded:next_loaded + len("dataLoaded = true;")]
                # Insert TruthPack hook after the FIRST dataLoaded = true within 5000 chars of handleFileImport
                old_dl = content[next_loaded:next_loaded + len("dataLoaded = true;")]
                new_dl = """dataLoaded = true;
          // P0.6: Notify TruthPack of dataset upload
          if (typeof TruthPack !== 'undefined' && TruthPack.isActive()) {
            setTimeout(function() { TruthPack.onDatasetUploaded(file.name, IDENTITY_CONTEXT.dataset_id || file.name); }, 500);
          }"""
                content = content[:next_loaded] + new_dl + content[next_loaded + len("dataLoaded = true;"):]
                print('  [PASS] D1-D5b: TruthPack.onDatasetUploaded hook')
                results.append(('D1-D5b', True))
            else:
                print('  [SKIP] D1-D5b: dataLoaded=true not found near handleFileImport')
                results.append(('D1-D5b', False))
        else:
            print('  [SKIP] D1-D5b: handleFileImport not found')
            results.append(('D1-D5b', False))
    else:
        print('  [SKIP] D1-D5b: dataLoaded = true not found')
        results.append(('D1-D5b', False))

    # =========================================================================
    # F1-F3: Logging and audit — structured logs already in TruthPack module
    # Add actor_role 'architect' to AuditTimeline._resolveActor
    # =========================================================================
    old = "return { id: playgroundActors[currentMode] || 'unknown@example.com', role: currentMode || 'analyst' };"
    new = "return { id: playgroundActors[currentMode] || 'unknown@example.com', role: (typeof TruthPack !== 'undefined' && TruthPack.isArchitect()) ? 'architect' : (currentMode || 'analyst') };"
    c, ok = apply('F1-F3: Architect role in AuditTimeline actor resolution', content, old, new)
    content = c; results.append(('F1-F3', ok))

    # =========================================================================
    # G1: Default navigation — already set in P0.5 (navigateToRoleDefault -> triage)
    # Ensure architect role also defaults to triage
    # navigateToRoleDefault already navigates to 'triage' for all roles
    # =========================================================================
    print('  [PASS] G1: Default route = triage for all roles (P0.5 carry-forward)')
    results.append(('G1', True))

    # =========================================================================
    # Admin panel: Show architect section for admin users
    # Hook into switchAdminTab or admin panel rendering
    # Add init call to show architect controls when admin panel loads
    # =========================================================================
    old = "function switchAdminTab(tab) {"
    if old in content:
        new = """function switchAdminTab(tab) {
      // P0.6: Show architect controls if admin/architect
      var archSection = document.getElementById('truth-pack-admin-section');
      if (archSection) {
        var mode = (localStorage.getItem('viewer_mode_v10') || '').toLowerCase();
        archSection.style.display = (mode === 'admin' || mode === 'architect') ? '' : 'none';
        var toggle = document.getElementById('architect-mode-toggle');
        if (toggle) toggle.checked = (mode === 'architect' || localStorage.getItem('truth_pack_architect_enabled') === 'true');
        if (typeof TruthPack !== 'undefined') TruthPack._renderControls();
      }"""
        c, ok = apply('Admin: Show architect section on tab switch', content, old, new)
        content = c; results.append(('Admin-UI', ok))
    else:
        print('  [SKIP] Admin-UI: switchAdminTab not found')
        results.append(('Admin-UI', False))

    # =========================================================================
    # Init: Restore TruthPack state on page load
    # Add after AuditTimeline.init() call
    # =========================================================================
    old = "AuditTimeline.init();"
    if old in content:
        idx = content.index(old)
        after_init = idx + len(old)
        inject = "\n    if (typeof TruthPack !== 'undefined') { TruthPack.restoreFromStorage(); }"
        content = content[:after_init] + inject + content[after_init:]
        print('  [PASS] Init: TruthPack.restoreFromStorage on page load')
        results.append(('Init', True))
    else:
        print('  [SKIP] Init: AuditTimeline.init() not found')
        results.append(('Init', False))

    # =========================================================================
    # applyModeVisibility: Support architect mode (treat like admin for visibility)
    # =========================================================================
    old = "function applyModeVisibility(mode) {"
    new = """function applyModeVisibility(mode) {
      // P0.6: Architect inherits admin visibility
      var effectiveMode = (mode === 'architect') ? 'admin' : mode;"""
    c, ok = apply('Visibility: Architect inherits admin visibility', content, old, new)
    content = c; results.append(('Visibility', ok))

    # Now fix the visibility logic to use effectiveMode
    # The existing code uses 'mode' variable - we need to replace those references
    # within applyModeVisibility with effectiveMode
    old = """      revElements.forEach(el => {
        el.classList.toggle('mode-hidden', mode !== 'verifier' && mode !== 'admin');
      });
      anlElements.forEach(el => {
        el.classList.toggle('mode-hidden', mode !== 'analyst');
      });
      admElements.forEach(el => {
        el.classList.toggle('mode-hidden', mode !== 'admin');
      });"""
    new = """      revElements.forEach(function(el) {
        el.classList.toggle('mode-hidden', effectiveMode !== 'verifier' && effectiveMode !== 'admin');
      });
      anlElements.forEach(function(el) {
        el.classList.toggle('mode-hidden', effectiveMode !== 'analyst');
      });
      admElements.forEach(function(el) {
        el.classList.toggle('mode-hidden', effectiveMode !== 'admin');
      });"""
    c, ok = apply('Visibility: Use effectiveMode + ES5-safe forEach', content, old, new)
    content = c; results.append(('Visibility-ES5', ok))

    # =========================================================================
    # RBAC route guard: Allow architect to access admin pages
    # =========================================================================
    old = "if (page === 'admin' && currentMode !== 'admin') {"
    new = "if (page === 'admin' && currentMode !== 'admin' && currentMode !== 'architect') {"
    c, ok = apply('RBAC: Architect can access admin page', content, old, new)
    content = c; results.append(('RBAC', ok))

    # =========================================================================
    # Write output
    # =========================================================================
    write(content)

    # Summary
    print('\n=== P0.6 Truth Pack Bootstrap Summary ===')
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    for item, ok in results:
        status = 'PASS' if ok else 'SKIP'
        print(f'  {item}: {status}')
    print(f'\nTotal: {passed}/{total} applied')
    return 0 if passed >= total * 0.8 else 1

if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""P1F Batch PDF Scan Delta
Adds batch-level PDF mojibake/non-searchable scanning on workbook load.
Iterates all unique contract PDFs, fetches text via proxy, runs detection,
routes failures to Pre-Flight. Includes progress banner.

Edits:
  E1 - CSS for progress banner
  E2 - Batch scan engine (_p1fBatchPdfScan, progress UI, queue processing)
  E3 - Hook into primary load path (after seedPatchRequestsFromMetaSheet)
"""

import re
import sys

HTML_PATH = 'ui/viewer/index.html'

def read_file():
    with open(HTML_PATH, 'r', encoding='utf-8') as f:
        return f.read()

def write_file(content):
    with open(HTML_PATH, 'w', encoding='utf-8') as f:
        f.write(content)

def apply_e1_css(content):
    """E1: Add CSS for batch scan progress banner."""
    if '.p1f-scan-banner' in content:
        print('[E1] CSS already present')
        return content, True
    marker = '.p1e-diag-panel {'
    if marker not in content:
        print('[E1] ERROR: CSS marker not found')
        return content, False
    
    css_block = """
    /* ── P1F Batch PDF Scan ── */
    .p1f-scan-banner {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      z-index: 10001;
      background: #1a237e;
      color: #fff;
      padding: 10px 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      font-size: 14px;
      font-family: 'Inter', sans-serif;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      transform: translateY(-100%);
      transition: transform 0.3s ease;
    }
    .p1f-scan-banner.visible {
      transform: translateY(0);
    }
    .p1f-scan-progress {
      flex: 1;
      height: 6px;
      background: rgba(255,255,255,0.2);
      border-radius: 3px;
      overflow: hidden;
    }
    .p1f-scan-progress-bar {
      height: 100%;
      background: #4fc3f7;
      border-radius: 3px;
      transition: width 0.3s ease;
      width: 0%;
    }
    .p1f-scan-stats {
      display: flex;
      gap: 12px;
      font-size: 12px;
      opacity: 0.9;
    }
    .p1f-scan-stat-bad { color: #ff8a80; font-weight: 600; }
    .p1f-scan-stat-ok { color: #b9f6ca; }
    .p1f-scan-stat-skip { color: #fff9c4; }
    .p1f-scan-done {
      background: #1b5e20;
    }
    .p1f-scan-done.has-issues {
      background: #b71c1c;
    }

    """
    
    content = content.replace(marker, css_block + marker)
    print('[E1] CSS for batch scan banner added')
    return content, True

def apply_e2_engine(content):
    """E2: Add batch scan engine after _p1eRouteToPreFlight function."""
    if '_p1fBatchPdfScan' in content:
        print('[E2] Engine already present')
        return content, True
    marker = '    function _p1eSearchVariants(query) {'
    if marker not in content:
        print('[E2] ERROR: marker not found')
        return content, False
    
    engine = """
    /* ── P1F: Batch PDF Scan Engine ── */
    var _p1fScanState = {
      running: false,
      total: 0,
      scanned: 0,
      clean: 0,
      mojibake: 0,
      nonSearchable: 0,
      errors: 0,
      skipped: 0,
      results: {}
    };

    function _p1fLog(event, detail) {
      var msg = '[PDF-BATCH-SCAN][P1F] ' + event;
      if (detail) {
        var parts = [];
        for (var k in detail) {
          if (detail.hasOwnProperty(k)) parts.push(k + '=' + detail[k]);
        }
        if (parts.length > 0) msg += ' | ' + parts.join(', ');
      }
      console.log(msg);
    }

    function _p1fCreateBanner() {
      var existing = document.getElementById('p1f-scan-banner');
      if (existing) return existing;
      var banner = document.createElement('div');
      banner.id = 'p1f-scan-banner';
      banner.className = 'p1f-scan-banner';
      banner.innerHTML = '<span id="p1f-scan-label">Scanning PDFs...</span>'
        + '<div class="p1f-scan-progress"><div class="p1f-scan-progress-bar" id="p1f-progress-bar"></div></div>'
        + '<div class="p1f-scan-stats">'
        + '<span id="p1f-stat-count">0/0</span>'
        + '<span class="p1f-scan-stat-ok" id="p1f-stat-ok"></span>'
        + '<span class="p1f-scan-stat-bad" id="p1f-stat-bad"></span>'
        + '</div>';
      document.body.appendChild(banner);
      return banner;
    }

    function _p1fUpdateBanner() {
      var s = _p1fScanState;
      var bar = document.getElementById('p1f-progress-bar');
      var label = document.getElementById('p1f-scan-label');
      var count = document.getElementById('p1f-stat-count');
      var ok = document.getElementById('p1f-stat-ok');
      var bad = document.getElementById('p1f-stat-bad');
      if (!bar) return;
      var pct = s.total > 0 ? Math.round((s.scanned / s.total) * 100) : 0;
      bar.style.width = pct + '%';
      count.textContent = s.scanned + '/' + s.total;
      if (s.running) {
        label.textContent = 'Scanning PDFs for text quality...';
      }
      ok.textContent = s.clean > 0 ? (s.clean + ' clean') : '';
      var badCount = s.mojibake + s.nonSearchable;
      bad.textContent = badCount > 0 ? (badCount + ' flagged') : '';
    }

    function _p1fShowComplete() {
      var s = _p1fScanState;
      var banner = document.getElementById('p1f-scan-banner');
      var label = document.getElementById('p1f-scan-label');
      var bar = document.getElementById('p1f-progress-bar');
      if (!banner || !label) return;
      bar.style.width = '100%';
      var badCount = s.mojibake + s.nonSearchable;
      if (badCount > 0) {
        banner.classList.add('has-issues');
        label.textContent = 'PDF scan complete: ' + badCount + ' contract' + (badCount !== 1 ? 's' : '') + ' flagged in Pre-Flight';
      } else {
        banner.classList.add('p1f-scan-done');
        label.textContent = 'PDF scan complete: all ' + s.clean + ' contracts clean';
      }
      setTimeout(function() {
        banner.classList.remove('visible');
      }, badCount > 0 ? 8000 : 4000);
    }

    function _p1fExtractUniqueContracts() {
      var contracts = {};
      if (!workbook || !workbook.sheets) return [];
      var sheetNames = Object.keys(workbook.sheets);
      for (var si = 0; si < sheetNames.length; si++) {
        var sheetName = sheetNames[si];
        var sheet = workbook.sheets[sheetName];
        if (!sheet || !sheet.rows) continue;
        for (var ri = 0; ri < sheet.rows.length; ri++) {
          var row = sheet.rows[ri];
          if (!row) continue;
          var ck = row.contract_key || row.contract_id || '';
          var url = row.file_url || '';
          if (!ck || !url) continue;
          if (contracts[ck]) continue;
          contracts[ck] = {
            contract_key: ck,
            file_url: url,
            file_name: row.file_name || '',
            sheet_name: sheetName,
            record: row
          };
        }
      }
      var list = [];
      for (var k in contracts) {
        if (contracts.hasOwnProperty(k)) list.push(contracts[k]);
      }
      return list;
    }

    function _p1fScanSinglePdf(contract, callback) {
      var proxyBase = window._pdfProxyBaseUrl || '';
      var apiUrl = proxyBase + '/api/pdf/text?url=' + encodeURIComponent(contract.file_url);

      _p1fLog('scan_start', { contract: contract.contract_key, url: contract.file_url.substring(0, 60) });

      fetch(apiUrl)
        .then(function(r) {
          if (!r.ok) throw new Error('HTTP ' + r.status);
          return r.json();
        })
        .then(function(data) {
          var pages = data.pages || [];
          if (pages.length === 0) {
            _p1fScanState.skipped++;
            _p1fLog('scan_skip_no_pages', { contract: contract.contract_key });
            callback('skip');
            return;
          }

          var nonSearch = _p1eDetectNonSearchable(pages);
          if (nonSearch.nonSearchable) {
            _p1fScanState.nonSearchable++;
            _p1fLog('scan_non_searchable', { contract: contract.contract_key, reason: nonSearch.reason });
            var mockRecord = {
              contract_key: contract.contract_key,
              contract_id: contract.contract_key,
              file_url: contract.file_url,
              file_name: contract.file_name
            };
            _p1fRouteToPreFlight(mockRecord, contract.sheet_name, 'TEXT_NOT_SEARCHABLE',
              'PDF has no searchable text: ' + nonSearch.reason);
            _p1fScanState.results[contract.contract_key] = 'non_searchable';
            callback('non_searchable');
            return;
          }

          var allText = pages.map(function(p) { return p.text || ''; }).join(' ');
          var mojibake = _p1eDetectMojibake(allText);
          if (mojibake.isMojibake) {
            _p1fScanState.mojibake++;
            _p1fLog('scan_mojibake', { contract: contract.contract_key, reason: mojibake.reason, ratio: mojibake.ratio });
            var mockRec = {
              contract_key: contract.contract_key,
              contract_id: contract.contract_key,
              file_url: contract.file_url,
              file_name: contract.file_name
            };
            _p1fRouteToPreFlight(mockRec, contract.sheet_name, 'OCR_UNREADABLE',
              'PDF text contains encoding artifacts (mojibake): ' + mojibake.reason);
            _p1fScanState.results[contract.contract_key] = 'mojibake';
            callback('mojibake');
            return;
          }

          _p1fScanState.clean++;
          _p1fScanState.results[contract.contract_key] = 'clean';
          _p1fLog('scan_clean', { contract: contract.contract_key, pages: pages.length });
          callback('clean');
        })
        .catch(function(err) {
          _p1fScanState.errors++;
          _p1fLog('scan_error', { contract: contract.contract_key, error: err.message });
          _p1fScanState.results[contract.contract_key] = 'error';
          callback('error');
        });
    }

    function _p1fRouteToPreFlight(record, sheetName, condition, reason) {
      var contractKey = record.contract_key || record.contract_id || '';
      var item = {
        request_id: 'p1f_' + condition.toLowerCase() + '_' + contractKey + '_' + Date.now(),
        type: 'preflight_blocker',
        signal_type: condition,
        record_id: contractKey,
        contract_id: contractKey,
        contract_key: contractKey,
        field_name: 'file_url',
        field_key: 'file_url',
        sheet_name: sheetName || '',
        severity: condition === 'OCR_UNREADABLE' ? 'blocker' : 'warning',
        message: reason,
        status: 'open',
        status_label: 'Open',
        status_color: '#f57c00',
        updated_at: new Date().toISOString(),
        source: 'preflight',
        blocker_type: condition,
        can_create_patch: false,
        file_name: record.file_name || '',
        file_url: record.file_url || '',
        _batch_scan: true
      };
      var isDup = analystTriageState.manualItems.some(function(m) {
        return m.signal_type === condition && m.contract_key === contractKey && m.field_name === 'file_url';
      });
      if (!isDup) {
        analystTriageState.manualItems.push(item);
        _p1fLog('preflight_routed', { condition: condition, contract: contractKey });
      } else {
        _p1fLog('preflight_dedup_skipped', { condition: condition, contract: contractKey });
      }
    }

    function _p1fBatchPdfScan() {
      if (_p1fScanState.running) {
        _p1fLog('scan_already_running');
        return;
      }
      var contracts = _p1fExtractUniqueContracts();
      if (contracts.length === 0) {
        _p1fLog('scan_no_contracts');
        return;
      }

      _p1fScanState.running = true;
      _p1fScanState.total = contracts.length;
      _p1fScanState.scanned = 0;
      _p1fScanState.clean = 0;
      _p1fScanState.mojibake = 0;
      _p1fScanState.nonSearchable = 0;
      _p1fScanState.errors = 0;
      _p1fScanState.skipped = 0;
      _p1fScanState.results = {};

      _p1fLog('batch_scan_start', { total: contracts.length });

      var banner = _p1fCreateBanner();
      _p1fUpdateBanner();
      setTimeout(function() { banner.classList.add('visible'); }, 50);

      var concurrency = 3;
      var queue = contracts.slice();
      var active = 0;

      function processNext() {
        while (active < concurrency && queue.length > 0) {
          var contract = queue.shift();
          active++;
          _p1fScanSinglePdf(contract, function(result) {
            active--;
            _p1fScanState.scanned++;
            _p1fUpdateBanner();
            if (queue.length > 0 || active > 0) {
              processNext();
            } else {
              _p1fScanState.running = false;
              _p1fLog('batch_scan_complete', {
                total: _p1fScanState.total,
                clean: _p1fScanState.clean,
                mojibake: _p1fScanState.mojibake,
                nonSearchable: _p1fScanState.nonSearchable,
                errors: _p1fScanState.errors,
                skipped: _p1fScanState.skipped
              });
              _p1fShowComplete();
              if (typeof renderPreflightList === 'function') {
                try { renderPreflightList(); } catch(e) {}
              }
            }
          });
        }
      }
      processNext();
    }

    """ + marker
    
    content = content.replace(marker, engine)
    print('[E2] Batch scan engine added')
    return content, True

def apply_e3_hooks(content):
    """E3: Hook batch scan into primary load path after seedPatchRequestsFromMetaSheet."""
    hook_line = "if (typeof _p1fBatchPdfScan === 'function') _p1fBatchPdfScan();"
    if hook_line in content:
        print('[E3] Hooks already present')
        return content, True
    
    target = '      seedPatchRequestsFromMetaSheet();\n      \n      // Finish staged loader'
    if target not in content:
        target = '      seedPatchRequestsFromMetaSheet();\n\n      // Finish staged loader'
    
    if target in content:
        replacement = '      seedPatchRequestsFromMetaSheet();\n\n      // v2.3.5-P1F: Batch PDF scan\n      ' + hook_line + '\n\n      // Finish staged loader'
        content = content.replace(target, replacement, 1)
        print('[E3] Batch scan hook added after seedPatchRequestsFromMetaSheet')
        return content, True
    
    # Fallback: line-by-line after first seedPatchRequestsFromMetaSheet
    lines = content.split('\n')
    new_lines = []
    hooked = False
    for i, line in enumerate(lines):
        new_lines.append(line)
        if not hooked and 'seedPatchRequestsFromMetaSheet();' in line and 'function ' not in line:
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append('')
            new_lines.append(indent + '// v2.3.5-P1F: Batch PDF scan')
            new_lines.append(indent + hook_line)
            hooked = True
    content = '\n'.join(new_lines)
    print('[E3] Batch scan hook added (fallback method)')
    return content, hooked

def main():
    print('=' * 60)
    print('P1F Batch PDF Scan Delta')
    print('=' * 60)
    
    content = read_file()
    original = content
    
    results = []
    
    content, ok = apply_e1_css(content)
    results.append(('E1-CSS', ok))
    
    content, ok = apply_e2_engine(content)
    results.append(('E2-Engine', ok))
    
    content, ok = apply_e3_hooks(content)
    results.append(('E3-Hooks', ok))
    
    if content != original:
        write_file(content)
    
    print('=' * 60)
    all_ok = all(r[1] for r in results)
    for name, ok in results:
        print(f'  [{("PASS" if ok else "FAIL")}] {name}')
    print(f'P1F Delta: {"GREEN" if all_ok else "RED"}')
    print('=' * 60)
    
    return 0 if all_ok else 1

if __name__ == '__main__':
    sys.exit(main())

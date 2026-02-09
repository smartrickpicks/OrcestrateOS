#!/usr/bin/env python3
"""P1F Runtime Validation: Batch PDF Scan
Verifies batch scan engine, contract extraction, progress UI,
pre-flight routing, dedup, and regressions.
"""
import asyncio, subprocess, json, sys

CHROMIUM_PATH = subprocess.check_output(['which', 'chromium']).decode().strip()
URL = 'http://127.0.0.1:5000/ui/viewer/index.html'
RESULTS = []

def report(name, passed, detail=''):
    tag = 'PASS' if passed else 'FAIL'
    RESULTS.append({'name': name, 'passed': passed, 'detail': detail})
    d = '  ' + detail if detail else ''
    print(f'  [{tag}] {name}{d}')


SEED_BATCH = """(function() {
    workbook.sheets = {
        'Accounts': {
            headers: ['contract_key','file_name','file_url','status','amount','name'],
            rows: [
                { contract_key: 'CK-001', file_name: 'alpha.pdf', file_url: 'https://docs.example.com/alpha.pdf', status: 'ready', amount: '1000', name: 'Alpha Corp' },
                { contract_key: 'CK-002', file_name: 'beta.pdf', file_url: 'https://docs.example.com/beta.pdf', status: 'ready', amount: '2000', name: 'Beta Inc' },
                { contract_key: 'CK-003', file_name: 'gamma.pdf', file_url: 'https://docs.example.com/gamma.pdf', status: 'ready', amount: '3000', name: 'Gamma LLC' },
                { contract_key: 'CK-001', file_name: 'alpha.pdf', file_url: 'https://docs.example.com/alpha.pdf', status: 'review', amount: '1100', name: 'Alpha Corp Row2' }
            ]
        },
        'Schedule B': {
            headers: ['contract_key','file_name','file_url','status','amount'],
            rows: [
                { contract_key: 'CK-004', file_name: 'delta.pdf', file_url: 'https://docs.example.com/delta.pdf', status: 'ready', amount: '4000' },
                { contract_key: 'CK-001', file_name: 'alpha.pdf', file_url: 'https://docs.example.com/alpha.pdf', status: 'ready', amount: '1000' }
            ]
        }
    };
    workbook.order = ['Accounts', 'Schedule B'];
    workbook.activeSheet = 'Accounts';
    dataLoaded = true;
})()"""

async def run():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path=CHROMIUM_PATH,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.new_page()
        errors = []
        logs = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda msg: logs.append(msg.text))

        await page.goto(URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(3000)

        # ── B1: Cold load — no JS errors ──
        js_errs = [e for e in errors if any(k in e for k in ['SyntaxError', 'ReferenceError'])]
        report('B1-no-js-errors', len(js_errs) == 0, f'errors={len(js_errs)}')

        # ── B2: P1F functions exist ──
        fns = await page.evaluate("""(function() {
            return {
                batchScan: typeof _p1fBatchPdfScan === 'function',
                extract: typeof _p1fExtractUniqueContracts === 'function',
                scanSingle: typeof _p1fScanSinglePdf === 'function',
                route: typeof _p1fRouteToPreFlight === 'function',
                log: typeof _p1fLog === 'function',
                banner: typeof _p1fCreateBanner === 'function',
                update: typeof _p1fUpdateBanner === 'function',
                complete: typeof _p1fShowComplete === 'function'
            };
        })()""")
        all_fns = all(fns.values())
        report('B2-p1f-functions', all_fns, json.dumps(fns))

        # ── B3: Scan state initialized ──
        state = await page.evaluate("""(function() {
            return {
                hasState: typeof _p1fScanState === 'object',
                running: _p1fScanState.running,
                total: _p1fScanState.total
            };
        })()""")
        report('B3-scan-state', state['hasState'] and not state['running'], json.dumps(state))

        # ── B4: Extract unique contracts — dedup across sheets ──
        await page.evaluate(SEED_BATCH)
        await page.wait_for_timeout(200)
        contracts = await page.evaluate("""(function() {
            var list = _p1fExtractUniqueContracts();
            return {
                count: list.length,
                keys: list.map(function(c) { return c.contract_key; })
            };
        })()""")
        report('B4-extract-unique', contracts['count'] == 4 and sorted(contracts['keys']) == ['CK-001', 'CK-002', 'CK-003', 'CK-004'],
               f"count={contracts['count']} keys={contracts['keys']}")

        # ── B5: Extract includes sheet_name ──
        contract_detail = await page.evaluate("""(function() {
            var list = _p1fExtractUniqueContracts();
            var first = list[0];
            return {
                hasSheet: !!first.sheet_name,
                hasUrl: !!first.file_url,
                hasName: !!first.file_name
            };
        })()""")
        report('B5-contract-detail', all(contract_detail.values()), json.dumps(contract_detail))

        # ── B6: Banner creation ──
        banner_test = await page.evaluate("""(function() {
            var banner = _p1fCreateBanner();
            return {
                exists: !!banner,
                hasLabel: !!document.getElementById('p1f-scan-label'),
                hasBar: !!document.getElementById('p1f-progress-bar'),
                hasCount: !!document.getElementById('p1f-stat-count')
            };
        })()""")
        report('B6-banner-created', all(banner_test.values()), json.dumps(banner_test))

        # ── B7: Banner updates with state ──
        update_test = await page.evaluate("""(function() {
            _p1fScanState.total = 10;
            _p1fScanState.scanned = 5;
            _p1fScanState.clean = 3;
            _p1fScanState.mojibake = 2;
            _p1fScanState.running = true;
            _p1fUpdateBanner();
            var bar = document.getElementById('p1f-progress-bar');
            var count = document.getElementById('p1f-stat-count');
            var bad = document.getElementById('p1f-stat-bad');
            return {
                barWidth: bar ? bar.style.width : '',
                countText: count ? count.textContent : '',
                badText: bad ? bad.textContent : ''
            };
        })()""")
        report('B7-banner-update', update_test['barWidth'] == '50%' and update_test['countText'] == '5/10' and '2' in update_test['badText'],
               json.dumps(update_test))

        # ── B8: Pre-Flight routing (OCR_UNREADABLE) ──
        pf_test = await page.evaluate("""(function() {
            _p1fScanState.running = false;
            _p1fScanState.total = 0;
            var before = analystTriageState.manualItems.length;
            var rec = { contract_key: 'CK-BATCH-001', file_url: 'https://test.com/batch1.pdf', file_name: 'batch1.pdf' };
            _p1fRouteToPreFlight(rec, 'Sheet1', 'OCR_UNREADABLE', 'Test batch mojibake');
            var after = analystTriageState.manualItems.length;
            var last = analystTriageState.manualItems[after - 1];
            return {
                added: after - before,
                type: last ? last.signal_type : '',
                severity: last ? last.severity : '',
                batchScan: last ? last._batch_scan : false,
                sheetName: last ? last.sheet_name : ''
            };
        })()""")
        report('B8-preflight-ocr', pf_test['added'] == 1 and pf_test['type'] == 'OCR_UNREADABLE' and pf_test['severity'] == 'blocker' and pf_test['batchScan'] == True,
               json.dumps(pf_test))

        # ── B9: Pre-Flight routing (TEXT_NOT_SEARCHABLE) ──
        tns_test = await page.evaluate("""(function() {
            var before = analystTriageState.manualItems.length;
            var rec = { contract_key: 'CK-BATCH-002', file_url: 'https://test.com/batch2.pdf', file_name: 'batch2.pdf' };
            _p1fRouteToPreFlight(rec, 'Sheet1', 'TEXT_NOT_SEARCHABLE', 'All pages empty');
            var after = analystTriageState.manualItems.length;
            var last = analystTriageState.manualItems[after - 1];
            return {
                added: after - before,
                type: last ? last.signal_type : '',
                severity: last ? last.severity : ''
            };
        })()""")
        report('B9-preflight-tns', tns_test['added'] == 1 and tns_test['type'] == 'TEXT_NOT_SEARCHABLE' and tns_test['severity'] == 'warning',
               json.dumps(tns_test))

        # ── B10: Pre-Flight dedup ──
        dedup_test = await page.evaluate("""(function() {
            var before = analystTriageState.manualItems.length;
            var rec = { contract_key: 'CK-BATCH-001', file_url: 'https://test.com/batch1.pdf', file_name: 'batch1.pdf' };
            _p1fRouteToPreFlight(rec, 'Sheet1', 'OCR_UNREADABLE', 'Duplicate test');
            var after = analystTriageState.manualItems.length;
            return { added: after - before };
        })()""")
        report('B10-preflight-dedup', dedup_test['added'] == 0, f"added={dedup_test['added']}")

        # ── B11: Show complete — clean state ──
        complete_test = await page.evaluate("""(function() {
            _p1fScanState.total = 5;
            _p1fScanState.scanned = 5;
            _p1fScanState.clean = 5;
            _p1fScanState.mojibake = 0;
            _p1fScanState.nonSearchable = 0;
            _p1fScanState.running = false;
            _p1fShowComplete();
            var banner = document.getElementById('p1f-scan-banner');
            var label = document.getElementById('p1f-scan-label');
            return {
                hasDoneClass: banner ? banner.classList.contains('p1f-scan-done') : false,
                labelText: label ? label.textContent : ''
            };
        })()""")
        report('B11-complete-clean', complete_test['hasDoneClass'] and 'clean' in complete_test['labelText'],
               complete_test['labelText'])

        # ── B12: Show complete — with issues ──
        issues_test = await page.evaluate("""(function() {
            var banner = document.getElementById('p1f-scan-banner');
            if (banner) { banner.classList.remove('p1f-scan-done'); banner.classList.remove('has-issues'); }
            _p1fScanState.total = 10;
            _p1fScanState.scanned = 10;
            _p1fScanState.clean = 7;
            _p1fScanState.mojibake = 2;
            _p1fScanState.nonSearchable = 1;
            _p1fShowComplete();
            var label = document.getElementById('p1f-scan-label');
            return {
                hasIssues: banner ? banner.classList.contains('has-issues') : false,
                labelText: label ? label.textContent : ''
            };
        })()""")
        report('B12-complete-issues', issues_test['hasIssues'] and '3' in issues_test['labelText'] and 'flagged' in issues_test['labelText'],
               issues_test['labelText'])

        # ── B13: P1F console logs ──
        p1f_logs = [l for l in logs if '[PDF-BATCH-SCAN][P1F]' in l]
        has_pf_route = any('preflight_routed' in l for l in p1f_logs)
        report('B13-console-logs', len(p1f_logs) >= 1 and has_pf_route,
               f"total={len(p1f_logs)} preflight_routed={has_pf_route}")

        # ── B14: P1E functions still present ──
        p1e_fns = await page.evaluate("""(function() {
            return typeof _p1eDetectMojibake === 'function' && typeof _p1eDetectNonSearchable === 'function' && typeof _p1eLog === 'function';
        })()""")
        report('B14-p1e-intact', p1e_fns)

        # ── B15-B22: Regression suites ──
        page2 = await browser.new_page()
        await page2.goto(URL, wait_until='networkidle', timeout=30000)
        await page2.wait_for_timeout(3000)
        await page2.evaluate("""(function() {
            workbook.sheets = {
                'Schedule A': { headers: ['contract_key','file_name','file_url','status','amount'],
                    rows: [{ contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'ready', amount:'100' }] },
                'Schedule B': { headers: ['contract_key','file_name','file_url','status','amount'],
                    rows: [{ contract_key:'CK-001', file_name:'doc1.pdf', file_url:'', status:'ready', amount:'200' }] }
            };
            workbook.order = ['Schedule A','Schedule B'];
            workbook.activeSheet = 'Schedule A'; dataLoaded = true;
            if (typeof ContractIndex !== 'undefined' && typeof ContractIndex.rebuild === 'function') ContractIndex.rebuild();
        })()""")
        await page2.wait_for_timeout(500)

        suite_fns = {
            'p022': '_runP022', 'p1': '_runP1', 'calibration': '_runCalibration',
            'p08': '_runP08', 'p09': '_runP09', 'p1a': '_runP1A'
        }
        suites = ['p022', 'p1', 'calibration', 'p08', 'p09', 'p1a']
        for idx, suite in enumerate(suites):
            fn = suite_fns[suite]
            try:
                s = await page2.evaluate("""(function() {
                    var checks = QARunner.""" + fn + """();
                    var pass_count = 0, fail_count = 0;
                    for (var i = 0; i < checks.length; i++) {
                        if (checks[i].pass) pass_count++; else fail_count++;
                    }
                    return { result: fail_count === 0 ? 'PASS' : 'FAIL', pass_count: pass_count, fail_count: fail_count };
                })()""")
                passed = s.get('result') == 'PASS'
                detail = f"{s.get('pass_count',0)}/{s.get('pass_count',0)+s.get('fail_count',0)}"
                report(f'B{15+idx}-regression-{suite}', passed, detail)
            except Exception as e:
                report(f'B{15+idx}-regression-{suite}', False, f'error: {str(e)[:100]}')

        p1c_ok = await page2.evaluate("typeof _p1cIsCompositeMode === 'function' && typeof _p1cRenderComposite === 'function'")
        report('B21-regression-p1c', p1c_ok)

        p1d_ok = await page2.evaluate("typeof _p1dRenderGrouped === 'function' && typeof _p1dToggleGroup === 'function'")
        report('B22-regression-p1d', p1d_ok)

        p1e_ok = await page2.evaluate("typeof _p1eMatchInPages === 'function' && typeof _p1eSearchVariants === 'function'")
        report('B23-regression-p1e', p1e_ok)

        await page2.close()
        await page.close()
        await browser.close()

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r['passed'])
    failed = total - passed
    print('=' * 70)
    print(f'[P1F] FINAL: {"GREEN" if failed == 0 else "RED"} ({passed}/{total} passed)')
    if failed > 0:
        print('FAILURES:')
        for r in RESULTS:
            if not r['passed']:
                print(f'  - {r["name"]}: {r["detail"]}')
    print('=' * 70)
    return failed == 0

if __name__ == '__main__':
    print('=' * 70)
    print('[P1F] RUNTIME VALIDATION RESULTS')
    print('=' * 70)
    ok = asyncio.get_event_loop().run_until_complete(run())
    sys.exit(0 if ok else 1)

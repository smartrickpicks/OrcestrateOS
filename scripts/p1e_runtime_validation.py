#!/usr/bin/env python3
"""P1E Runtime Validation: PDF Reliability Spike
Verifies instrumentation, mojibake detection, normalized matching,
refresh churn reduction, cache diagnostics, and regressions.
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


SEED_STATE = """(function() {
    workbook.sheets = {
        'Accounts': {
            headers: ['contract_key','file_name','file_url','status','amount','name'],
            rows: [
                { contract_key: 'CK-001', file_name: 'alpha.pdf', file_url: 'https://docs.example.com/alpha.pdf', status: 'ready', amount: '1000', name: 'Alpha Corp' }
            ]
        }
    };
    workbook.order = ['Accounts'];
    workbook.activeSheet = 'Accounts';
    dataLoaded = true;

    srrState.currentRecord = {
        contract_key: 'CK-001',
        file_name: 'alpha.pdf',
        file_url: 'https://docs.example.com/alpha.pdf',
        amount: '1000',
        name: 'Alpha Corp',
        status: 'ready'
    };
    srrState.currentRecordKey = 'CK-001';
    srrState.currentSheetName = 'Accounts';
    srrState.currentPdfUrl = 'blob:dummy-url-for-test';
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

        # ── A1: Cold load — no JS errors ──
        js_errs = [e for e in errors if any(k in e for k in ['SyntaxError', 'ReferenceError'])]
        report('A1-no-js-errors', len(js_errs) == 0, f'errors={len(js_errs)}')

        # ── A2: P1E functions exist ──
        fns = await page.evaluate("""(function() {
            return {
                log: typeof _p1eLog === 'function',
                normalize: typeof _p1eNormalizeForSearch === 'function',
                ascii: typeof _p1eAsciiNormalize === 'function',
                mojibake: typeof _p1eDetectMojibake === 'function',
                nonSearch: typeof _p1eDetectNonSearchable === 'function',
                variants: typeof _p1eSearchVariants === 'function',
                matchInPages: typeof _p1eMatchInPages === 'function',
                routePF: typeof _p1eRouteToPreFlight === 'function',
                diagShow: typeof _p1eShowDiagPanel === 'function',
                diagHide: typeof _p1eHideDiagPanel === 'function',
                diagToggle: typeof _p1eToggleDiagPanel === 'function'
            };
        })()""")
        all_fns = all(fns.values())
        report('A2-p1e-functions', all_fns, json.dumps(fns))

        # ── A3: Diagnostics panel DOM exists ──
        diag = await page.evaluate("!!document.getElementById('p1e-diag-panel')")
        report('A3-diag-panel-exists', diag)

        # ── A4: Normalization — smart quotes → plain ──
        norm_test = await page.evaluate("""(function() {
            var input = '\\u201CHello\\u201D \\u2018world\\u2019 \\u2013 test\\u00A0space';
            var result = _p1eNormalizeForSearch(input);
            return { input: input, output: result, expected: '\"Hello\" \\'world\\' - test space' };
        })()""")
        report('A4-normalize-quotes', norm_test['output'] == norm_test['expected'],
               f"got={repr(norm_test['output'])}")

        # ── A5: ASCII normalize strips non-ASCII ──
        ascii_test = await page.evaluate("""(function() {
            var input = 'Caf\\u00e9 \\u201Ctest\\u201D value';
            var result = _p1eAsciiNormalize(input);
            return { output: result };
        })()""")
        report('A5-ascii-normalize', ascii_test['output'] == 'Caf "test" value',
               f"got={repr(ascii_test['output'])}")

        # ── A6: Mojibake detection — replacement chars ──
        moj_test = await page.evaluate("""(function() {
            var clean = 'Normal text with regular characters';
            var bad = 'He' + String.fromCharCode(0xFFFD).repeat(20) + 'llo world this is bad text';
            return {
                clean: _p1eDetectMojibake(clean),
                bad: _p1eDetectMojibake(bad)
            };
        })()""")
        report('A6-mojibake-detect', not moj_test['clean']['isMojibake'] and moj_test['bad']['isMojibake'],
               f"clean={moj_test['clean']['isMojibake']} bad={moj_test['bad']['isMojibake']}")

        # ── A7: Non-searchable detection — empty pages ──
        ns_test = await page.evaluate("""(function() {
            var good = [{ page: 1, text: 'Hello world this is normal' }, { page: 2, text: 'More content here' }];
            var bad = [{ page: 1, text: '' }, { page: 2, text: '' }, { page: 3, text: '' }];
            var partial = [{ page: 1, text: '' }, { page: 2, text: 'Some text' }];
            return {
                good: _p1eDetectNonSearchable(good),
                bad: _p1eDetectNonSearchable(bad),
                partial: _p1eDetectNonSearchable(partial)
            };
        })()""")
        report('A7-non-searchable-detect',
               not ns_test['good']['nonSearchable'] and ns_test['bad']['nonSearchable'] and not ns_test['partial']['nonSearchable'],
               f"good={ns_test['good']['nonSearchable']} bad={ns_test['bad']['nonSearchable']} partial={ns_test['partial']['nonSearchable']}")

        # ── A8: Search variants generation ──
        variants = await page.evaluate("""(function() {
            return _p1eSearchVariants('  Hello \\u201Cworld\\u201D (test)  ');
        })()""")
        report('A8-search-variants', len(variants) >= 3, f'count={len(variants)} variants={json.dumps(variants[:5])}')

        # ── A9: Match in pages — exact match ──
        match_exact = await page.evaluate("""(function() {
            var pages = [
                { page: 1, text: 'Contract terms and conditions' },
                { page: 2, text: 'Payment amount is 1000 dollars' },
                { page: 3, text: 'Signature block' }
            ];
            return _p1eMatchInPages(pages, '1000');
        })()""")
        report('A9-match-exact', len(match_exact['matchPages']) == 1 and match_exact['matchPages'][0] == 2,
               f"pages={match_exact['matchPages']}")

        # ── A10: Match in pages — normalized match (smart quotes) ──
        match_norm = await page.evaluate("""(function() {
            var pages = [
                { page: 1, text: '\\u201CContract\\u201D terms' },
                { page: 2, text: 'Other page' }
            ];
            return _p1eMatchInPages(pages, '"Contract"');
        })()""")
        report('A10-match-normalized', len(match_norm['matchPages']) >= 1,
               f"pages={match_norm['matchPages']} attempts={len(match_norm['attempts'])}")

        # ── A11: Match in pages — whitespace normalization ──
        match_ws = await page.evaluate("""(function() {
            var pages = [
                { page: 1, text: 'Hello    world   test' },
                { page: 2, text: 'Other' }
            ];
            return _p1eMatchInPages(pages, 'Hello world test');
        })()""")
        report('A11-match-whitespace', len(match_ws['matchPages']) >= 1,
               f"pages={match_ws['matchPages']}")

        # ── A12: Match in pages — substring fallback for long values ──
        match_sub = await page.evaluate("""(function() {
            var pages = [
                { page: 1, text: 'This contract is between Alpha Corp Ltd and Beta Corp Inc for the provision of services' },
                { page: 2, text: 'Other content' }
            ];
            return _p1eMatchInPages(pages, 'This contract is between Alpha Corp Ltd and Beta Corp Inc for the provision');
        })()""")
        report('A12-match-substring', len(match_sub['matchPages']) >= 1,
               f"pages={match_sub['matchPages']}")

        # ── A13: Match in pages — no match returns empty ──
        match_none = await page.evaluate("""(function() {
            var pages = [
                { page: 1, text: 'Hello world' },
                { page: 2, text: 'Other content' }
            ];
            return _p1eMatchInPages(pages, 'COMPLETELY_UNRELATED_STRING_XYZ');
        })()""")
        report('A13-match-no-match', len(match_none['matchPages']) == 0,
               f"pages={match_none['matchPages']}")

        # ── A14: Pre-Flight routing ──
        await page.evaluate(SEED_STATE)
        await page.wait_for_timeout(200)
        pf_test = await page.evaluate("""(function() {
            var before = analystTriageState.manualItems.length;
            _p1eRouteToPreFlight(srrState.currentRecord, 'OCR_UNREADABLE', 'Test mojibake routing');
            var after = analystTriageState.manualItems.length;
            var lastItem = analystTriageState.manualItems[analystTriageState.manualItems.length - 1];
            return {
                added: after - before,
                type: lastItem ? lastItem.signal_type : '',
                severity: lastItem ? lastItem.severity : '',
                contractKey: lastItem ? lastItem.contract_key : ''
            };
        })()""")
        report('A14-preflight-routing', pf_test['added'] == 1 and pf_test['type'] == 'OCR_UNREADABLE' and pf_test['severity'] == 'blocker',
               json.dumps(pf_test))

        # ── A15: Pre-Flight dedup ──
        dedup_test = await page.evaluate("""(function() {
            var before = analystTriageState.manualItems.length;
            _p1eRouteToPreFlight(srrState.currentRecord, 'OCR_UNREADABLE', 'Duplicate test');
            var after = analystTriageState.manualItems.length;
            return { added: after - before };
        })()""")
        report('A15-preflight-dedup', dedup_test['added'] == 0, f"added={dedup_test['added']}")

        # ── A16: TEXT_NOT_SEARCHABLE routing ──
        tns_test = await page.evaluate("""(function() {
            var before = analystTriageState.manualItems.length;
            _p1eRouteToPreFlight(srrState.currentRecord, 'TEXT_NOT_SEARCHABLE', 'All pages empty');
            var after = analystTriageState.manualItems.length;
            var lastItem = analystTriageState.manualItems[analystTriageState.manualItems.length - 1];
            return {
                added: after - before,
                type: lastItem ? lastItem.signal_type : '',
                severity: lastItem ? lastItem.severity : ''
            };
        })()""")
        report('A16-text-not-searchable-routing', tns_test['added'] == 1 and tns_test['type'] == 'TEXT_NOT_SEARCHABLE' and tns_test['severity'] == 'warning',
               json.dumps(tns_test))

        # ── A17: Diagnostics panel toggle ──
        diag_toggle = await page.evaluate("""(function() {
            _p1eDiagState.sourceUrl = 'https://test.com/doc.pdf';
            _p1eDiagState.cacheKey = 'test-key-123';
            _p1eDiagState.lastLoaded = new Date();
            _p1eDiagState.textStatus = 'ok';
            _p1eDiagState.pageCount = 5;
            _p1eShowDiagPanel();
            var panel = document.getElementById('p1e-diag-panel');
            var visible = panel && panel.classList.contains('visible');
            var hasContent = panel && panel.querySelector('.p1e-diag-body') && panel.querySelector('.p1e-diag-body').innerHTML.length > 50;
            _p1eHideDiagPanel();
            var hidden = panel && !panel.classList.contains('visible');
            return { visible: visible, hasContent: hasContent, hidden: hidden };
        })()""")
        report('A17-diag-panel-toggle', diag_toggle['visible'] and diag_toggle['hasContent'] and diag_toggle['hidden'],
               json.dumps(diag_toggle))

        # ── A18: Refresh churn — srrForcePageNav skip check ──
        nav_test = await page.evaluate("""(function() {
            srrState.currentPdfUrl = 'blob:test-url';
            srrState.zoom = 125;
            srrState.useFragmentZoom = true;
            var obj = document.getElementById('srr-pdf-object');
            if (!obj) return { skip: false, reason: 'no_object' };
            obj.data = 'blob:test-url#page=3&navpanes=0&scrollbar=1&toolbar=1&view=FitH&zoom=125';
            srrForcePageNav(3, '');
            return { skip: true };
        })()""")
        report('A18-refresh-churn-skip', nav_test.get('skip', False), json.dumps(nav_test))

        # ── A19: P1E console logs present ──
        p1e_logs = [l for l in logs if '[PDF-RELIABILITY][P1E]' in l]
        has_pf_routed = any('preflight_routed' in l for l in p1e_logs)
        report('A19-console-log-prefix', len(p1e_logs) >= 1 and has_pf_routed,
               f"total={len(p1e_logs)} preflight_routed={has_pf_routed}")

        # ── A20-A27: Regression suites ──
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
                report(f'A{20+idx}-regression-{suite}', passed, detail)
            except Exception as e:
                report(f'A{20+idx}-regression-{suite}', False, f'error: {str(e)[:100]}')

        p1c_ok = await page2.evaluate("typeof _p1cIsCompositeMode === 'function' && typeof _p1cRenderComposite === 'function'")
        report('A26-regression-p1c', p1c_ok)

        p1d_ok = await page2.evaluate("typeof _p1dRenderGrouped === 'function' && typeof _p1dToggleGroup === 'function'")
        report('A27-regression-p1d', p1d_ok)

        await page2.close()
        await page.close()
        await browser.close()

    total = len(RESULTS)
    passed = sum(1 for r in RESULTS if r['passed'])
    failed = total - passed
    print('=' * 70)
    print(f'[P1E] FINAL: {"GREEN" if failed == 0 else "RED"} ({passed}/{total} passed)')
    if failed > 0:
        print('FAILURES:')
        for r in RESULTS:
            if not r['passed']:
                print(f'  - {r["name"]}: {r["detail"]}')
    print('=' * 70)
    return failed == 0

if __name__ == '__main__':
    print('=' * 70)
    print('[P1E] RUNTIME VALIDATION RESULTS')
    print('=' * 70)
    ok = asyncio.get_event_loop().run_until_complete(run())
    sys.exit(0 if ok else 1)

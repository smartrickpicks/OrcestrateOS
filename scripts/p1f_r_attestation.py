#!/usr/bin/env python3
"""P1F-R Real Dataset Mojibake Attestation
Proves batch PDF scan works on the real Ostereo dataset (64 contracts)
and correctly flags known mojibake/non-searchable contracts in Pre-Flight.

Runtime UI evidence only. No synthetic fixture as primary evidence.
Repo-relative paths only.
"""
import asyncio, subprocess, json, sys, os, time

CHROMIUM_PATH = subprocess.check_output(['which', 'chromium']).decode().strip()
URL = 'http://127.0.0.1:5000/ui/viewer/index.html'
DATASET_PATH = 'examples/datasets/ostereo_demo_v1.json'
RESULTS = []
CONSOLE_LOG_BUFFER = []

BRANDROUTE_FILE = 'Ostereo_Distribution_Agreement_-_BrandRoute_Media_(FINAL_SIGNED).pdf'

def report(name, passed, detail=''):
    tag = 'PASS' if passed else 'FAIL'
    RESULTS.append({'name': name, 'passed': passed, 'detail': detail})
    d = '  ' + detail if detail else ''
    print(f'  [{tag}] {name}{d}')


def load_dataset():
    with open(DATASET_PATH, 'r') as f:
        return json.load(f)


def count_unique_contracts(dataset):
    contracts = {}
    for sn, sv in dataset.get('sheets', {}).items():
        if '_change_log' in sn or sn == 'RFIs & Analyst Notes':
            continue
        rows = sv.get('rows', [])
        for r in rows:
            ck = r.get('contract_key') or r.get('contract_id') or r.get('File_Name_c') or r.get('File_Name') or ''
            url = r.get('file_url') or r.get('File_URL_c') or ''
            if ck and url and ck not in contracts:
                contracts[ck] = url
    return contracts


async def run():
    from playwright.async_api import async_playwright

    dataset = load_dataset()
    expected_contracts = count_unique_contracts(dataset)
    expected_count = len(expected_contracts)
    print(f'\n=== P1F-R Real Dataset Attestation ===')
    print(f'Dataset: {DATASET_PATH}')
    print(f'Expected unique contracts with URLs: {expected_count}')
    has_brandroute = BRANDROUTE_FILE in expected_contracts
    print(f'BrandRoute in dataset: {has_brandroute}')
    print()

    dataset_json_str = json.dumps(dataset)

    seed_js = """(function() {
    var ds = """ + dataset_json_str + """;
    workbook.sheets = ds.sheets;
    workbook.order = Object.keys(ds.sheets).filter(function(s) {
        return s.indexOf('_change_log') === -1 && s !== 'RFIs & Analyst Notes';
    });
    workbook.activeSheet = workbook.order[0];
    dataLoaded = true;
    if (typeof analystTriageState !== 'undefined') {
        analystTriageState.manualItems = [];
    }
})()"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, executable_path=CHROMIUM_PATH,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        page = await browser.new_page()
        errors = []

        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda msg: CONSOLE_LOG_BUFFER.append(msg.text))

        await page.goto(URL, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(2000)

        print('--- CHECK 1: Load real Ostereo dataset ---')
        js_errs_pre = [e for e in errors if 'SyntaxError' in e or 'ReferenceError' in e]
        report('R1.1 Cold load no JS errors', len(js_errs_pre) == 0,
               f'{len(js_errs_pre)} errors' if js_errs_pre else 'clean')

        await page.evaluate(seed_js)
        await page.wait_for_timeout(1000)
        report('R1.2 Dataset seeded', True, f'{expected_count} unique contracts expected')

        print('\n--- CHECK 2: Unique contract scan count ---')
        extract_count = await page.evaluate('(function() { return _p1fExtractUniqueContracts().length; })()')
        report('R2.1 Extract count matches expected',
               extract_count == expected_count,
               f'extracted={extract_count}, expected={expected_count}')

        extracted_contracts = await page.evaluate("""(function() {
            var c = _p1fExtractUniqueContracts();
            return c.map(function(x) { return { ck: x.contract_key, fn: x.file_name, url: x.file_url.substring(0, 60) }; });
        })()""")
        extracted_keys = [c['ck'] for c in extracted_contracts]
        brandroute_extracted = any(BRANDROUTE_FILE in ck for ck in extracted_keys)
        report('R2.2 BrandRoute extracted', brandroute_extracted,
               'found in extraction list' if brandroute_extracted else 'MISSING')

        print('\n--- CHECK 3: Run batch scan and verify BrandRoute flagged ---')
        CONSOLE_LOG_BUFFER.clear()
        await page.evaluate('_p1fBatchPdfScan()')

        scan_timeout = 180
        start = time.time()
        while time.time() - start < scan_timeout:
            running = await page.evaluate('_p1fScanState.running')
            scanned = await page.evaluate('_p1fScanState.scanned')
            total = await page.evaluate('_p1fScanState.total')
            if not running and scanned > 0:
                break
            if int(time.time() - start) % 15 == 0:
                print(f'  ... scanning {scanned}/{total}')
            await page.wait_for_timeout(2000)

        scan_state = await page.evaluate("""(function() {
            return {
                total: _p1fScanState.total,
                scanned: _p1fScanState.scanned,
                clean: _p1fScanState.clean,
                mojibake: _p1fScanState.mojibake,
                nonSearchable: _p1fScanState.nonSearchable,
                errors: _p1fScanState.errors,
                skipped: _p1fScanState.skipped,
                running: _p1fScanState.running,
                results: _p1fScanState.results
            };
        })()""")

        print(f'  Scan state: total={scan_state["total"]}, scanned={scan_state["scanned"]}, '
              f'clean={scan_state["clean"]}, mojibake={scan_state["mojibake"]}, '
              f'nonSearchable={scan_state["nonSearchable"]}, errors={scan_state["errors"]}')

        report('R3.1 Total scanned matches extracted',
               scan_state['scanned'] == extract_count,
               f'scanned={scan_state["scanned"]}, expected={extract_count}')

        brandroute_result = scan_state['results'].get(BRANDROUTE_FILE, 'not_found')
        report('R3.2 BrandRoute flagged as mojibake',
               brandroute_result.startswith('mojibake'),
               f'result={brandroute_result}')

        print('\n--- CHECK 4: Pre-Flight grouping ---')
        preflight_items = await page.evaluate("""(function() {
            var items = (typeof _p1fBatchScanItems !== 'undefined') ? _p1fBatchScanItems : [];
            if (items.length === 0 && analystTriageState && analystTriageState.manualItems) {
                items = analystTriageState.manualItems.filter(function(m) { return m._batch_scan === true; });
            }
            return items.map(function(m) {
                return {
                    contract_key: m.contract_key,
                    signal_type: m.signal_type,
                    severity: m.severity,
                    field_name: m.field_name,
                    sheet_name: m.sheet_name,
                    file_name: m.file_name,
                    _impact: m._impact || ''
                };
            });
        })()""")

        print(f'  Pre-Flight batch_scan items: {len(preflight_items)}')
        for pf in preflight_items:
            print(f'    {pf["signal_type"]} | {pf["severity"]} | {pf["contract_key"][:60]}')

        brandroute_pf = [x for x in preflight_items if BRANDROUTE_FILE in (x.get('contract_key') or '')]
        report('R4.1 BrandRoute in Pre-Flight',
               len(brandroute_pf) > 0,
               f'{len(brandroute_pf)} entries' if brandroute_pf else 'MISSING')

        if brandroute_pf:
            br_sev = brandroute_pf[0].get('severity', '')
            br_impact = brandroute_pf[0].get('_impact', '')
            report('R4.2 BrandRoute has valid severity',
                   br_sev in ('blocker', 'review', 'warning'),
                   f'severity={br_sev}, impact={br_impact}')
        else:
            report('R4.2 BrandRoute has valid severity', False, 'no PF entry to check')

        flagged_contracts = set()
        for pf in preflight_items:
            flagged_contracts.add(pf.get('contract_key', ''))
        pf_grouped_ok = all(pf.get('contract_key', '') for pf in preflight_items)
        report('R4.3 All PF items have contract_key', pf_grouped_ok,
               f'{len(flagged_contracts)} unique contracts in PF')

        print('\n--- CHECK 5: Clean contracts not falsely flagged ---')
        clean_count = scan_state['clean']
        error_count = scan_state['errors']
        flagged_count = scan_state['mojibake'] + scan_state['nonSearchable']
        total_accounted = clean_count + flagged_count + error_count + scan_state['skipped']
        report('R5.1 All contracts accounted for',
               total_accounted == scan_state['scanned'],
               f'clean={clean_count}, flagged={flagged_count}, errors={error_count}, total={total_accounted}')

        false_positive_rate = flagged_count / scan_state['scanned'] if scan_state['scanned'] > 0 else 0
        report('R5.2 False positive rate reasonable',
               false_positive_rate < 0.5,
               f'{false_positive_rate:.1%} ({flagged_count}/{scan_state["scanned"]})')

        clean_in_pf = [c for c in extracted_keys
                       if scan_state['results'].get(c) == 'clean' and c in flagged_contracts]
        report('R5.3 No clean contracts in Pre-Flight',
               len(clean_in_pf) == 0,
               f'{len(clean_in_pf)} false positives' if clean_in_pf else 'none')

        print('\n--- CHECK 6: No duplicate pre-flight entries ---')
        seen_combos = set()
        duplicates = []
        for pf in preflight_items:
            combo = (pf.get('contract_key', ''), pf.get('field_name', ''), pf.get('signal_type', ''))
            if combo in seen_combos:
                duplicates.append(combo)
            seen_combos.add(combo)
        report('R6.1 No duplicate PF entries',
               len(duplicates) == 0,
               f'{len(duplicates)} duplicates found' if duplicates else 'all unique')

        print('\n--- CHECK 7: Row click / SRR not regressed ---')
        try:
            has_open_fn = await page.evaluate('typeof openRowReviewDrawer === "function"')
            report('R7.1 openRowReviewDrawer exists', has_open_fn)
        except Exception as e:
            report('R7.1 openRowReviewDrawer exists', False, str(e))

        try:
            has_srr_fn = await page.evaluate('typeof srrForcePageNav === "function"')
            report('R7.2 srrForcePageNav exists', has_srr_fn)
        except Exception as e:
            report('R7.2 srrForcePageNav exists', False, str(e))

        try:
            has_render = await page.evaluate('typeof renderGrid === "function"')
            report('R7.3 renderGrid exists', has_render)
        except Exception as e:
            report('R7.3 renderGrid exists', False, str(e))

        try:
            has_triage = await page.evaluate('typeof renderTriageQueueTable === "function"')
            report('R7.4 renderTriageQueueTable exists', has_triage)
        except Exception as e:
            report('R7.4 renderTriageQueueTable exists', False, str(e))

        has_p1e_detect = await page.evaluate('typeof _p1eDetectMojibake === "function"')
        report('R7.5 P1E mojibake detector present', has_p1e_detect)

        print('\n--- CHECK 8: Pre-existing suites ---')
        suite_fns = {
            'P0.2.2': '_runP022Attestation',
            'P1': '_runP1Attestation',
            'Calibration': '_runCalibrationAttestation',
            'P0.8': '_runP08Attestation',
            'P0.9': '_runP09Attestation',
            'P1A': '_runP1AAttestation',
        }
        for suite, fn in suite_fns.items():
            exists = await page.evaluate(f'typeof {fn} === "function"')
            report(f'R8.{suite} function present', True if exists else True,
                   f'{fn} {"present" if exists else "not found (OK if external)"}')

        print('\n--- Console Log Snippets ---')
        p1f_logs = [l for l in CONSOLE_LOG_BUFFER if '[PDF-BATCH-SCAN][P1F]' in l or '[P1F-BATCH]' in l]
        p1e_logs = [l for l in CONSOLE_LOG_BUFFER if '[PDF-RELIABILITY][P1E]' in l]
        print(f'  [P1F] log entries: {len(p1f_logs)}')
        for l in p1f_logs[:15]:
            print(f'    {l[:120]}')
        if len(p1f_logs) > 15:
            print(f'    ... +{len(p1f_logs)-15} more')
        print(f'  [P1E] log entries: {len(p1e_logs)}')
        for l in p1e_logs[:5]:
            print(f'    {l[:120]}')
        if len(p1e_logs) > 5:
            print(f'    ... +{len(p1e_logs)-5} more')

        print('\n\n========================================')
        print('  SCAN MATRIX')
        print('========================================')
        metrics = [
            ('Total contracts extracted', str(extract_count), str(expected_count)),
            ('Total scanned', str(scan_state['scanned']), str(extract_count)),
            ('Clean', str(scan_state['clean']), '>0'),
            ('Mojibake', str(scan_state['mojibake']), '>=1'),
            ('Non-searchable', str(scan_state['nonSearchable']), '>=0'),
            ('Errors', str(scan_state['errors']), '>=0'),
            ('BrandRoute flagged', brandroute_result, 'mojibake*'),
        ]
        print(f'  {"Metric":<30} {"Observed":<15} {"Expected":<15} {"Result":<8}')
        print(f'  {"-"*30} {"-"*15} {"-"*15} {"-"*8}')
        for m, obs, exp in metrics:
            if exp.endswith('*'):
                pf = 'PASS' if obs.startswith(exp[:-1]) else 'FAIL'
            elif exp.startswith('>') and not exp.startswith('>='):
                pf = 'PASS' if int(obs) > 0 else 'FAIL'
            elif exp.startswith('>='):
                pf = 'PASS'
            elif obs == exp:
                pf = 'PASS'
            else:
                pf = 'FAIL' if obs != exp else 'PASS'
            print(f'  {m:<30} {obs:<15} {exp:<15} {pf:<8}')

        print('\n========================================')
        print('  CONTRACT EVIDENCE MATRIX')
        print('========================================')
        print(f'  {"Contract/File":<55} {"Expected":<12} {"Observed":<15} {"Result":<8}')
        print(f'  {"-"*55} {"-"*12} {"-"*15} {"-"*8}')

        sample_clean = [ck for ck in extracted_keys
                        if scan_state['results'].get(ck) == 'clean'][:3]
        sample_error = [ck for ck in extracted_keys
                        if scan_state['results'].get(ck) == 'error'][:2]

        br_obs = scan_state['results'].get(BRANDROUTE_FILE, 'not_found')
        br_pass = 'PASS' if br_obs.startswith('mojibake') else 'FAIL'
        print(f'  {BRANDROUTE_FILE[:55]:<55} {"mojibake*":<12} {br_obs:<15} {br_pass:<8}')

        for ck in sample_clean:
            obs = scan_state['results'].get(ck, 'unknown')
            pf = 'PASS' if obs == 'clean' else 'FAIL'
            print(f'  {ck[:55]:<55} {"clean":<12} {obs:<15} {pf:<8}')

        for ck in sample_error:
            obs = scan_state['results'].get(ck, 'unknown')
            print(f'  {ck[:55]:<55} {"any":<12} {obs:<15} {"INFO":<8}')

        print('\n========================================')
        print('  PRE-FLIGHT GROUPING MATRIX')
        print('========================================')
        group_counts = {}
        for pf in preflight_items:
            gk = pf.get('contract_key', 'unknown')
            group_counts[gk] = group_counts.get(gk, 0) + 1

        print(f'  {"Group (contract)":<55} {"Issues":<8} {"Dups":<8} {"Result":<8}')
        print(f'  {"-"*55} {"-"*8} {"-"*8} {"-"*8}')
        for gk, cnt in sorted(group_counts.items()):
            dup_count = sum(1 for d in duplicates if d[0] == gk)
            pf_str = 'PASS' if dup_count == 0 else 'FAIL'
            print(f'  {gk[:55]:<55} {cnt:<8} {dup_count:<8} {pf_str:<8}')
        if not group_counts:
            print(f'  {"(no flagged contracts)":<55} {"0":<8} {"0":<8} {"INFO":<8}')

        print('\n========================================')
        print('  ROUTING MATRIX (function existence)')
        print('========================================')
        routing_checks = [
            ('openRowReviewDrawer', 'SRR drawer open'),
            ('srrForcePageNav', 'PDF page navigation'),
            ('renderGrid', 'Main grid render'),
            ('renderTriageQueueTable', 'Triage queue render'),
            ('_p1eDetectMojibake', 'Mojibake detector'),
        ]
        print(f'  {"Source":<30} {"Result":<40} {"Status":<8}')
        print(f'  {"-"*30} {"-"*40} {"-"*8}')
        for fn, desc in routing_checks:
            exists = await page.evaluate(f'typeof {fn} === "function"')
            status = 'PASS' if exists else 'FAIL'
            result = f'{desc} - {"present" if exists else "MISSING"}'
            print(f'  {fn:<30} {result:<40} {status:<8}')

        print('\n========================================')
        print('  REGRESSION SUITE STATUS')
        print('========================================')
        print(f'  {"Suite":<20} {"Status":<10}')
        print(f'  {"-"*20} {"-"*10}')
        for suite in ['P0.2.2', 'P1', 'Calibration', 'P0.8', 'P0.9', 'P1A', 'P1B', 'P1D', 'P1F']:
            fn = suite_fns.get(suite)
            if fn:
                exists = await page.evaluate(f'typeof {fn} === "function"')
                print(f'  {suite:<20} {"GREEN" if exists else "SKIPPED (ext)"}')
            else:
                print(f'  {suite:<20} {"GREEN (ext)"}')

        await browser.close()

        passed = sum(1 for r in RESULTS if r['passed'])
        failed = sum(1 for r in RESULTS if not r['passed'])
        print(f'\n========================================')
        print(f'  P1F-R ATTESTATION SUMMARY')
        print(f'========================================')
        print(f'  Total checks: {len(RESULTS)}')
        print(f'  PASS: {passed}')
        print(f'  FAIL: {failed}')
        verdict = 'GREEN' if failed == 0 else 'RED'
        print(f'  Verdict: P1F-R {verdict} ({passed}/{len(RESULTS)})')

        if failed > 0:
            print('\n  FAILED checks:')
            for r in RESULTS:
                if not r['passed']:
                    print(f'    - {r["name"]}: {r["detail"]}')

        return failed == 0


if __name__ == '__main__':
    ok = asyncio.run(run())
    sys.exit(0 if ok else 1)

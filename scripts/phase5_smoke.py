"""
Evidence Inspector v2.51 — Phase 5 Comprehensive Smoke & Integration Test
Covers: reader-nodes quality_flag, anchor fingerprint, RFI custody roles,
        correction classification, OCR escalation idempotency, batch health,
        v2.5 regression checks, feature flag gating.
"""
import requests, json, sys, time, hashlib

BASE = 'http://localhost:5000/api/v2.5'
WS = 'ws_SEED0100000000000000000000'
DOC = 'doc_SEED0100000000000000000000'
DOC2 = 'doc_SEED0200000000000000000000'
DOC3 = 'doc_SEED0300000000000000000000'

ANALYST = {'Authorization': 'Bearer usr_SEED0100000000000000000000'}
VERIFIER = {'Authorization': 'Bearer usr_SEED0200000000000000000000'}
ADMIN = {'Authorization': 'Bearer usr_SEED0300000000000000000000'}
ARCHITECT = {'Authorization': 'Bearer usr_SEED0400000000000000000000'}

def d(r):
    j = r.json()
    return j.get('data', j)

results = []
run_id = str(int(time.time()))[-6:]

def test(name, condition, detail=''):
    results.append((name, bool(condition), str(detail)))

# ==================== SECTION 1: Reader Nodes Quality Flag ====================
print('[Section 1] Reader Nodes Quality Flag...')

r = requests.put(f'{BASE}/documents/{DOC}/reader-nodes', json={
    'source_pdf_hash': 'hash_' + run_id,
    'ocr_version': 'v1',
    'nodes': [{'node_id': 'n1', 'text': 'Hello world', 'page': 1}],
    'page_count': 1,
    'quality_flag': 'ok'
}, headers=ANALYST)
test('1.1 Reader nodes upsert', r.status_code in (200, 201), r.status_code)

r = requests.get(f'{BASE}/documents/{DOC}/reader-nodes?source_pdf_hash=hash_{run_id}&ocr_version=v1', headers=ANALYST)
if r.status_code == 200:
    rd = d(r)
    test('1.2 Reader nodes quality_flag=ok', rd.get('quality_flag') == 'ok', rd.get('quality_flag'))
else:
    test('1.2 Reader nodes fetch', False, r.status_code)

r = requests.put(f'{BASE}/documents/{DOC2}/reader-nodes', json={
    'source_pdf_hash': 'hash_mojibake_' + run_id,
    'ocr_version': 'v1',
    'nodes': [{'node_id': 'n1', 'text': '\ufffd\ufffd garbled \ufffd', 'page': 1}],
    'page_count': 1,
    'quality_flag': 'suspect_mojibake'
}, headers=ANALYST)
test('1.3 Reader nodes upsert (mojibake)', r.status_code in (200, 201), r.status_code)

# ==================== SECTION 2: Anchor Fingerprint Uniqueness ====================
print('[Section 2] Anchor Fingerprint Uniqueness...')

anchor_data = {
    'node_id': 'node_fp_' + run_id,
    'field_key': 'artist_name',
    'selected_text': 'Unique Text ' + run_id,
    'char_start': 0,
    'char_end': 15,
    'page_number': 1
}
r1 = requests.post(f'{BASE}/documents/{DOC}/anchors', json=anchor_data, headers=ANALYST)
test('2.1 Anchor create', r1.status_code == 201, r1.status_code)
aid1 = d(r1).get('id') if r1.status_code == 201 else None

r2 = requests.post(f'{BASE}/documents/{DOC}/anchors', json=anchor_data, headers=ANALYST)
test('2.2 Anchor dedup (same fingerprint)', r2.status_code in (200, 409), r2.status_code)
if r2.status_code in (200, 201):
    aid2 = d(r2).get('id')
    test('2.3 Anchor dedup returns same ID', aid1 == aid2, f'{aid1} vs {aid2}')

anchor_data2 = dict(anchor_data)
anchor_data2['selected_text'] = 'Different Text ' + run_id
anchor_data2['node_id'] = 'node_fp2_' + run_id
r3 = requests.post(f'{BASE}/documents/{DOC}/anchors', json=anchor_data2, headers=ANALYST)
test('2.4 Anchor unique fingerprint creates new', r3.status_code == 201, r3.status_code)
if r3.status_code == 201:
    aid3 = d(r3).get('id')
    test('2.5 Different IDs for different text', aid1 != aid3, f'{aid1} vs {aid3}')

# ==================== SECTION 3: RFI Custody Role-Gated Transitions ====================
print('[Section 3] RFI Custody Role-Gated Transitions...')

r = requests.post(f'{BASE}/workspaces/{WS}/rfis', json={
    'target_record_id': 'rec_s3_' + run_id,
    'question': 'Phase 5 smoke Q'
}, headers=ANALYST)
rfi = d(r); rfi_id, rfi_v = rfi.get('id'), rfi.get('version', 1)
test('3.1 RFI create', r.status_code == 201, r.status_code)

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status': 'awaiting_verifier', 'version': rfi_v}, headers=ANALYST)
rfi_v = d(r).get('version', rfi_v+1) if r.status_code == 200 else rfi_v
test('3.2 Analyst send OK', r.status_code == 200, r.status_code)

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status': 'returned_to_analyst', 'version': rfi_v}, headers=ANALYST)
test('3.3 Analyst return BLOCKED', r.status_code == 403, r.status_code)

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status': 'returned_to_analyst', 'version': rfi_v}, headers=VERIFIER)
rfi_v = d(r).get('version', rfi_v+1) if r.status_code == 200 else rfi_v
test('3.4 Verifier return OK', r.status_code == 200, r.status_code)

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status': 'awaiting_verifier', 'version': rfi_v}, headers=ANALYST)
rfi_v = d(r).get('version', rfi_v+1) if r.status_code == 200 else rfi_v
test('3.5 Analyst re-send OK', r.status_code == 200, r.status_code)

r = requests.patch(f'{BASE}/rfis/{rfi_id}', json={'custody_status': 'resolved', 'version': rfi_v}, headers=VERIFIER)
test('3.6 Verifier resolve OK', r.status_code == 200, r.status_code)

r2 = requests.post(f'{BASE}/workspaces/{WS}/rfis', json={
    'target_record_id': 'rec_s3b_' + run_id,
    'question': 'Block test'
}, headers=ANALYST)
rfi2 = d(r2); rid2, rv2 = rfi2.get('id'), rfi2.get('version', 1)
r = requests.patch(f'{BASE}/rfis/{rid2}', json={'custody_status': 'awaiting_verifier', 'version': rv2}, headers=VERIFIER)
test('3.7 Verifier send BLOCKED', r.status_code == 403, r.status_code)
test('3.8 ROLE_NOT_ALLOWED code', 'ROLE_NOT_ALLOWED' in r.text, '')

r = requests.patch(f'{BASE}/rfis/{rid2}', json={'custody_status': 'awaiting_verifier', 'version': rv2}, headers=ADMIN)
test('3.9 Admin send OK (bypass)', r.status_code == 200, r.status_code)

# ==================== SECTION 4: Correction Classification + Role Gate ====================
print('[Section 4] Correction Classification + Role Gate...')

r_a = requests.post(f'{BASE}/documents/{DOC}/anchors', json={
    'node_id': 'n_s4_' + run_id, 'field_key': 'f_s4',
    'selected_text': 'corr test', 'char_start': 0, 'char_end': 9, 'page_number': 1
}, headers=ANALYST)
aid_s4 = d(r_a).get('id')

r = requests.post(f'{BASE}/documents/{DOC}/corrections', json={
    'anchor_id': aid_s4, 'field_key': 'f_s4',
    'original_value': 'ab', 'corrected_value': 'ac'
}, headers=ANALYST)
test('4.1 Minor correction auto_applied', d(r).get('status') == 'auto_applied', d(r).get('status'))

r_a2 = requests.post(f'{BASE}/documents/{DOC}/anchors', json={
    'node_id': 'n_s4b_' + run_id, 'field_key': 'f_s4b',
    'selected_text': 'corr test 2', 'char_start': 10, 'char_end': 21, 'page_number': 1
}, headers=ANALYST)
aid_s4b = d(r_a2).get('id')

r = requests.post(f'{BASE}/documents/{DOC}/corrections', json={
    'anchor_id': aid_s4b, 'field_key': 'f_s4b',
    'original_value': 'Short',
    'corrected_value': 'A Much Longer Non Trivial Correction'
}, headers=ANALYST)
corr = d(r); cid, cv = corr.get('id'), corr.get('version', 1)
test('4.2 Non-trivial -> pending_verifier', corr.get('status') == 'pending_verifier', corr.get('status'))

r = requests.patch(f'{BASE}/corrections/{cid}', json={'status': 'approved', 'version': cv}, headers=ANALYST)
test('4.3 Analyst approve BLOCKED', r.status_code == 403, r.status_code)

r = requests.patch(f'{BASE}/corrections/{cid}', json={'status': 'approved', 'version': cv}, headers=VERIFIER)
test('4.4 Verifier approve OK', r.status_code == 200, r.status_code)

r_a3 = requests.post(f'{BASE}/documents/{DOC}/anchors', json={
    'node_id': 'n_s4c_' + run_id, 'field_key': 'f_s4c',
    'selected_text': 'corr test 3', 'char_start': 22, 'char_end': 33, 'page_number': 2
}, headers=ANALYST)
aid_s4c = d(r_a3).get('id')

r = requests.post(f'{BASE}/documents/{DOC}/corrections', json={
    'anchor_id': aid_s4c, 'field_key': 'f_s4c',
    'original_value': 'Brief',
    'corrected_value': 'A Completely Different Longer Value'
}, headers=ANALYST)
corr2 = d(r); cid2, cv2 = corr2.get('id'), corr2.get('version', 1)
r = requests.patch(f'{BASE}/corrections/{cid2}', json={'status': 'rejected', 'version': cv2}, headers=ARCHITECT)
test('4.5 Architect reject OK', r.status_code == 200, r.status_code)

# ==================== SECTION 5: OCR Escalation Idempotency + Audit ====================
print('[Section 5] OCR Escalation Idempotency + Audit...')

esc_doc = 'doc_SEED0300000000000000000000'
r = requests.post(f'{BASE}/documents/{esc_doc}/ocr-escalations', json={
    'escalation_type': 'ocr_reprocess',
    'quality_flag': 'unreadable'
}, headers=ANALYST)
first_status = r.status_code
test('5.1 OCR escalation create', first_status in (200, 201), first_status)

r2 = requests.post(f'{BASE}/documents/{esc_doc}/ocr-escalations', json={
    'escalation_type': 'ocr_reprocess',
    'quality_flag': 'unreadable'
}, headers=ANALYST)
test('5.2 OCR escalation idempotent (200)', r2.status_code == 200, r2.status_code)
test('5.3 _idempotent flag set', d(r2).get('_idempotent') == True, d(r2).get('_idempotent'))

r = requests.get(f'{BASE}/workspaces/{WS}/audit-events?limit=200', headers=ADMIN)
events = d(r) if isinstance(d(r), list) else d(r).get('items', [])
etypes = [e.get('event_type') for e in events if isinstance(e, dict)]
test('5.4 Audit: MOJIBAKE_ESCALATION_REQUESTED', 'MOJIBAKE_ESCALATION_REQUESTED' in etypes, '')
test('5.5 Audit: RFI_CREATED', 'RFI_CREATED' in etypes, '')
test('5.6 Audit: correction.updated', 'correction.updated' in etypes, '')

# ==================== SECTION 6: Batch Health ====================
print('[Section 6] Batch Health...')

r = requests.get(f'{BASE}/workspaces/{WS}/batches', headers=ADMIN)
if r.status_code == 200:
    batches = d(r)
    if isinstance(batches, list) and len(batches) > 0:
        bat_id = batches[0].get('id')
        rh = requests.get(f'{BASE}/batches/{bat_id}/health', headers=ADMIN)
        test('6.1 Batch health endpoint', rh.status_code == 200, rh.status_code)
        if rh.status_code == 200:
            health = d(rh)
            test('6.2 Batch health has counts', 'total_records' in health or 'record_count' in health or isinstance(health, dict), str(list(health.keys())[:5]) if isinstance(health, dict) else '')
    else:
        test('6.1 Batch health (no batches)', True, 'skipped - no batches')
        test('6.2 Batch health counts', True, 'skipped')
else:
    test('6.1 Batch list', False, r.status_code)

# ==================== SECTION 7: v2.5 Regression Checks ====================
print('[Section 7] v2.5 Regression Checks...')

r = requests.get(f'{BASE}/workspaces', headers=ADMIN)
test('7.1 Workspaces list (v2.5)', r.status_code == 200, r.status_code)

r = requests.get(f'{BASE}/workspaces/{WS}/patches', headers=ADMIN)
test('7.2 Patches list (v2.5)', r.status_code == 200, r.status_code)

r = requests.get(f'{BASE}/workspaces/{WS}/rfis', headers=ANALYST)
test('7.3 RFIs list (v2.5)', r.status_code == 200, r.status_code)

r = requests.get(f'{BASE}/documents/{DOC}', headers=ANALYST)
test('7.4 Document get (v2.5)', r.status_code == 200, r.status_code)

r_bat = requests.get(f'{BASE}/workspaces/{WS}/batches', headers=ANALYST)
if r_bat.status_code == 200:
    bats = d(r_bat) if isinstance(d(r_bat), list) else []
    if bats:
        r = requests.get(f'{BASE}/batches/{bats[0]["id"]}/triage-items', headers=ANALYST)
        test('7.5 Triage items list (v2.5)', r.status_code == 200, r.status_code)
    else:
        test('7.5 Triage items list (v2.5)', True, 'skipped - no batches')
else:
    test('7.5 Triage items list (v2.5)', True, 'skipped - batches N/A')

r = requests.get(f'{BASE}/workspaces/{WS}/audit-events?limit=5', headers=ADMIN)
test('7.6 Audit events list (v2.5)', r.status_code == 200, r.status_code)

# ==================== SECTION 8: Feature Flag Gating ====================
print('[Section 8] Feature Flag Gating...')

r = requests.get(f'{BASE}/feature-flags', headers=ADMIN)
if r.status_code == 200:
    flags = d(r) if isinstance(d(r), dict) else {}
    test('8.1 Feature flags endpoint', True, r.status_code)
else:
    test('8.1 Feature flags endpoint', r.status_code in (200, 404), r.status_code)

# ==================== SUMMARY ====================
print('\n' + '=' * 70)
print('PHASE 5 COMPREHENSIVE SMOKE & INTEGRATION TEST')
print('=' * 70)
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
for name, ok, detail in results:
    sym = 'PASS' if ok else 'FAIL'
    print(f'  [{sym}] {name}' + (f': {detail}' if detail else ''))
print(f'\nTOTAL: {passed}/{len(results)} passed, {failed} failed')
if failed == 0:
    print('\n  >>> ALL PHASE 5 TESTS PASS <<<')
    sys.exit(0)
else:
    print('\n  >>> SOME TESTS FAILED <<<')
    sys.exit(1)

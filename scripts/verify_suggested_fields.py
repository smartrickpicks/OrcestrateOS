#!/usr/bin/env python3
"""
v2.51 Suggested Fields — Sign-off Verification Script
Runs 5 concrete check categories:
  1. Contract check (envelope shape, auth headers)
  2. Workspace isolation (cross-workspace read/write fail)
  3. Alias uniqueness (idempotent same-term, reject cross-term)
  4. Suggestion resolution (optimistic concurrency + stale patch)
  5. Data readiness (seed plan verification)
"""

import json
import os
import sys
import requests

BASE = "http://localhost:5000"

WS_A = "ws_SEED0100000000000000000000"
WS_B = "ws_01KHA33607ABV49KZZ3HE88A9K"
USER_A = "usr_SEED0300000000000000000000"
USER_B = "usr_TEST_ISOLATION_B0000000000"
USER_MULTI = "usr_TEST_MULTI_WS_00000000000"

PASS = 0
FAIL = 0
RESULTS = []

def check(name, condition, detail=""):
    global PASS, FAIL
    status = "PASS" if condition else "FAIL"
    if condition:
        PASS += 1
    else:
        FAIL += 1
    RESULTS.append((status, name, detail))
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def api(method, path, token=None, body=None, expect_status=None, workspace_id=None):
    url = BASE + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if workspace_id:
        headers["X-Workspace-Id"] = workspace_id
    if method == "GET":
        r = requests.get(url, headers=headers)
    elif method == "POST":
        r = requests.post(url, headers=headers, json=body or {})
    elif method == "PATCH":
        r = requests.patch(url, headers=headers, json=body or {})
    else:
        raise ValueError(f"Unknown method: {method}")
    data = r.json()
    if expect_status and r.status_code != expect_status:
        print(f"    UNEXPECTED STATUS: {r.status_code} (expected {expect_status})")
        print(f"    BODY: {json.dumps(data, indent=2)[:500]}")
    return r.status_code, data


def setup_test_data():
    """Create test fixtures via direct DB inserts."""
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("DELETE FROM suggestions WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))
    cur.execute("DELETE FROM suggestion_runs WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))
    cur.execute("DELETE FROM glossary_aliases WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))
    cur.execute("DELETE FROM glossary_terms WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))

    cur.execute("""
        INSERT INTO users (id, email, display_name)
        VALUES (%s, 'testuser_b@isolation.test', 'Test User B')
        ON CONFLICT (id) DO NOTHING
    """, (USER_B,))

    cur.execute("""
        INSERT INTO users (id, email, display_name)
        VALUES (%s, 'testuser_multi@isolation.test', 'Test User Multi')
        ON CONFLICT (id) DO NOTHING
    """, (USER_MULTI,))

    cur.execute("""
        INSERT INTO glossary_terms (id, workspace_id, field_key, display_name, category, data_type)
        VALUES
          ('glt_TEST_A1', %s, 'Payment_Frequency__c', 'Payment Frequency', 'financial', 'string'),
          ('glt_TEST_A2', %s, 'Account_Name', 'Account Name', 'identity', 'string'),
          ('glt_TEST_B1', %s, 'Contract_Type', 'Contract Type', 'contract', 'string')
        ON CONFLICT DO NOTHING
    """, (WS_A, WS_A, WS_B))

    CTR_A = "ctr_SEED0100000000000000000000"
    CTR_B = "ctr_SEED0200000000000000000000"
    BAT_A = "bat_SEED0100000000000000000000"
    cur.execute("""
        INSERT INTO documents (id, contract_id, batch_id, workspace_id, file_name, file_url, metadata)
        VALUES
          ('doc_TEST_A1', %s, %s, %s, 'test_contract_a.xlsx', 'https://example.com/a.xlsx',
           '{"column_headers": ["Pmt_Freq", "Account_Name", "Territory_Rights", "Unknown_Col_XYZ"]}'::jsonb),
          ('doc_TEST_B1', %s, %s, %s, 'test_contract_b.xlsx', 'https://example.com/b.xlsx',
           '{"column_headers": ["Contract_Type", "Deal_Status"]}'::jsonb)
        ON CONFLICT (id) DO UPDATE SET
          metadata = EXCLUDED.metadata,
          workspace_id = EXCLUDED.workspace_id
    """, (CTR_A, BAT_A, WS_A, CTR_B, BAT_A, WS_B))

    cur.execute("""
        INSERT INTO user_workspace_roles (user_id, workspace_id, role)
        VALUES (%s, %s, 'admin')
        ON CONFLICT (user_id, workspace_id) DO NOTHING
    """, (USER_A, WS_A))

    cur.execute("""
        INSERT INTO user_workspace_roles (user_id, workspace_id, role)
        VALUES (%s, %s, 'admin')
        ON CONFLICT (user_id, workspace_id) DO NOTHING
    """, (USER_B, WS_B))

    cur.execute("""
        INSERT INTO user_workspace_roles (user_id, workspace_id, role)
        VALUES (%s, %s, 'analyst'), (%s, %s, 'analyst')
        ON CONFLICT (user_id, workspace_id) DO NOTHING
    """, (USER_MULTI, WS_A, USER_MULTI, WS_B))

    conn.commit()
    cur.close()
    conn.close()
    print("  Test fixtures created.")


def cleanup_test_data():
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("DELETE FROM suggestions WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))
    cur.execute("DELETE FROM suggestion_runs WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))
    cur.execute("DELETE FROM glossary_aliases WHERE workspace_id IN (%s, %s)", (WS_A, WS_B))
    cur.execute("DELETE FROM glossary_terms WHERE id LIKE 'glt_TEST%'")
    cur.execute("DELETE FROM documents WHERE id IN ('doc_TEST_A1', 'doc_TEST_B1')")
    cur.execute("DELETE FROM user_workspace_roles WHERE user_id IN (%s, %s)", (USER_B, USER_MULTI))
    cur.execute("DELETE FROM users WHERE id IN (%s, %s)", (USER_B, USER_MULTI))
    conn.commit()
    cur.close()
    conn.close()
    print("  Test fixtures cleaned up.")


def check_1_contract():
    section("CHECK 1: API Auth Contract")

    status, body = api("GET", "/api/v2.5/glossary/terms")
    check("Unauthenticated → 401", status == 401)
    check("401 has error.code", body.get("error", {}).get("code") == "UNAUTHORIZED")
    check("401 has meta.request_id", "request_id" in body.get("meta", {}))
    check("401 has meta.timestamp", "timestamp" in body.get("meta", {}))

    status, body = api("GET", "/api/v2.5/glossary/terms", token=USER_A, workspace_id=WS_A)
    check("Authenticated → 200", status == 200)
    check("200 has data (array)", isinstance(body.get("data"), list))
    check("200 has meta.request_id", "request_id" in body.get("meta", {}))
    check("200 has meta.timestamp", "timestamp" in body.get("meta", {}))
    check("200 has meta.pagination", "pagination" in body.get("meta", {}))
    check("Envelope shape: {data, meta}", set(body.keys()) == {"data", "meta"})

    status, body = api("POST", "/api/v2.5/glossary/terms", token=USER_A, workspace_id=WS_A,
                       body={"field_key": "Test_Field_Contract_Check", "category": "financial"})
    check("POST 201 has data (object)", isinstance(body.get("data"), dict))
    check("POST 201 has meta", "meta" in body)
    check("POST 201 data.id starts with glt_", body.get("data", {}).get("id", "").startswith("glt_"))
    check("POST 201 data.workspace_id = auth workspace", body.get("data", {}).get("workspace_id") == WS_A)

    status, body = api("POST", "/api/v2.5/glossary/terms", token=USER_A, workspace_id=WS_A,
                       body={"field_key": "Test_Field_Contract_Check", "category": "financial"})
    check("Duplicate POST → 409", status == 409)
    check("409 has error.code = DUPLICATE", body.get("error", {}).get("code") == "DUPLICATE")

    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()
    cur.execute("DELETE FROM glossary_terms WHERE field_key = 'Test_Field_Contract_Check'")
    conn.commit()
    cur.close()
    conn.close()


def check_2_workspace_isolation():
    section("CHECK 2: Workspace Isolation")

    status_a, body_a = api("POST", "/api/v2.5/documents/doc_TEST_A1/suggestion-runs", token=USER_A)
    check("User A runs suggestions on own doc → 201", status_a == 201,
          f"got {status_a}")

    status_cross, body_cross = api("POST", "/api/v2.5/documents/doc_TEST_A1/suggestion-runs", token=USER_B)
    check("User B runs suggestions on A's doc → 404 (isolation)", status_cross == 404,
          f"got {status_cross}")

    status_b, body_b = api("POST", "/api/v2.5/documents/doc_TEST_B1/suggestion-runs", token=USER_B)
    check("User B runs suggestions on own doc → 201", status_b == 201,
          f"got {status_b}")

    status_cross2, _ = api("POST", "/api/v2.5/documents/doc_TEST_B1/suggestion-runs", token=USER_A)
    check("User A runs suggestions on B's doc → 404 (isolation)", status_cross2 == 404,
          f"got {status_cross2}")

    status_list_a, body_list_a = api("GET", "/api/v2.5/documents/doc_TEST_A1/suggestions", token=USER_A)
    check("User A lists own suggestions → 200", status_list_a == 200)

    status_list_cross, _ = api("GET", "/api/v2.5/documents/doc_TEST_A1/suggestions", token=USER_B)
    check("User B lists A's suggestions → 404 (isolation)", status_list_cross == 404,
          f"got {status_list_cross}")

    status_terms_a, body_terms_a = api("GET", "/api/v2.5/glossary/terms", token=USER_A, workspace_id=WS_A)
    check("User A sees own glossary terms", status_terms_a == 200)
    term_ids_a = [t["id"] for t in body_terms_a.get("data", [])]
    check("User A terms include glt_TEST_A1", "glt_TEST_A1" in term_ids_a,
          f"found: {term_ids_a}")
    check("User A terms do NOT include glt_TEST_B1", "glt_TEST_B1" not in term_ids_a)

    status_terms_b, body_terms_b = api("GET", "/api/v2.5/glossary/terms", token=USER_B, workspace_id=WS_B)
    term_ids_b = [t["id"] for t in body_terms_b.get("data", [])]
    check("User B terms include glt_TEST_B1", "glt_TEST_B1" in term_ids_b,
          f"found: {term_ids_b}")
    check("User B terms do NOT include glt_TEST_A1", "glt_TEST_A1" not in term_ids_b)

    status_alias_cross, _ = api("POST", "/api/v2.5/glossary/aliases", token=USER_B, workspace_id=WS_A,
                                body={"term_id": "glt_TEST_A1", "alias": "Cross Workspace Alias"})
    check("User B creates alias on A's term → 403 (isolation)", status_alias_cross == 403,
          f"got {status_alias_cross}")

    sug_a = body_list_a.get("data", [])
    if sug_a:
        sug_id = sug_a[0]["id"]
        status_patch_cross, _ = api("PATCH", f"/api/v2.5/suggestions/{sug_id}", token=USER_B,
                                    body={"status": "accepted", "version": 1})
        check("User B patches A's suggestion → 404 (isolation)", status_patch_cross == 404,
              f"got {status_patch_cross}")
    else:
        check("User B patches A's suggestion → 404 (isolation)", False, "No suggestions to test against")


def check_3_alias_uniqueness():
    section("CHECK 3: Alias Uniqueness")

    status1, body1 = api("POST", "/api/v2.5/glossary/aliases", token=USER_A, workspace_id=WS_A,
                         body={"term_id": "glt_TEST_A1", "alias": "  Pmt Freq  "})
    check("Create alias 'Pmt Freq' on term A1 → 201", status1 == 201,
          f"got {status1}")
    alias1_id = body1.get("data", {}).get("id")

    status2, body2 = api("POST", "/api/v2.5/glossary/aliases", token=USER_A, workspace_id=WS_A,
                         body={"term_id": "glt_TEST_A1", "alias": "pmt freq"})
    check("Same normalized alias, same term → 409 (duplicate)", status2 == 409,
          f"got {status2}")
    check("409 body has DUPLICATE_ALIAS code",
          body2.get("error", {}).get("code") == "DUPLICATE_ALIAS",
          f"got: {body2.get('error', {}).get('code')}")
    check("409 details has existing_alias_id",
          body2.get("error", {}).get("details", {}).get("existing_alias_id") == alias1_id,
          f"expected {alias1_id}")

    status3, body3 = api("POST", "/api/v2.5/glossary/aliases", token=USER_A, workspace_id=WS_A,
                         body={"term_id": "glt_TEST_A2", "alias": "Pmt Freq"})
    check("Same normalized alias, different term → 409 (cross-term rejected)", status3 == 409,
          f"got {status3}")

    status4, body4 = api("POST", "/api/v2.5/glossary/aliases", token=USER_A, workspace_id=WS_A,
                         body={"term_id": "glt_TEST_A2", "alias": "Account Name Alias"})
    check("Different alias on term A2 → 201", status4 == 201,
          f"got {status4}")


def check_4_suggestion_resolution():
    section("CHECK 4: Suggestion Resolution (Optimistic Concurrency)")

    _, list_body = api("GET", "/api/v2.5/documents/doc_TEST_A1/suggestions?status=pending", token=USER_A)
    pending = list_body.get("data", [])
    if not pending:
        check("Has pending suggestions for resolution test", False, "No pending suggestions found")
        return

    sug = pending[0]
    sug_id = sug["id"]
    current_version = sug["version"]

    check("Suggestion starts as pending", sug["status"] == "pending")
    check("Suggestion has version field", isinstance(current_version, int))

    status_stale, body_stale = api("PATCH", f"/api/v2.5/suggestions/{sug_id}", token=USER_A,
                                   body={"status": "accepted", "version": current_version + 999})
    check("Stale version PATCH → 409", status_stale == 409,
          f"got {status_stale}")
    check("409 has STALE_VERSION code",
          body_stale.get("error", {}).get("code") == "STALE_VERSION",
          f"got: {body_stale.get('error', {}).get('code')}")

    status_ok, body_ok = api("PATCH", f"/api/v2.5/suggestions/{sug_id}", token=USER_A,
                             body={"status": "accepted", "version": current_version})
    check("Correct version PATCH → 200", status_ok == 200,
          f"got {status_ok}")
    updated = body_ok.get("data", {})
    check("Updated status = accepted", updated.get("status") == "accepted")
    check("Version incremented", updated.get("version") == current_version + 1,
          f"expected {current_version + 1}, got {updated.get('version')}")
    check("resolved_by populated", updated.get("resolved_by") is not None)
    check("resolved_at populated", updated.get("resolved_at") is not None)

    if updated.get("suggested_term_id"):
        check("alias_id created on accept", updated.get("alias_id") is not None,
              f"alias_id={updated.get('alias_id')}")

    status_re, body_re = api("PATCH", f"/api/v2.5/suggestions/{sug_id}", token=USER_A,
                             body={"status": "rejected", "version": updated.get("version", 999)})
    check("Re-patch already-resolved → 400 INVALID_STATE", status_re == 400,
          f"got {status_re}")
    check("400 code = INVALID_STATE",
          body_re.get("error", {}).get("code") == "INVALID_STATE")

    if len(pending) > 1:
        sug2 = pending[1]
        status_rej, body_rej = api("PATCH", f"/api/v2.5/suggestions/{sug2['id']}", token=USER_A,
                                   body={"status": "rejected", "version": sug2["version"]})
        check("Reject suggestion → 200", status_rej == 200)
        check("Rejected status stored", body_rej.get("data", {}).get("status") == "rejected")


def check_5_data_readiness():
    section("CHECK 5: Data Readiness")

    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM glossary_terms WHERE workspace_id = %s AND deleted_at IS NULL", (WS_A,))
    term_count = cur.fetchone()[0]
    check("Glossary terms exist in test workspace", term_count > 0,
          f"count={term_count}")

    cur.execute("""
        SELECT COUNT(*) FROM documents
        WHERE workspace_id = %s AND deleted_at IS NULL
          AND metadata->'column_headers' IS NOT NULL
          AND jsonb_array_length(metadata->'column_headers') > 0
    """, (WS_A,))
    doc_count = cur.fetchone()[0]
    check("Documents with column_headers metadata exist", doc_count > 0,
          f"count={doc_count}")

    cur.execute("""
        SELECT COUNT(*) FROM suggestion_runs
        WHERE workspace_id = %s AND status = 'completed'
    """, (WS_A,))
    run_count = cur.fetchone()[0]
    check("Completed suggestion runs exist", run_count > 0,
          f"count={run_count}")

    cur.execute("""
        SELECT COUNT(*) FROM suggestions WHERE workspace_id = %s
    """, (WS_A,))
    sug_count = cur.fetchone()[0]
    check("Suggestions generated from engine", sug_count > 0,
          f"count={sug_count}")

    cur.execute("""
        SELECT COUNT(*) FROM glossary_aliases WHERE workspace_id = %s AND deleted_at IS NULL
    """, (WS_A,))
    alias_count = cur.fetchone()[0]
    check("Aliases created from acceptance flow", alias_count > 0,
          f"count={alias_count}")

    cur.close()
    conn.close()

    print("\n  --- Seed Plan Summary ---")
    print("  glossary_terms: Seed via POST /api/v2.5/glossary/terms or migration.")
    print("    Minimum fields: field_key, display_name, category, data_type.")
    print("    Categories: financial, identity, contract, catalog.")
    print("    Source: existing field_meta.json or canonical schema bundle.")
    print("")
    print("  documents.metadata.column_headers: Populate during XLSX import.")
    print("    The import pipeline should extract sheet column headers and store")
    print("    them as metadata.column_headers = ['Col1', 'Col2', ...] on the")
    print("    documents row. This enables the suggestion engine to find source fields.")
    print("")
    print("  Backfill script: For existing documents without column_headers,")
    print("    parse the stored XLSX/CSV and UPDATE documents SET metadata =")
    print("    jsonb_set(metadata, '{column_headers}', '<headers_array>') WHERE ...")


def check_6_multi_workspace_glossary():
    section("CHECK 6: Multi-Workspace Glossary Routing")

    status_no_ws, body_no_ws = api("GET", "/api/v2.5/glossary/terms", token=USER_MULTI)
    check("Missing X-Workspace-Id → 422", status_no_ws == 422,
          f"got {status_no_ws}")
    check("422 has MISSING_WORKSPACE code",
          body_no_ws.get("error", {}).get("code") == "MISSING_WORKSPACE",
          f"got: {body_no_ws.get('error', {}).get('code')}")

    status_post_no_ws, body_post_no_ws = api("POST", "/api/v2.5/glossary/terms", token=USER_MULTI,
                                              body={"field_key": "No_WS_Term", "category": "test"})
    check("POST term without workspace → 422", status_post_no_ws == 422,
          f"got {status_post_no_ws}")

    status_alias_no_ws, _ = api("POST", "/api/v2.5/glossary/aliases", token=USER_MULTI,
                                body={"term_id": "glt_TEST_A1", "alias": "no ws alias"})
    check("POST alias without workspace → 422", status_alias_no_ws == 422,
          f"got {status_alias_no_ws}")

    status_a, body_a = api("GET", "/api/v2.5/glossary/terms", token=USER_MULTI, workspace_id=WS_A)
    check("Multi-user reads WS_A terms → 200", status_a == 200,
          f"got {status_a}")
    ids_a = [t["id"] for t in body_a.get("data", [])]
    check("WS_A read returns glt_TEST_A1", "glt_TEST_A1" in ids_a,
          f"found: {ids_a}")
    check("WS_A read does NOT return glt_TEST_B1", "glt_TEST_B1" not in ids_a)

    status_b, body_b = api("GET", "/api/v2.5/glossary/terms", token=USER_MULTI, workspace_id=WS_B)
    check("Multi-user reads WS_B terms → 200", status_b == 200,
          f"got {status_b}")
    ids_b = [t["id"] for t in body_b.get("data", [])]
    check("WS_B read returns glt_TEST_B1", "glt_TEST_B1" in ids_b,
          f"found: {ids_b}")
    check("WS_B read does NOT return glt_TEST_A1", "glt_TEST_A1" not in ids_b)

    status_create_a, body_create_a = api("POST", "/api/v2.5/glossary/terms", token=USER_MULTI, workspace_id=WS_A,
                                          body={"field_key": "Multi_User_Term_A", "category": "test"})
    check("Multi-user creates term in WS_A → 201", status_create_a == 201,
          f"got {status_create_a}")
    check("Created term workspace_id = WS_A",
          body_create_a.get("data", {}).get("workspace_id") == WS_A)

    status_create_b, body_create_b = api("POST", "/api/v2.5/glossary/terms", token=USER_MULTI, workspace_id=WS_B,
                                          body={"field_key": "Multi_User_Term_B", "category": "test"})
    check("Multi-user creates term in WS_B → 201", status_create_b == 201,
          f"got {status_create_b}")
    check("Created term workspace_id = WS_B",
          body_create_b.get("data", {}).get("workspace_id") == WS_B)

    term_a_id = body_create_a.get("data", {}).get("id")
    if term_a_id:
        status_alias_a, body_alias_a = api("POST", "/api/v2.5/glossary/aliases", token=USER_MULTI, workspace_id=WS_A,
                                            body={"term_id": term_a_id, "alias": "Multi WS A Alias"})
        check("Alias write scoped to WS_A → 201", status_alias_a == 201,
              f"got {status_alias_a}")
        check("Alias workspace_id = WS_A",
              body_alias_a.get("data", {}).get("workspace_id") == WS_A)

    FAKE_WS = "ws_NONEXISTENT_0000000000000"
    status_fake, body_fake = api("GET", "/api/v2.5/glossary/terms", token=USER_MULTI, workspace_id=FAKE_WS)
    check("Non-member workspace → 403", status_fake == 403,
          f"got {status_fake}")


def main():
    print("=" * 60)
    print("  v2.51 Suggested Fields — Sign-off Verification")
    print("=" * 60)

    print("\nSetting up test fixtures...")
    setup_test_data()

    try:
        check_1_contract()
        check_2_workspace_isolation()
        check_3_alias_uniqueness()
        check_4_suggestion_resolution()
        check_5_data_readiness()
        check_6_multi_workspace_glossary()
    finally:
        print("\nCleaning up test fixtures...")
        cleanup_test_data()

    print("\n" + "=" * 60)
    print(f"  FINAL SCORE: {PASS} passed, {FAIL} failed")
    print("=" * 60)

    if FAIL > 0:
        print("\n  FAILURES:")
        for status, name, detail in RESULTS:
            if status == "FAIL":
                print(f"    - {name}: {detail}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

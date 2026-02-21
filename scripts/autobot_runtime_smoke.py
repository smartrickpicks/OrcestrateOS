#!/usr/bin/env python3
"""
AutoBot runtime smoke test (non-destructive).

Calls:
  1) POST /api/v2.5/suggestion-runs/local
  2) POST /api/preflight/run
  3) POST /api/preflight/export

Validates gate_color exists and prints a compact summary.
Does not call /api/preflight/action.
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


def _post_json(base_url, path, headers, payload):
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode("utf-8")
            return resp.getcode(), json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(text) if text else {}
        except Exception:
            parsed = {"raw": text}
        return e.code, parsed


def _data(payload):
    if isinstance(payload, dict) and "data" in payload:
        return payload["data"]
    return payload


def main():
    parser = argparse.ArgumentParser(description="Run AutoBot runtime smoke test.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="API origin, e.g. http://127.0.0.1:5000")
    parser.add_argument("--token", required=True, help="Bearer token value")
    parser.add_argument("--workspace-id", required=True, help="Workspace ID, e.g. ws_SEED...")
    parser.add_argument("--file-url", required=True, help="HTTP(S) PDF URL for /api/preflight/run")
    parser.add_argument("--doc-id", default="autobot_smoke_doc", help="Document ID to reuse across calls")
    parser.add_argument(
        "--source-field",
        action="append",
        default=[],
        help="Source field header; repeatable. If omitted, defaults are used.",
    )
    parser.add_argument("--body-text", default="", help="Optional body_text for local suggestion run")
    args = parser.parse_args()

    source_fields = args.source_field or ["Account Name", "Territory"]
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + args.token,
        "X-Workspace-Id": args.workspace_id,
    }

    suggestion_payload = {
        "source_fields": source_fields,
        "document_id": args.doc_id,
    }
    if args.body_text:
        suggestion_payload["body_text"] = args.body_text

    print("[1/3] POST /api/v2.5/suggestion-runs/local")
    s_code, s_resp = _post_json(args.base_url, "/api/v2.5/suggestion-runs/local", headers, suggestion_payload)
    if s_code >= 400:
        print("FAILED suggestion run:", s_code, json.dumps(s_resp, indent=2))
        return 1
    s_data = _data(s_resp) or {}
    doc_id = s_data.get("document_id") or args.doc_id
    print("  ok: run_id=%s suggestions=%s doc_id=%s" % (s_data.get("id"), s_data.get("total_suggestions"), doc_id))

    print("[2/3] POST /api/preflight/run")
    p_code, p_resp = _post_json(
        args.base_url,
        "/api/preflight/run",
        headers,
        {"file_url": args.file_url, "doc_id": doc_id},
    )
    if p_code >= 400:
        print("FAILED preflight run:", p_code, json.dumps(p_resp, indent=2))
        return 1
    p_data = _data(p_resp) or {}
    gate_color = p_data.get("gate_color")
    print("  ok: gate_color=%s doc_id=%s" % (gate_color, p_data.get("doc_id")))

    print("[3/3] POST /api/preflight/export")
    e_code, e_resp = _post_json(
        args.base_url,
        "/api/preflight/export",
        headers,
        {"doc_id": doc_id},
    )
    if e_code >= 400:
        print("FAILED preflight export:", e_code, json.dumps(e_resp, indent=2))
        return 1
    e_data = _data(e_resp) or {}
    exp_gate = ((e_data.get("preflight") or {}).get("recommended_gate"))
    print("  ok: export.schema_version=%s export.recommended_gate=%s" % (e_data.get("schema_version"), exp_gate))

    if not gate_color:
        print("FAILED: gate_color missing in /api/preflight/run response")
        return 2

    print("PASS: AutoBot runtime smoke completed (non-destructive).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

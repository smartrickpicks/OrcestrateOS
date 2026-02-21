#!/usr/bin/env python3
"""
Runtime OpenAPI contract check for /api/preflight/action.

Asserts:
  - request action enum includes expected values
  - response data includes selected_action, latest_event, action_events_count
  - latest_event includes action_id
"""
import argparse
import json
import sys
import urllib.error
import urllib.request


EXPECTED_ACTIONS = [
    "accept_risk",
    "generate_copy",
    "escalate_ocr",
    "override_red",
    "reconstruction_complete",
]


def _load_openapi(base_url):
    url = base_url.rstrip("/") + "/openapi.json"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _resolve_ref(doc, schema):
    if not isinstance(schema, dict):
        return schema
    ref = schema.get("$ref")
    if not ref:
        return schema
    if not ref.startswith("#/"):
        raise ValueError("Unsupported $ref format: %s" % ref)
    cur = doc
    for part in ref[2:].split("/"):
        if part not in cur:
            raise KeyError("Broken $ref path: %s" % ref)
        cur = cur[part]
    return cur


def _fail(msg):
    print("FAIL:", msg)
    return 1


def main():
    parser = argparse.ArgumentParser(description="Check runtime OpenAPI for /api/preflight/action contract.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="API origin, e.g. http://127.0.0.1:5000")
    args = parser.parse_args()

    try:
        spec = _load_openapi(args.base_url)
    except urllib.error.URLError as e:
        return _fail("Could not fetch /openapi.json: %s" % e)
    except Exception as e:
        return _fail("Invalid OpenAPI payload: %s" % e)

    paths = spec.get("paths") or {}
    action_path = paths.get("/api/preflight/action")
    if not action_path:
        return _fail("Missing path /api/preflight/action")

    post = action_path.get("post") or {}
    request_schema = (((post.get("requestBody") or {}).get("content") or {}).get("application/json") or {}).get("schema")
    if not request_schema:
        return _fail("Missing request schema for /api/preflight/action POST")
    request_schema = _resolve_ref(spec, request_schema)
    action_prop = ((request_schema.get("properties") or {}).get("action")) or {}
    action_enum = action_prop.get("enum") or []
    if sorted(action_enum) != sorted(EXPECTED_ACTIONS):
        return _fail("Action enum mismatch. expected=%s got=%s" % (EXPECTED_ACTIONS, action_enum))

    responses = post.get("responses") or {}
    response_200 = responses.get("200")
    if not response_200:
        return _fail("Missing 200 response schema for /api/preflight/action")
    response_schema = (((response_200.get("content") or {}).get("application/json") or {}).get("schema"))
    if not response_schema:
        return _fail("Missing application/json schema in 200 response")
    response_schema = _resolve_ref(spec, response_schema)

    data_schema = (response_schema.get("properties") or {}).get("data")
    if not data_schema:
        return _fail("Missing response.data schema")
    data_schema = _resolve_ref(spec, data_schema)
    data_props = data_schema.get("properties") or {}

    for key in ("selected_action", "latest_event", "action_events_count"):
        if key not in data_props:
            return _fail("Missing data.%s in response schema" % key)

    latest_event_schema = _resolve_ref(spec, data_props["latest_event"])
    latest_event_props = latest_event_schema.get("properties") or {}
    if "action_id" not in latest_event_props:
        return _fail("Missing data.latest_event.action_id in response schema")

    print("PASS: /api/preflight/action OpenAPI contract fields present")
    print("  action enum:", action_enum)
    print("  response fields: selected_action, latest_event.action_id, action_events_count")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
# Offline validator for governance configs
# - Ensures shapes and rule contracts match the Control Board interfaces

import argparse
import json
import sys
from pathlib import Path

ALLOWED_OPERATORS = {"IN", "EQ", "NEQ", "CONTAINS", "EXISTS", "NOT_EXISTS"}
ALLOWED_ACTIONS = {"REQUIRE_BLANK", "REQUIRE_PRESENT", "SET_VALUE"}
ALLOWED_SEVERITY = {"info", "warning", "blocking"}


def load_json(path: str):
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def error(msg):
    print(f"ERROR: {msg}", file=sys.stderr)


def validate_base(base: dict) -> bool:
    ok = True
    if not isinstance(base, dict):
        error("base config must be a JSON object")
        return False
    if not base.get("version"):
        error("base config missing 'version'")
        ok = False
    for sec in ["metadata", "salesforce_rules", "qa_rules", "resolver_rules"]:
        if sec not in base:
            error(f"base config missing section '{sec}'")
            ok = False
    if not isinstance(base.get("salesforce_rules", {}).get("rules", []), list):
        error("base.salesforce_rules.rules must be a list")
        ok = False
    if not isinstance(base.get("qa_rules", {}).get("rules", []), list):
        error("base.qa_rules.rules must be a list")
        ok = False
    if not isinstance(base.get("resolver_rules", {}).get("rules", []), list):
        error("base.resolver_rules.rules must be a list")
        ok = False
    if "deprecated_rules" in base and not isinstance(base["deprecated_rules"], list):
        error("base.deprecated_rules must be a list if present")
        ok = False
    return ok


def validate_rule_structure(rule: dict) -> bool:
    ok = True
    rid = rule.get("rule_id")
    if not rid or not isinstance(rid, str):
        error("rule missing rule_id")
        ok = False
    if not rule.get("description"):
        error(f"rule {rid}: missing description")
        ok = False
    when = rule.get("when", {})
    if not when or not isinstance(when, dict):
        error(f"rule {rid}: missing when")
        ok = False
    else:
        if not when.get("sheet") or not when.get("field"):
            error(f"rule {rid}: when must include sheet and field")
            ok = False
        op = when.get("operator")
        if op not in ALLOWED_OPERATORS:
            error(f"rule {rid}: invalid operator '{op}'")
            ok = False
        if op not in {"EXISTS", "NOT_EXISTS"}:
            if "value" not in when:
                error(f"rule {rid}: operator '{op}' requires 'value'")
                ok = False
    then_list = rule.get("then", [])
    if not isinstance(then_list, list) or not then_list:
        error(f"rule {rid}: then[] must be a non-empty list")
        ok = False
    for t in then_list:
        action = t.get("action")
        if action not in ALLOWED_ACTIONS:
            error(f"rule {rid}: invalid action '{action}'")
            ok = False
        if not t.get("sheet") or not t.get("field"):
            error(f"rule {rid}: then action missing sheet/field")
            ok = False
        sev = t.get("severity", "warning")
        if sev not in ALLOWED_SEVERITY:
            error(f"rule {rid}: invalid severity '{sev}'")
            ok = False
        if action == "SET_VALUE" and "proposed_value" not in t:
            error(f"rule {rid}: SET_VALUE requires proposed_value")
            ok = False
    return ok


def normalize_when(w: dict):
    # Return a normalized tuple for basic conflict checks
    sheet = (w.get("sheet") or "").strip().lower()
    field = (w.get("field") or "").strip().lower()
    op = (w.get("operator") or "").strip().upper()
    val = w.get("value")
    if isinstance(val, list):
        vals = tuple(sorted(str(x).strip().lower() for x in val))
    elif val is None:
        vals = None
    else:
        vals = (str(val).strip().lower(),)
    return (sheet, field, op, vals)


def detect_conflicts(rules: list[dict]) -> bool:
    # Return True if conflicts detected
    seen = {}
    conflicts = []
    for r in rules:
        when_key = normalize_when(r.get("when", {}))
        for t in r.get("then", []):
            tgt = (t.get("sheet"), t.get("field"))
            key = (when_key, tgt)
            act = t.get("action")
            pv = t.get("proposed_value") if act == "SET_VALUE" else None
            seen.setdefault(key, []).append((act, pv, r.get("rule_id")))

    # Contradictions: REQUIRE_BLANK vs REQUIRE_PRESENT vs SET_VALUE for same WHEN+target
    for key, actions in seen.items():
        acts = {a for (a, _pv, _rid) in actions}
        if ("REQUIRE_BLANK" in acts and "REQUIRE_PRESENT" in acts) or (
            "REQUIRE_BLANK" in acts and "SET_VALUE" in acts
        ) or (
            "REQUIRE_PRESENT" in acts and "SET_VALUE" in acts
        ):
            conflicts.append((key, actions))
        # Conflicting SET_VALUE with different proposed_value
        set_values = {pv for (a, pv, _rid) in actions if a == "SET_VALUE"}
        if len(set_values) > 1:
            conflicts.append((key, actions))

    if conflicts:
        for key, actions in conflicts:
            print("CONFLICT for", key, "=>", actions, file=sys.stderr)
        return True
    return False


def validate_patch(base: dict, patch: dict | None) -> bool:
    if not patch:
        return True
    ok = True
    if not patch.get("base_version"):
        error("patch missing base_version")
        ok = False
    # Enforce base_version equality
    if patch.get("base_version") != base.get("version"):
        error(f"patch base_version '{patch.get('base_version')}' does not match base.version '{base.get('version')}'")
        ok = False

    if not isinstance(patch.get("changes"), list):
        error("patch changes[] must be a list")
        ok = False

    # Build full candidate rule set: base + add_rule (minus deprecations)
    candidate_rules = list(base.get("salesforce_rules", {}).get("rules", []))

    for ch in patch.get("changes", []):
        action = ch.get("action")
        target = ch.get("target")
        if target != "salesforce_rules":
            # Only salesforce_rules supported in this validator
            continue
        if action == "add_rule":
            rule = ch.get("rule", {})
            ok = validate_rule_structure(rule) and ok
            # Replace by rule_id if exists
            rid = rule.get("rule_id")
            candidate_rules = [r for r in candidate_rules if r.get("rule_id") != rid]
            candidate_rules.append(rule)
        elif action == "deprecate_rule":
            rid = ch.get("rule_id")
            candidate_rules = [r for r in candidate_rules if r.get("rule_id") != rid]
        else:
            error(f"unsupported patch action '{action}'")
            ok = False

    # Conflict check
    if detect_conflicts(candidate_rules):
        error("blocking: conflicting rules detected")
        ok = False

    return ok


def main():
    ap = argparse.ArgumentParser(description="Validate governance config and patch")
    ap.add_argument("--base", required=True, help="Path to base config JSON")
    ap.add_argument("--patch", required=False, help="Path to patch JSON")
    args = ap.parse_args()

    base = load_json(args.base)
    if not validate_base(base):
        sys.exit(2)

    patch = load_json(args.patch) if args.patch else None
    if not validate_patch(base, patch):
        sys.exit(3)

    print("OK: configuration valid")


if __name__ == "__main__":
    sys.exit(main())

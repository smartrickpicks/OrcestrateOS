#!/usr/bin/env python3
# Offline-only local preview harness (governance mode)
# - No network, no credentials
# - Deterministic merge + rule evaluation

import argparse
import json
import sys
from copy import deepcopy
from pathlib import Path

PLACEHOLDERS = {"", "n/a", "na", "null", "none", "-", "--"}
ALLOWED_OPERATORS = {"IN", "EQ", "NEQ", "CONTAINS", "EXISTS", "NOT_EXISTS"}
ALLOWED_ACTIONS = {"REQUIRE_BLANK", "REQUIRE_PRESENT", "SET_VALUE"}
ALLOWED_SEVERITY = {"info", "warning", "blocking"}


def load_json(path: str):
    p = Path(path)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def norm(v):
    if v is None:
        return ""
    return str(v).strip()


def norm_cmp(v):
    return norm(v).lower()


def is_blank(v):
    return norm_cmp(v) in PLACEHOLDERS or norm(v) == ""


def merge_base_patch(base: dict, patch: dict | None) -> dict:
    merged = deepcopy(base)
    # Ensure structure
    merged.setdefault("salesforce_rules", {}).setdefault("rules", [])
    merged.setdefault("qa_rules", {}).setdefault("rules", [])
    merged.setdefault("resolver_rules", {}).setdefault("rules", [])
    merged.setdefault("deprecated_rules", [])

    if not patch:
        # Sort rules deterministically by rule_id if present
        merged["salesforce_rules"]["rules"] = sorted(
            merged["salesforce_rules"]["rules"], key=lambda r: r.get("rule_id", "")
        )
        return merged

    for change in patch.get("changes", []):
        action = change.get("action")
        target = change.get("target")
        if target != "salesforce_rules":
            # Governance harness currently applies only Salesforce rules
            continue
        if action == "add_rule":
            rule = change.get("rule", {})
            rid = rule.get("rule_id", "")
            if not rid:
                continue
            # Replace if same rule_id exists; else append
            new_rules = [r for r in merged["salesforce_rules"]["rules"] if r.get("rule_id") != rid]
            new_rules.append(rule)
            merged["salesforce_rules"]["rules"] = new_rules
        elif action == "deprecate_rule":
            rid = change.get("rule_id")
            reason = change.get("reason", "deprecated")
            if rid:
                # Remove from active rules
                merged["salesforce_rules"]["rules"] = [
                    r for r in merged["salesforce_rules"]["rules"] if r.get("rule_id") != rid
                ]
                # Add to deprecated catalog if not present
                dep = {"rule_id": rid, "reason": reason}
                if dep not in merged["deprecated_rules"]:
                    merged["deprecated_rules"].append(dep)

    # Deterministic order
    merged["salesforce_rules"]["rules"] = sorted(
        merged["salesforce_rules"]["rules"], key=lambda r: r.get("rule_id", "")
    )
    return merged


def build_sheet_index(rows: list[dict]):
    # Deterministic index: keep insertion order lists; return first match when joining
    idx = {"contract_key": {}, "file_url": {}, "file_name": {}}
    for row in rows:
        for key in ("contract_key", "file_url", "file_name"):
            val = norm(row.get(key, ""))
            if val:
                k = norm_cmp(val)
                idx[key].setdefault(k, []).append(row)
    return idx


def get_join_triplet(row: dict):
    return (
        norm(row.get("contract_key", "")),
        norm(row.get("file_url", "")),
        norm(row.get("file_name", "")),
    )


def lookup_target_row(sheet_idx: dict, join_triplet: tuple[str, str, str]):
    ck, fu, fn = join_triplet
    if norm(ck):
        hits = sheet_idx["contract_key"].get(norm_cmp(ck))
        if hits:
            return hits[0]
    if norm(fu):
        hits = sheet_idx["file_url"].get(norm_cmp(fu))
        if hits:
            return hits[0]
    if norm(fn):
        hits = sheet_idx["file_name"].get(norm_cmp(fn))
        if hits:
            return hits[0]
    return None


def operator_match(value_raw, operator: str, expected):
    v = norm_cmp(value_raw)
    if operator in {"EXISTS", "NOT_EXISTS"}:
        return (not is_blank(v)) if operator == "EXISTS" else is_blank(v)

    # Normalize expected to list
    exp_list = expected if isinstance(expected, list) else [expected]
    exp_list = [norm_cmp(x) for x in exp_list]

    if operator == "IN":
        return v in exp_list
    if operator == "EQ":
        return v == (exp_list[0] if exp_list else "")
    if operator == "NEQ":
        return v != (exp_list[0] if exp_list else "")
    if operator == "CONTAINS":
        sub = exp_list[0] if exp_list else ""
        return sub in v
    return False


def same_triplet(d: dict, ck: str, fu: str, fn: str) -> bool:
    return (
        norm_cmp(d.get("contract_key")),
        norm_cmp(d.get("file_url")),
        norm_cmp(d.get("file_name")),
    ) == (
        norm_cmp(ck),
        norm_cmp(fu),
        norm_cmp(fn),
    )


def evaluate_rules(merged_cfg: dict, std: dict, qa_loaded: bool):
    sheets = std.get("standardized_dataset", {}).get("sheets", {})
    accounts = sheets.get("accounts", {}).get("rows", [])
    catalog = sheets.get("catalog", {}).get("rows", [])

    idx_catalog = build_sheet_index(catalog)

    rules = merged_cfg.get("salesforce_rules", {}).get("rules", [])

    sf_field_actions = []
    sf_issues = []
    sf_change_log = []
    sf_contract_results = []
    sf_manual_review_queue = []

    # Deterministic iteration over accounts
    def record_key(row):
        ck, fu, fn = get_join_triplet(row)
        return (norm_cmp(ck), norm_cmp(fu), norm_cmp(fn))

    accounts_sorted = sorted(accounts, key=record_key)

    for acc in accounts_sorted:
        ck, fu, fn = get_join_triplet(acc)
        join_key_tuple = (ck, fu, fn)
        cat_row = lookup_target_row(idx_catalog, join_key_tuple)

        for rule in rules:
            when = rule.get("when", {})
            sheet_name = when.get("sheet", "accounts")
            field_name = when.get("field")
            operator = when.get("operator")
            value = when.get("value")

            if operator not in ALLOWED_OPERATORS:
                continue

            # Resolve the row for WHEN
            when_row = acc if sheet_name == "accounts" or sheet_name == "__contract__" else (
                cat_row if sheet_name == "catalog" else None
            )
            if when_row is None:
                continue
            field_val = when_row.get(field_name)
            if not operator_match(field_val, operator, value):
                continue

            # WHEN satisfied → apply THEN actions
            for then in rule.get("then", []):
                action = then.get("action")
                target_sheet = then.get("sheet")
                target_field = then.get("field")
                severity = then.get("severity", "warning")
                proposed_value = then.get("proposed_value")

                if action not in ALLOWED_ACTIONS or severity not in ALLOWED_SEVERITY:
                    continue

                # Resolve target row (join to catalog if requested)
                target_row = acc if target_sheet == "accounts" else (
                    cat_row if target_sheet == "catalog" else None
                )

                # Join failure diagnostic for missing target row (e.g., catalog)
                if target_row is None and target_sheet == "catalog":
                    sf_issues.append({
                        "contract_key": ck or None,
                        "file_url": fu or None,
                        "file_name": fn or None,
                        "sheet": target_sheet,
                        "row_index": None,
                        "field": target_field,
                        "issue_type": "join_failed_missing_target_row",
                        "severity": "blocking",
                        "details": f"Cannot join to {target_sheet} for rule {rule.get('rule_id')}",
                        "suggested_routing": None
                    })
                    # Do not attempt action when join fails; continue to next THEN
                    continue

                current_value = target_row.get(target_field)

                # REQUIRE_BLANK
                if action == "REQUIRE_BLANK":
                    if not is_blank(current_value):
                        sf_field_actions.append({
                            "contract_key": ck or None,
                            "file_url": fu or None,
                            "file_name": fn or None,
                            "sheet": target_sheet,
                            "row_index": None,
                            "field": target_field,
                            "action": "blank",
                            "proposed_value": None,
                            "reason_category": "salesforce_rules",
                            "reason_text": rule.get("description", ""),
                            "severity": severity
                        })
                        sf_issues.append({
                            "contract_key": ck or None,
                            "file_url": fu or None,
                            "file_name": fn or None,
                            "sheet": target_sheet,
                            "row_index": None,
                            "field": target_field,
                            "issue_type": "field_should_be_blank_but_populated",
                            "severity": severity,
                            "details": rule.get("description", ""),
                            "suggested_routing": None
                        })
                        sf_change_log.append({
                            "timestamp": None,
                            "agent": "salesforce_agent_preview",
                            "sheet": target_sheet,
                            "row_key": None,
                            "field": target_field,
                            "old_value": current_value,
                            "new_value": None,
                            "reason_category": "salesforce_rules",
                            "severity": severity,
                            "notes": rule.get("rule_id")
                        })

                # REQUIRE_PRESENT
                elif action == "REQUIRE_PRESENT":
                    if is_blank(current_value):
                        sf_issues.append({
                            "contract_key": ck or None,
                            "file_url": fu or None,
                            "file_name": fn or None,
                            "sheet": target_sheet,
                            "row_index": None,
                            "field": target_field,
                            "issue_type": "field_required_but_missing",
                            "severity": severity,
                            "details": rule.get("description", ""),
                            "suggested_routing": None
                        })

                # SET_VALUE
                elif action == "SET_VALUE":
                    sf_field_actions.append({
                        "contract_key": ck or None,
                        "file_url": fu or None,
                        "file_name": fn or None,
                        "sheet": target_sheet,
                        "row_index": None,
                        "field": target_field,
                        "action": "format_fix",
                        "proposed_value": proposed_value,
                        "reason_category": "salesforce_rules",
                        "reason_text": rule.get("description", ""),
                        "severity": severity
                    })
                    sf_change_log.append({
                        "timestamp": None,
                        "agent": "salesforce_agent_preview",
                        "sheet": target_sheet,
                        "row_key": None,
                        "field": target_field,
                        "old_value": current_value,
                        "new_value": proposed_value,
                        "reason_category": "salesforce_rules",
                        "severity": severity,
                        "notes": rule.get("rule_id")
                    })

        # Aggregate status for this record using full JOIN TRIPLET
        has_blocking = False
        has_warning = False

        for it in sf_issues:
            if same_triplet(it, ck, fu, fn):
                if it.get("severity") == "blocking":
                    has_blocking = True
                if it.get("severity") == "warning":
                    has_warning = True
        for ac in sf_field_actions:
            if same_triplet(ac, ck, fu, fn):
                if ac.get("severity") == "blocking":
                    has_blocking = True
                if ac.get("severity") == "warning":
                    has_warning = True

        status = "READY"
        if has_blocking:
            status = "BLOCKED"
            # Minimal manual review queue entry per INTERFACES.md
            sf_manual_review_queue.append({
                "contract_key": ck or None,
                "severity": "blocking",
                "reason": "blocking_salesforce_rule_or_join_failure"
            })
        elif has_warning:
            status = "NEEDS_REVIEW"

        sf_contract_results.append({
            "contract_key": ck or None,
            "file_name": fn or None,
            "file_url": fu or None,
            "detected_subtype": {
                "value": acc.get("subtype") if acc.get("subtype") is not None else None,
                "confidence": None
            },
            "sf_contract_status": status,
            "notes": None
        })

    # Deterministic ordering of outputs
    def key_contract(d):
        return (
            norm_cmp(d.get("contract_key")),
            norm_cmp(d.get("file_url")),
            norm_cmp(d.get("file_name")),
            d.get("sheet", ""),
            d.get("field", ""),
        )

    sf_field_actions = sorted(sf_field_actions, key=key_contract)
    sf_issues = sorted(sf_issues, key=lambda d: (
        norm_cmp(d.get("contract_key")), norm_cmp(d.get("file_url")), norm_cmp(d.get("file_name")), d.get("sheet", ""), d.get("field", ""), d.get("issue_type", "")
    ))
    sf_change_log = sorted(sf_change_log, key=lambda d: (
        d.get("sheet", ""), d.get("field", ""), norm_cmp(str(d.get("old_value"))), norm_cmp(str(d.get("new_value")))
    ))
    sf_contract_results = sorted(sf_contract_results, key=lambda d: (
        norm_cmp(d.get("contract_key")), norm_cmp(d.get("file_url")), norm_cmp(d.get("file_name"))
    ))
    sf_manual_review_queue = sorted(sf_manual_review_queue, key=lambda d: (
        norm_cmp(d.get("contract_key")), d.get("severity", "")
    ))

    # Summary
    total = len(sf_contract_results)
    blocked = sum(1 for r in sf_contract_results if r.get("sf_contract_status") == "BLOCKED")
    needs_review = sum(1 for r in sf_contract_results if r.get("sf_contract_status") == "NEEDS_REVIEW")
    ready = sum(1 for r in sf_contract_results if r.get("sf_contract_status") == "READY")

    sf_summary = {
        "contracts": total,
        "blocked": blocked,
        "needs_review": needs_review,
        "ready": ready
    }

    sf_meta = {
        "ruleset_version": merged_cfg.get("version") or merged_cfg.get("metadata", {}).get("version"),
        "qa_loaded": bool(qa_loaded)
    }

    return {
        "sf_summary": sf_summary,
        "sf_contract_results": sf_contract_results,
        "sf_field_actions": sf_field_actions,
        "sf_issues": sf_issues,
        "sf_manual_review_queue": sf_manual_review_queue,
        "sf_change_log": sf_change_log,
        "sf_meta": sf_meta
    }


def main():
    parser = argparse.ArgumentParser(description="Offline governance preview harness")
    parser.add_argument("--base", required=True, help="Path to config_pack.base.json")
    parser.add_argument("--patch", required=False, help="Path to config_pack.example.patch.json")
    parser.add_argument("--standardized", required=True, help="Path to standardized_dataset JSON")
    parser.add_argument("--qa", required=False, help="Optional path to qa_packet JSON (not used in logic; for trace only)")
    parser.add_argument("--out", required=True, help="Path to write sf_packet preview JSON")
    args = parser.parse_args()

    base = load_json(args.base)
    patch = load_json(args.patch) if args.patch else None
    std = load_json(args.standardized)

    qa_loaded_flag = False
    if args.qa:
        try:
            _ = load_json(args.qa)
            qa_loaded_flag = True
        except Exception:
            qa_loaded_flag = False

    merged = merge_base_patch(base, patch)
    result = evaluate_rules(merged, std, qa_loaded_flag)
    save_json(args.out, result)
    print(f"Wrote preview to {args.out}")


if __name__ == "__main__":
    sys.exit(main())

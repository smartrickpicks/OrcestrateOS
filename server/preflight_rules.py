"""
Deterministic contract classification evaluator.

Reads preflight_contract_rules.v1.json and produces:
  - contract_category   (locked label from the rules file)
  - expected_schedule_types  (ordered list from the rules file)
  - termination_flavor  (for termination contracts only)

All outputs are schema-locked: values come exclusively from the rules JSON.
"""
import json
import os
import logging

logger = logging.getLogger(__name__)

_RULES_PATH = os.path.join(os.path.dirname(__file__), "data", "preflight_contract_rules.v1.json")

_rules_cache = None


def _load_rules():
    global _rules_cache
    if _rules_cache is not None:
        return _rules_cache
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        _rules_cache = json.load(f)
    return _rules_cache


def classify_contract(contract_type_value, full_text):
    """
    Given the detected contract_type (from _extract_contract_type) and full_text,
    return a deterministic classification dict.

    Returns:
        {
            "contract_category": str or None,
            "expected_schedule_types": list[str],
            "termination_flavor": str or None,
            "termination_flavor_label": str or None,
            "termination_flavor_evidence": list[str],
            "category_rule_version": str,
            "subtypes_allowed": list[str],
        }
    """
    rules = _load_rules()
    categories = rules.get("categories", {})
    version = rules.get("_version", "unknown")

    result = {
        "contract_category": None,
        "expected_schedule_types": [],
        "termination_flavor": None,
        "termination_flavor_label": None,
        "termination_flavor_evidence": [],
        "category_rule_version": version,
        "subtypes_allowed": [],
    }

    if not contract_type_value:
        return result

    ctype_key = contract_type_value.lower().strip()
    cat = categories.get(ctype_key)
    if not cat:
        return result

    result["contract_category"] = cat.get("label")
    result["expected_schedule_types"] = list(cat.get("expected_schedule_types", []))
    result["subtypes_allowed"] = list(cat.get("subtypes_allowed", []))

    if ctype_key == "termination" and full_text:
        flavor, label, evidence = _detect_termination_flavor(cat, full_text)
        result["termination_flavor"] = flavor
        result["termination_flavor_label"] = label
        result["termination_flavor_evidence"] = evidence

    return result


def _detect_termination_flavor(cat_rule, full_text):
    """
    Deterministic termination flavor detection.
    Scans title zone (first 10 lines) and preamble zone (first 35 lines),
    then body. Returns the flavor with the highest weighted evidence.
    """
    flavors = cat_rule.get("termination_flavors", {})
    if not flavors:
        return None, None, []

    text_lower = full_text.lower()
    lines = text_lower.split("\n")
    title_zone = "\n".join(lines[:10])
    preamble_zone = "\n".join(lines[:35])

    scores = {}
    evidence_map = {}

    for flavor_key, fdef in flavors.items():
        keywords = fdef.get("keywords", [])
        best = 0.0
        hits = []
        for kw in keywords:
            if kw in title_zone:
                w = 0.50
                hits.append(f"title: {kw}")
            elif kw in preamble_zone:
                w = 0.30
                hits.append(f"preamble: {kw}")
            elif kw in text_lower:
                w = 0.15
                hits.append(f"body: {kw}")
            else:
                continue
            if w > best:
                best = w
        if hits:
            bonus = min(len(hits) - 1, 3) * 0.05
            scores[flavor_key] = round(min(best + bonus, 1.0), 4)
            evidence_map[flavor_key] = hits

    if not scores:
        return None, None, []

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    winner_key = ranked[0][0]
    winner_def = flavors[winner_key]
    return winner_key, winner_def.get("label"), evidence_map.get(winner_key, [])


def get_expected_schedule_types(contract_type_value):
    """Return the expected schedule types for a contract type."""
    rules = _load_rules()
    categories = rules.get("categories", {})
    if not contract_type_value:
        return []
    cat = categories.get(contract_type_value.lower().strip())
    if not cat:
        return []
    return list(cat.get("expected_schedule_types", []))


def get_schema_locked_schedule_types():
    """Return the full list of schema-locked schedule type identifiers."""
    rules = _load_rules()
    return list(rules.get("schema_locked_schedule_types", []))


def get_schema_locked_subtypes():
    """Return the full list of schema-locked subtype labels."""
    rules = _load_rules()
    return list(rules.get("schema_locked_subtypes", []))


def get_schedule_type_priority():
    """Return the priority ordering for schedule types (most specific first)."""
    rules = _load_rules()
    return list(rules.get("schedule_type_priority", []))


def is_subtype_allowed(contract_type_value, subtype_value):
    """Check if a subtype is valid for the given contract category."""
    rules = _load_rules()
    categories = rules.get("categories", {})
    if not contract_type_value or not subtype_value:
        return True
    cat = categories.get(contract_type_value.lower().strip())
    if not cat:
        return True
    allowed = cat.get("subtypes_allowed", [])
    if not allowed:
        return True
    return subtype_value in allowed

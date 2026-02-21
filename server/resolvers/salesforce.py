"""
Salesforce Account Resolver — CSV-backed deterministic matching (v1)

Contract:
    resolve_account(query) ->
        {
            "classification": str,        # "matched" | "ambiguous" | "not_found"
            "score": float,               # 0.0–1.0 confidence in top match
            "candidates": list[dict],     # ranked candidate matches (max 5)
            "explanation": str,           # human-readable reasoning
            "provider": str,              # "cmg_csv_v1"
            "resolved": bool,             # whether a confident match was found
        }

Matching tiers (in order):
    1. Exact — normalized query matches a normalized name variant exactly → score 1.0
    2. Token overlap — Jaccard similarity on token sets → score = overlap ratio
    3. Edit distance — Levenshtein ratio on normalized strings → score = ratio

Thresholds:
    - EXACT_THRESHOLD:   1.0  (exact match)
    - FUZZY_THRESHOLD:   0.6  (minimum score to surface as candidate)
    - AMBIGUOUS_CUTOFF:  0.85 (below this, classification = "ambiguous")
    - MAX_CANDIDATES:    5

Stable ordering: candidates sorted by (-score, account_name) for determinism.
"""

import logging

from server.resolvers.account_index import get_index, normalize, tokenize

logger = logging.getLogger(__name__)

PROVIDER = "cmg_csv_v1"
FUZZY_THRESHOLD = 0.6
AMBIGUOUS_CUTOFF = 0.85
MAX_CANDIDATES = 5


def _edit_distance(a, b):
    la, lb = len(a), len(b)
    if la == 0:
        return lb
    if lb == 0:
        return la
    prev = list(range(lb + 1))
    for i in range(1, la + 1):
        cur = [i] + [0] * lb
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            cur[j] = min(cur[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
        prev = cur
    return prev[lb]


def _edit_ratio(a, b):
    if not a and not b:
        return 1.0
    max_len = max(len(a), len(b))
    if max_len == 0:
        return 1.0
    return 1.0 - (_edit_distance(a, b) / max_len)


def _jaccard(set_a, set_b):
    if not set_a or not set_b:
        return 0.0
    a = set(set_a)
    b = set(set_b)
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union > 0 else 0.0


def resolve_account(query):
    if not query or not str(query).strip():
        return {
            "classification": "not_found",
            "score": 0.0,
            "candidates": [],
            "explanation": "Empty query",
            "provider": PROVIDER,
            "resolved": False,
        }

    index = get_index()
    if not index.loaded:
        return {
            "classification": "not_found",
            "score": 0.0,
            "candidates": [],
            "explanation": "Account index not loaded",
            "provider": PROVIDER,
            "resolved": False,
        }

    norm_query = normalize(query)
    query_tokens = tokenize(query)
    scored = {}

    exact_matches = index.exact_lookup(query)
    for rec in exact_matches:
        key = rec.account_id or rec.display_name
        if key not in scored or scored[key][0] < 1.0:
            scored[key] = (1.0, "exact", rec)

    if not scored:
        for rec in index.all_records():
            best_score = 0.0
            best_tier = "none"

            for ts in rec.token_sets:
                j = _jaccard(query_tokens, ts)
                if j > best_score:
                    best_score = j
                    best_tier = "token_overlap"

            for nn in rec.normalized_names:
                r = _edit_ratio(norm_query, nn)
                if r > best_score:
                    best_score = r
                    best_tier = "edit_distance"

            if best_score >= FUZZY_THRESHOLD:
                key = rec.account_id or rec.display_name
                if key not in scored or scored[key][0] < best_score:
                    scored[key] = (best_score, best_tier, rec)

    candidates = []
    for key, (score, tier, rec) in scored.items():
        c = rec.to_candidate_dict()
        c["score"] = round(score, 4)
        c["match_tier"] = tier
        candidates.append(c)

    candidates.sort(key=lambda c: (-c["score"], c.get("account_name", "")))
    candidates = candidates[:MAX_CANDIDATES]

    if not candidates:
        return {
            "classification": "not_found",
            "score": 0.0,
            "candidates": [],
            "explanation": f"No matches found for '{query}'",
            "provider": PROVIDER,
            "resolved": False,
        }

    top_score = candidates[0]["score"]
    if top_score >= AMBIGUOUS_CUTOFF:
        classification = "matched"
        resolved = True
    else:
        classification = "ambiguous"
        resolved = False

    return {
        "classification": classification,
        "score": top_score,
        "candidates": candidates,
        "explanation": f"Top match: {candidates[0].get('account_name', '?')} (score={top_score}, tier={candidates[0].get('match_tier', '?')})",
        "provider": PROVIDER,
        "resolved": resolved,
    }


def is_resolver_enabled():
    return get_index().loaded


def get_resolver_status():
    index = get_index()
    return {
        "enabled": index.loaded,
        "provider": PROVIDER,
        "record_count": index.record_count if index.loaded else 0,
        "ready_for_integration": True,
        "live_api": False,
        "notes": "CSV-backed deterministic resolver using CMG_Account.csv",
    }


def resolve_entity(workspace_id, name, address=None):
    return resolve_account(name)

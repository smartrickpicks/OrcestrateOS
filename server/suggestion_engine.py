import re
import os
import json
import logging
import unicodedata
from difflib import SequenceMatcher

from rapidfuzz import fuzz as rf_fuzz
from rapidfuzz.distance import Levenshtein as rf_lev

logger = logging.getLogger(__name__)

NOISE_TOKENS = frozenset({
    "a", "an", "the",
    "and", "or", "of", "for", "to", "in", "on", "at", "by", "with", "from",
    "agreement", "schedule", "exhibit", "appendix", "annex", "attachment",
    "section", "clause", "paragraph", "item", "subitem",
    "hereby", "herein", "thereof", "whereas", "therein", "hereto",
    "shall", "per", "upon", "between", "under", "above",
    "this", "that", "are", "was", "will", "has", "have", "been", "not",
    "its", "into", "used", "can", "may", "when", "which", "also", "each",
    "such", "than", "any", "all", "but", "does", "other", "only", "how", "about",
})

KEEP_TOKENS = frozenset({
    "sync", "synch", "distribution", "digital", "masters", "recording",
    "royalty", "term", "territory", "recoupment", "fee", "advance",
    "records", "label", "music", "llc", "inc", "ltd", "limited",
    "corp", "co", "company", "group", "holdings",
    "field", "value", "stores", "record", "data", "set", "based",
})

ENTITY_TOKENS = frozenset({
    "records", "label", "music", "llc", "inc", "ltd", "limited",
    "corp", "co", "company", "group", "holdings",
})

ENTITY_CONTEXT_TOKENS = frozenset({
    "party", "label", "company", "records", "licensee", "licensor",
    "address", "entity", "inc", "llc",
})

DOMAIN_SIGNAL_TOKENS = frozenset({
    "sync", "synch", "distribution", "digital", "masters", "recording",
    "royalty", "term", "territory", "recoupment", "fee", "advance",
    "payment", "revenue", "rate", "amount", "cost", "price",
    "contract", "agreement", "effective", "expiration",
    "title", "artist", "album", "track", "isrc", "upc",
    "genre", "release", "catalog", "rights",
})

DOCUMENT_TYPE_KEYWORDS = {
    "financial": [
        "payment", "revenue", "royalty", "rate", "amount", "fee", "cost",
        "price", "billing", "invoice", "currency", "term", "frequency",
    ],
    "identity": [
        "account", "name", "contact", "email", "phone", "address",
        "city", "state", "country", "zip", "postal",
    ],
    "contract": [
        "contract", "agreement", "effective", "expiration", "start", "end",
        "status", "type", "category", "opportunity", "deal",
    ],
    "catalog": [
        "title", "artist", "album", "track", "isrc", "upc", "label",
        "genre", "release", "catalog", "territory", "rights",
    ],
}

_RE_SECTION_MARKER_ROMAN = re.compile(r'^\(?[ivxlcdm]+\)?\.?$', re.IGNORECASE)
_RE_SECTION_MARKER_NUM = re.compile(r'^\d+(\.\d+)+$')
_RE_SECTION_MARKER_ALPHA = re.compile(r'^\(?[a-z]\)?$', re.IGNORECASE)
_RE_PUNCT = re.compile(r'[^a-z0-9\s]')
_RE_MULTI_SPACE = re.compile(r'\s+')

_field_meta_cache = None


def _load_field_meta():
    global _field_meta_cache
    if _field_meta_cache is not None:
        return _field_meta_cache
    meta_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "rules", "rules_bundle", "field_meta.json",
    )
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _field_meta_cache = data
        logger.info("[SUGGEST] field_meta loaded: %d fields", len(data.get("fields", [])))
    except Exception as e:
        logger.warning("[SUGGEST] Could not load field_meta.json: %s", e)
        _field_meta_cache = {}
    return _field_meta_cache


def normalize_text(s):
    if not s:
        return "", []
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = _RE_PUNCT.sub(" ", s)
    s = _RE_MULTI_SPACE.sub(" ", s).strip()
    tokens = s.split()
    filtered = [t for t in tokens if t in KEEP_TOKENS or t not in NOISE_TOKENS]
    return " ".join(filtered), filtered


def normalize_field_name(name):
    s = name.strip()
    s = re.sub(r'__c$', '', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = s.replace('_', ' ').replace('-', ' ')
    s = _RE_MULTI_SPACE.sub(' ', s).strip().lower()
    return s


def _classify_suppression(text, tokens):
    reasons = []
    stripped = text.strip()
    if _RE_SECTION_MARKER_ROMAN.match(stripped):
        reasons.append("section_marker")
    if _RE_SECTION_MARKER_NUM.match(stripped):
        reasons.append("section_marker")
    if _RE_SECTION_MARKER_ALPHA.match(stripped):
        reasons.append("section_marker")
    if "http" in stripped.lower():
        reasons.append("url_heavy")
    url_signals = sum(1 for p in ["://", ".com", ".net", ".org"] if p in stripped.lower())
    slash_count = stripped.count("/")
    if url_signals + min(slash_count, 2) >= 2:
        reasons.append("url_heavy")
    if tokens:
        digit_chars = sum(1 for c in stripped if c.isdigit())
        total_chars = max(len(stripped), 1)
        if digit_chars / total_chars > 0.80 and len(tokens) <= 6:
            has_entity = any(t in ENTITY_TOKENS for t in tokens)
            if not has_entity:
                reasons.append("numeric_heavy")
    replacement_chars = stripped.count('\ufffd')
    control_chars = sum(1 for c in stripped if unicodedata.category(c).startswith('C') and c not in ('\n', '\r', '\t'))
    if (replacement_chars + control_chars) / max(len(stripped), 1) > 0.05:
        reasons.append("mojibake")
    if len(tokens) == 1 and len(tokens[0]) < 3 and tokens[0] not in KEEP_TOKENS:
        reasons.append("too_short")
    return list(set(reasons))


def _is_entity_eligible(tokens):
    if not tokens or len(tokens) < 2:
        return False
    if tokens[0].isdigit() and any(t in ENTITY_TOKENS for t in tokens):
        return True
    return False


def _lcs_length(a_tokens, b_tokens):
    m, n = len(a_tokens), len(b_tokens)
    if m == 0 or n == 0:
        return 0
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if a_tokens[i - 1] == b_tokens[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[m][n]


def _compute_exact_alias(candidate_norm, alias_map, entry):
    entry_id = entry.get("id") or entry.get("field_key", "")
    alias_hit = alias_map.get(candidate_norm)
    if alias_hit and alias_hit == entry_id:
        return 1.0
    fk_norm = entry.get("fk_normalized", "")
    if candidate_norm and candidate_norm == fk_norm:
        return 1.0
    norm_label = entry.get("normalized", "")
    if candidate_norm and candidate_norm == norm_label:
        return 1.0
    for alias_key, alias_tid in alias_map.items():
        if alias_tid == entry_id:
            alias_clean = normalize_field_name(alias_key)
            if candidate_norm == alias_clean:
                return 1.0
    return 0.0


def _find_alias_match_text(candidate_norm, alias_map, entry):
    entry_id = entry.get("id") or entry.get("field_key", "")
    alias_hit = alias_map.get(candidate_norm)
    if alias_hit and alias_hit == entry_id:
        return candidate_norm
    fk_norm = entry.get("fk_normalized", "")
    if candidate_norm and candidate_norm == fk_norm:
        return entry.get("field_key", fk_norm)
    norm_label = entry.get("normalized", "")
    if candidate_norm and candidate_norm == norm_label:
        return entry.get("label", norm_label)
    for alias_key, alias_tid in alias_map.items():
        if alias_tid == entry_id:
            alias_clean = normalize_field_name(alias_key)
            if candidate_norm == alias_clean:
                return alias_key
    return None


def _collect_all_aliases_for_entry(entry, alias_map, alias_originals=None):
    entry_id = entry.get("id") or entry.get("field_key", "")
    aliases = []
    for alias_key, alias_tid in alias_map.items():
        if alias_tid == entry_id:
            original = (alias_originals or {}).get(alias_key, alias_key)
            aliases.append(original)
    return aliases


def _find_best_edit_sim_pair(c_tokens, g_tokens_list, c_norm, g_norm):
    pairs = []
    if c_norm and g_norm:
        phrase_sim = rf_fuzz.token_sort_ratio(c_norm, g_norm) / 100.0
        pairs.append({
            "source_text": c_norm,
            "glossary_text": g_norm,
            "similarity": round(phrase_sim * 100),
            "type": "phrase",
        })
    if c_tokens and g_tokens_list:
        for gt in g_tokens_list:
            best_sim = 0.0
            best_st = ""
            for ct in c_tokens:
                sim = 1.0 - (rf_lev.normalized_distance(ct, gt))
                if sim > best_sim:
                    best_sim = sim
                    best_st = ct
            if best_sim >= 0.6:
                pairs.append({
                    "source_text": best_st,
                    "glossary_text": gt,
                    "similarity": round(best_sim * 100),
                    "type": "token",
                })
    pairs.sort(key=lambda p: -p["similarity"])
    return pairs[:5]


def _compute_tok_overlap(c_set, a_or_t_set):
    if not a_or_t_set:
        return 0.0
    return len(c_set & a_or_t_set) / max(1, len(a_or_t_set))


def _compute_ordered_overlap(c_tokens, a_or_t_tokens):
    if not c_tokens or not a_or_t_tokens:
        return 0.0
    lcs = _lcs_length(c_tokens, a_or_t_tokens)
    return lcs / max(1, len(a_or_t_tokens))


def _compute_edit_sim(c_tokens, a_or_t_tokens, c_norm, a_or_t_norm):
    if not c_norm or not a_or_t_norm:
        return 0.0
    phrase_sim = rf_fuzz.token_sort_ratio(c_norm, a_or_t_norm) / 100.0
    if not c_tokens or not a_or_t_tokens:
        return phrase_sim
    token_sims = []
    for at in a_or_t_tokens:
        best = 0.0
        for ct in c_tokens:
            sim = 1.0 - (rf_lev.normalized_distance(ct, at))
            if sim > best:
                best = sim
        token_sims.append(best)
    avg_token_sim = sum(token_sims) / max(1, len(token_sims))
    return max(phrase_sim, avg_token_sim)


def _compute_first_token_bonus(c_tokens, a_or_t_tokens):
    if len(a_or_t_tokens) < 2 or not c_tokens:
        return 0.0
    return 1.0 if c_tokens[0] == a_or_t_tokens[0] else 0.0


def _compute_context_bonus(candidate_tokens_set, all_candidate_tokens_on_line):
    if not all_candidate_tokens_on_line:
        return 0.0
    other_tokens = all_candidate_tokens_on_line - candidate_tokens_set
    if other_tokens & DOMAIN_SIGNAL_TOKENS:
        return 1.0
    return 0.0


def _classify_confidence(score_pct):
    if score_pct >= 80:
        return "HIGH"
    elif score_pct >= 60:
        return "MEDIUM"
    elif score_pct >= 40:
        return "LOW"
    else:
        return "HIDDEN"


def _generate_reason_chips(exact_alias, tok_overlap, ordered_overlap, edit_sim, first_token, context_bonus, entity_eligible):
    chips = []
    if exact_alias == 1.0:
        chips.append("Exact alias")
    if tok_overlap >= 0.50:
        chips.append("Token overlap")
    if ordered_overlap >= 0.50:
        chips.append("Ordered match")
    if edit_sim >= 0.80:
        chips.append("Edit-sim")
    elif edit_sim >= 0.75:
        chips.append("Edit-sim")
    if context_bonus == 1.0:
        chips.append("Context boost")
    if entity_eligible:
        chips.append("Entity rule")
    if first_token == 1.0 and "Exact alias" not in chips:
        chips.append("First-token anchor")
    return chips


def _determine_match_method(exact_alias, tok_overlap, edit_sim, ordered_overlap):
    if exact_alias == 1.0:
        return "alias_exact"
    if ordered_overlap >= 0.5 and edit_sim >= 0.6:
        return "phrase_fuzzy"
    if tok_overlap >= 0.3:
        return "token_overlap"
    if edit_sim >= 0.5:
        return "phrase_fuzzy"
    return "none"


def _build_glossary_index(field_meta_fields, glossary_term_list):
    index = []
    seen_keys = set()

    for fm in field_meta_fields:
        fk = fm.get("field_key", "")
        if not fk or fk in seen_keys:
            continue
        seen_keys.add(fk)
        label = fm.get("field_label", "") or fk
        defn = fm.get("definition", "") or ""
        category = fm.get("category", "") or ""
        sheet = fm.get("sheet", "") or ""
        opts = fm.get("options") or []

        label_norm, label_tokens = normalize_text(label)
        fk_norm, fk_tokens = normalize_text(fk)
        _, def_tokens = normalize_text(defn)
        top_def_tokens = sorted(set(def_tokens), key=lambda w: len(w), reverse=True)[:12]
        opt_tokens = []
        for opt in opts[:20]:
            _, ot = normalize_text(str(opt))
            opt_tokens.extend(ot)

        all_tokens = list(dict.fromkeys(label_tokens + fk_tokens))
        keyword_set = set(all_tokens) | set(top_def_tokens) | set(opt_tokens)

        cat_kws_set = set()
        for cat_name, cat_words in DOCUMENT_TYPE_KEYWORDS.items():
            check_set = set(label_tokens) | set(fk_tokens)
            if any(cw in check_set for cw in cat_words):
                cat_kws_set.update(cat_words)
        keyword_set |= cat_kws_set

        glossary_id = None
        for gt in glossary_term_list:
            gt_fk_norm, _ = normalize_text(gt["field_key"])
            if gt["field_key"] == fk or gt_fk_norm == fk_norm:
                glossary_id = gt["id"]
                break

        normalized_label = normalize_field_name(label)
        normalized_fk = normalize_field_name(fk)

        index.append({
            "id": glossary_id or fk,
            "field_key": fk,
            "label": label,
            "normalized": normalized_label,
            "fk_normalized": normalized_fk,
            "definition": defn[:200],
            "category": category,
            "tokens_list": all_tokens,
            "tokens_set": set(all_tokens),
            "keyword_set": keyword_set,
            "domain_keywords": cat_kws_set,
        })

    for gt in glossary_term_list:
        if gt["field_key"] not in seen_keys:
            seen_keys.add(gt["field_key"])
            fk = gt["field_key"]
            label = gt.get("display_name") or fk
            _, label_tokens = normalize_text(label)
            _, fk_tokens = normalize_text(fk)
            all_tokens = list(dict.fromkeys(label_tokens + fk_tokens))

            normalized_label = normalize_field_name(label)
            normalized_fk = normalize_field_name(fk)

            index.append({
                "id": gt["id"],
                "field_key": fk,
                "label": label,
                "normalized": normalized_label,
                "fk_normalized": normalized_fk,
                "definition": "",
                "category": gt.get("category", ""),
                "tokens_list": all_tokens,
                "tokens_set": set(all_tokens),
                "keyword_set": set(all_tokens),
                "domain_keywords": set(),
            })

    return index


def _score_candidate_against_entry(
    c_norm, c_tokens, c_token_set, entry, alias_map,
    context_tokens=None, entity_eligible=False, entity_context=False,
    alias_originals=None,
):
    g_tokens_list = entry["tokens_list"]
    g_tokens_set = entry["tokens_set"]
    if not g_tokens_set:
        return None

    g_norm = entry["normalized"]
    g_fk_norm = entry.get("fk_normalized", "")
    best_g_norm = g_norm if len(g_norm) >= len(g_fk_norm) else g_fk_norm

    exact_alias = _compute_exact_alias(c_norm, alias_map, entry)
    tok_overlap = _compute_tok_overlap(c_token_set, g_tokens_set)
    ordered_overlap = _compute_ordered_overlap(c_tokens, g_tokens_list)
    edit_sim = _compute_edit_sim(c_tokens, g_tokens_list, c_norm, best_g_norm)
    first_token = _compute_first_token_bonus(c_tokens, g_tokens_list)
    context_bonus = _compute_context_bonus(c_token_set, context_tokens) if context_tokens else 0.0

    S = (
        0.45 * exact_alias +
        0.20 * tok_overlap +
        0.12 * ordered_overlap +
        0.18 * edit_sim +
        0.03 * first_token +
        0.02 * context_bonus
    )

    if len(c_tokens) == 1 and len(g_tokens_list) == 1 and edit_sim >= 0.75:
        short_boost = edit_sim * 0.72
        S = max(S, short_boost)

    if entity_eligible and entity_context:
        S = min(1.0, S + 0.05)

    confidence_pct = round(100 * S)

    if exact_alias == 1.0 and confidence_pct < 80:
        confidence_pct = max(confidence_pct, 80)

    confidence_bucket = _classify_confidence(confidence_pct)
    reason_chips = _generate_reason_chips(
        exact_alias, tok_overlap, ordered_overlap, edit_sim,
        first_token, context_bonus, entity_eligible,
    )
    match_method = _determine_match_method(exact_alias, tok_overlap, edit_sim, ordered_overlap)

    matched_tokens = sorted(c_token_set & g_tokens_set)

    alias_text_norm = _find_alias_match_text(c_norm, alias_map, entry) if exact_alias == 1.0 else None
    alias_text = (alias_originals or {}).get(alias_text_norm, alias_text_norm) if alias_text_norm else None
    all_aliases = _collect_all_aliases_for_entry(entry, alias_map, alias_originals)
    overlapping_tokens = sorted(c_token_set & g_tokens_set)
    glossary_tokens = sorted(g_tokens_set)
    context_overlap = sorted(c_token_set & set(context_tokens)) if context_tokens else []
    edit_pairs = _find_best_edit_sim_pair(c_tokens, g_tokens_list, c_norm, best_g_norm) if edit_sim > 0.0 else []
    first_token_match = c_tokens[0] if (first_token == 1.0 and c_tokens) else None
    domain_kws_hit = sorted(c_token_set & entry.get("domain_keywords", set()))

    trigger_summary = []
    if exact_alias == 1.0 and alias_text:
        trigger_summary.append('Alias "' + str(alias_text) + '" exactly matches this glossary term')
    elif edit_pairs:
        top_pair = edit_pairs[0]
        trigger_summary.append(
            '"' + str(top_pair["source_text"]) + '" is ' + str(top_pair["similarity"]) +
            '% similar to "' + str(top_pair["glossary_text"]) + '"'
        )
    if overlapping_tokens:
        trigger_summary.append("Shared tokens: " + ", ".join(overlapping_tokens))
    if entity_eligible:
        trigger_summary.append("Entity-eligible (numeric-leading name pattern)")

    return {
        "glossary_term_id": entry["id"],
        "glossary_field_key": entry["field_key"],
        "label": entry["label"],
        "confidence_score": round(S, 4),
        "confidence_pct": confidence_pct,
        "confidence_bucket": confidence_bucket,
        "match_method": match_method,
        "reason_labels": reason_chips,
        "_components": {
            "exact_alias": round(exact_alias, 4),
            "tok_overlap": round(tok_overlap, 4),
            "ordered_overlap": round(ordered_overlap, 4),
            "edit_sim": round(edit_sim, 4),
            "first_token_bonus": round(first_token, 4),
            "context_bonus": round(context_bonus, 4),
        },
        "_match_context": {
            "alias_matched": alias_text,
            "all_aliases": all_aliases,
            "glossary_label": entry["label"],
            "glossary_field_key": entry["field_key"],
            "glossary_definition": entry.get("definition", ""),
            "glossary_category": entry.get("category", ""),
            "glossary_tokens": glossary_tokens,
            "source_normalized": c_norm,
            "glossary_normalized": best_g_norm,
            "overlapping_tokens": overlapping_tokens,
            "context_tokens_matched": context_overlap,
            "edit_sim_pairs": edit_pairs,
            "first_token_match": first_token_match,
            "domain_keywords_hit": domain_kws_hit,
            "trigger_summary": trigger_summary,
        },
        "matched_tokens": matched_tokens,
    }


def _match_source_against_glossary(source_field, glossary_index, alias_map, context_tokens=None, alias_originals=None):
    source_norm = normalize_field_name(source_field)
    _, source_tokens = normalize_text(source_field)
    source_token_set = set(source_tokens)

    suppression_reasons = _classify_suppression(source_field, source_tokens)
    entity_eligible = _is_entity_eligible(source_tokens)
    if entity_eligible and "numeric_heavy" in suppression_reasons:
        suppression_reasons.remove("numeric_heavy")

    entity_context = False
    if entity_eligible and context_tokens:
        entity_context = bool(context_tokens & ENTITY_CONTEXT_TOKENS)

    all_candidates = []
    for entry in glossary_index:
        result = _score_candidate_against_entry(
            source_norm, source_tokens, source_token_set, entry, alias_map,
            context_tokens=context_tokens,
            entity_eligible=entity_eligible,
            entity_context=entity_context,
            alias_originals=alias_originals,
        )
        if result:
            all_candidates.append(result)

    all_candidates.sort(key=lambda c: (
        -c["confidence_pct"],
        -(c["_components"]["exact_alias"]),
        -(c["_components"]["tok_overlap"]),
        -(c["_components"]["edit_sim"]),
        c["glossary_field_key"],
    ))

    seen_keys = set()
    deduped = []
    for c in all_candidates:
        if c["glossary_field_key"] not in seen_keys:
            seen_keys.add(c["glossary_field_key"])
            deduped.append(c)

    is_suppressed = len(suppression_reasons) > 0
    top = deduped[:3]

    if top:
        best = top[0]
        method_label = best["match_method"]
        if best["confidence_bucket"] == "HIDDEN":
            method_label = "none"

        return {
            "source_field": source_field,
            "suggested_term_id": best["glossary_term_id"],
            "suggested_label": best["label"],
            "glossary_term_id": best["glossary_term_id"],
            "glossary_field_key": best["glossary_field_key"],
            "matched_text": source_field,
            "confidence_score": best["confidence_score"],
            "confidence_pct": best["confidence_pct"],
            "confidence_bucket": best["confidence_bucket"],
            "match_score": best["confidence_score"],
            "match_method": method_label,
            "match_reason": ", ".join(best["reason_labels"]) if best["reason_labels"] else best["match_method"],
            "reason_labels": best["reason_labels"],
            "suppressed": is_suppressed,
            "suppression_reasons": suppression_reasons,
            "entity_eligible": entity_eligible,
            "candidates": [
                {
                    "term_id": c["glossary_term_id"],
                    "field_key": c["glossary_field_key"],
                    "label": c["label"],
                    "score": c["confidence_score"],
                    "confidence_pct": c["confidence_pct"],
                    "confidence_bucket": c["confidence_bucket"],
                    "method": c["match_method"],
                    "reason_labels": c["reason_labels"],
                    "components": c["_components"],
                    "match_context": c.get("_match_context"),
                }
                for c in top
            ],
            "_match_context": best.get("_match_context"),
            "_meta": {
                "source_normalized": source_norm,
                "source_tokens": source_tokens,
                "matched_keywords": best.get("matched_tokens", []),
                "reason": ", ".join(best["reason_labels"]) if best["reason_labels"] else "no reason",
                "components": best.get("_components"),
            },
        }

    return {
        "source_field": source_field,
        "suggested_term_id": None,
        "suggested_label": None,
        "glossary_term_id": None,
        "glossary_field_key": None,
        "matched_text": source_field,
        "confidence_score": 0.0,
        "confidence_pct": 0,
        "confidence_bucket": "HIDDEN",
        "match_score": 0.0,
        "match_method": "none",
        "match_reason": "No matching canonical field found",
        "reason_labels": [],
        "suppressed": is_suppressed,
        "suppression_reasons": suppression_reasons,
        "entity_eligible": entity_eligible,
        "candidates": [],
        "_meta": {
            "source_normalized": source_norm,
            "source_tokens": source_tokens,
            "matched_keywords": [],
            "reason": "No match",
            "components": None,
        },
    }


def _build_glossary_term_list(terms_rows):
    term_list = []
    for t in terms_rows:
        entry = {
            "id": t[0],
            "field_key": t[1],
            "display_name": t[2] or t[1],
            "category": t[3] or "",
            "normalized": normalize_field_name(t[1]),
        }
        term_list.append(entry)
    return term_list


def generate_suggestions(cur, workspace_id, document_id):
    cur.execute(
        "SELECT metadata FROM documents WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL",
        (document_id, workspace_id),
    )
    doc_row = cur.fetchone()
    if not doc_row:
        return [], {"run_mode": "db_doc_not_found", "error": "Document not found in database"}

    doc_meta = doc_row[0] if doc_row[0] else {}
    source_fields = doc_meta.get("column_headers", [])

    if not source_fields:
        logger.info("[SUGGEST] No column_headers in document %s metadata", document_id)
        return [], {"run_mode": "db_backed", "error": "No column_headers in document metadata"}

    return _run_suggestions(cur, workspace_id, source_fields, run_mode="db_backed")


def generate_suggestions_local(cur, workspace_id, source_fields):
    if not source_fields:
        return [], {"run_mode": "local_fallback", "error": "No source_fields provided"}
    return _run_suggestions(cur, workspace_id, source_fields, run_mode="local_fallback")


def _run_suggestions(cur, workspace_id, source_fields, run_mode="db_backed"):
    field_meta = _load_field_meta()
    field_meta_fields = field_meta.get("fields", []) if field_meta else []
    has_field_meta = len(field_meta_fields) > 0

    cur.execute(
        """SELECT id, field_key, display_name, category
           FROM glossary_terms
           WHERE workspace_id = %s AND deleted_at IS NULL""",
        (workspace_id,),
    )
    terms = cur.fetchall()
    glossary_term_list = _build_glossary_term_list(terms) if terms else []

    glossary_index = _build_glossary_index(field_meta_fields, glossary_term_list)

    cur.execute(
        """SELECT normalized_alias, term_id, alias
           FROM glossary_aliases
           WHERE workspace_id = %s AND deleted_at IS NULL""",
        (workspace_id,),
    )
    alias_map = {}
    alias_originals = {}
    for row in cur.fetchall():
        alias_map[row[0]] = row[1]
        alias_originals[row[0]] = row[2] if len(row) > 2 and row[2] else row[0]

    all_source_tokens = set()
    for sf in source_fields:
        _, toks = normalize_text(sf)
        all_source_tokens.update(toks)

    suggestions = []
    suppressed_list = []
    counts = {
        "alias_exact": 0, "phrase_fuzzy": 0,
        "token_overlap": 0, "none": 0,
    }
    bucket_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "HIDDEN": 0}

    for source_field in source_fields:
        result = _match_source_against_glossary(
            source_field, glossary_index, alias_map,
            context_tokens=all_source_tokens,
            alias_originals=alias_originals,
        )

        method = result.get("match_method", "none")
        counts[method] = counts.get(method, 0) + 1
        bucket = result.get("confidence_bucket", "HIDDEN")
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1

        if result.get("suppressed"):
            suppressed_list.append(result)
        else:
            suggestions.append(result)

    diagnostics = {
        "run_mode": run_mode,
        "has_field_meta": has_field_meta,
        "field_meta_count": len(field_meta_fields),
        "glossary_index_size": len(glossary_index),
        "glossary_terms_count": len(glossary_term_list),
        "aliases_count": len(alias_map),
        "total_headers": len(source_fields),
        "suppressed_count": len(suppressed_list),
        "counts": counts,
        "confidence_buckets": bucket_counts,
    }

    total_matched = sum(v for k, v in counts.items() if k != "none")
    logger.info(
        "[SUGGEST] run_complete: mode=%s, fields=%d, matched=%d, unmatched=%d, suppressed=%d, buckets=%s",
        run_mode, len(source_fields), total_matched, counts.get("none", 0),
        len(suppressed_list), bucket_counts,
    )

    return suggestions, diagnostics, suppressed_list

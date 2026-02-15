import re
import os
import json
import logging
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

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

_STOP_WORDS = frozenset({
    "the", "this", "that", "and", "for", "from", "with", "are", "was",
    "will", "has", "have", "been", "not", "its", "into", "used", "can",
    "may", "when", "which", "also", "each", "such", "than", "any",
    "all", "but", "does", "field", "value", "stores", "record",
    "data", "set", "based", "other", "only", "how", "about",
    "shall", "per", "upon", "between", "under", "above",
    "herein", "thereof", "hereby", "therein", "hereto",
})

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


def _extract_tokens(text):
    if not text:
        return []
    words = re.findall(r'[a-z]{2,}', text.lower())
    return [w for w in words if w not in _STOP_WORDS and len(w) > 1]


def _extract_token_set(text):
    return set(_extract_tokens(text))


def normalize_field_name(name):
    s = name.strip()
    s = re.sub(r'__c$', '', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = s.replace('_', ' ').replace('-', ' ')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


def _char_similarity(a, b):
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def _ordered_phrase_score(source_tokens_list, glossary_tokens_list):
    if not source_tokens_list or not glossary_tokens_list:
        return 0.0
    g_ptr = 0
    matched_in_order = 0
    for st in source_tokens_list:
        if g_ptr < len(glossary_tokens_list) and st == glossary_tokens_list[g_ptr]:
            matched_in_order += 1
            g_ptr += 1
    if matched_in_order == 0:
        return 0.0
    if matched_in_order == len(glossary_tokens_list):
        return 1.0
    return min(matched_in_order / max(len(glossary_tokens_list), 1) * 0.8, 0.5)


def _compute_alias_boost(source_norm, alias_map, glossary_entry):
    entry_id = glossary_entry.get("id") or glossary_entry.get("field_key", "")
    alias_hit = alias_map.get(source_norm)
    if alias_hit and alias_hit == entry_id:
        return 1.0, "alias_exact"
    alias_norm = normalize_field_name(source_norm)
    for alias_key, alias_tid in alias_map.items():
        if alias_tid == entry_id and alias_norm == alias_key:
            return 0.6, "alias_normalized"
    return 0.0, None


def _generate_reason_labels(source_tokens_set, glossary_tokens_list, source_norm, glossary_norm, char_sim, ordered_score, alias_boost_val):
    labels = []
    if alias_boost_val >= 1.0:
        labels.append("ALIAS_EXACT")
    elif alias_boost_val >= 0.6:
        labels.append("ALIAS_NORMALIZED")
    if glossary_tokens_list and source_tokens_set:
        if glossary_tokens_list[0] in source_tokens_set:
            labels.append("FIRST_TOKEN_MATCH")
    if ordered_score >= 0.8:
        labels.append("ORDERED_TOKENS")
    elif ordered_score >= 0.3:
        labels.append("PARTIAL_ORDER")
    if char_sim >= 0.85:
        labels.append("EDIT_DISTANCE_NEAR")
    elif char_sim >= 0.7:
        labels.append("EDIT_DISTANCE_MODERATE")
    g_set = set(glossary_tokens_list) if glossary_tokens_list else set()
    overlap = source_tokens_set & g_set
    if len(overlap) >= 3:
        labels.append("MULTI_TOKEN_OVERLAP")
    elif len(overlap) >= 1:
        labels.append("TOKEN_OVERLAP")
    return labels


def _classify_confidence(score):
    if score >= 0.85:
        return "HIGH"
    elif score >= 0.70:
        return "MEDIUM"
    elif score >= 0.55:
        return "LOW"
    else:
        return "HIDDEN"


def _determine_match_method(alias_boost_val, token_overlap_score, char_sim, ordered_score):
    if alias_boost_val >= 1.0:
        return "alias_exact"
    if alias_boost_val >= 0.6:
        return "alias_normalized"
    if ordered_score >= 0.5 and char_sim >= 0.6:
        return "phrase_fuzzy"
    if token_overlap_score > 0:
        return "token_overlap"
    if char_sim >= 0.5:
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

        normalized = normalize_field_name(label)
        fk_normalized = normalize_field_name(fk)

        label_tokens = _extract_tokens(label)
        fk_tokens = _extract_tokens(fk)
        def_tokens = _extract_tokens(defn)
        top_def_tokens = sorted(set(def_tokens), key=lambda w: len(w), reverse=True)[:12]
        opt_tokens = []
        for opt in opts[:20]:
            opt_tokens.extend(_extract_tokens(str(opt)))

        all_tokens = list(dict.fromkeys(label_tokens + fk_tokens))
        keyword_set = set(all_tokens) | set(top_def_tokens) | set(opt_tokens)

        cat_kws_set = set()
        for cat_name, cat_words in DOCUMENT_TYPE_KEYWORDS.items():
            check_set = set(label_tokens) | set(fk_tokens) | _extract_token_set(sheet)
            if any(cw in check_set for cw in cat_words):
                cat_kws_set.update(cat_words)
        keyword_set |= cat_kws_set

        glossary_id = None
        for gt in glossary_term_list:
            if gt["field_key"] == fk or gt["normalized"] == fk_normalized:
                glossary_id = gt["id"]
                break

        index.append({
            "id": glossary_id or fk,
            "field_key": fk,
            "label": label,
            "normalized": normalized,
            "fk_normalized": fk_normalized,
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
            normalized = normalize_field_name(label)
            fk_normalized = normalize_field_name(fk)
            tokens = _extract_tokens(label)
            fk_toks = _extract_tokens(fk)
            all_tokens = list(dict.fromkeys(tokens + fk_toks))

            index.append({
                "id": gt["id"],
                "field_key": fk,
                "label": label,
                "normalized": normalized,
                "fk_normalized": fk_normalized,
                "definition": "",
                "category": gt.get("category", ""),
                "tokens_list": all_tokens,
                "tokens_set": set(all_tokens),
                "keyword_set": set(all_tokens),
                "domain_keywords": set(),
            })

    return index


def _score_glossary_candidate(source_norm, source_tokens_list, source_tokens_set, entry, alias_map):
    g_tokens_list = entry["tokens_list"]
    g_tokens_set = entry["tokens_set"]

    if not g_tokens_set:
        return None

    matched = source_tokens_set & g_tokens_set
    token_overlap_score = len(matched) / len(g_tokens_set) if g_tokens_set else 0.0

    char_sim = _char_similarity(source_norm, entry["normalized"])
    char_sim_fk = _char_similarity(source_norm, entry["fk_normalized"])
    char_similarity_score = max(char_sim, char_sim_fk)

    ordered_score = _ordered_phrase_score(source_tokens_list, g_tokens_list)

    alias_boost_val, alias_type = _compute_alias_boost(source_norm, alias_map, entry)

    final_score = (
        0.45 * token_overlap_score +
        0.30 * char_similarity_score +
        0.15 * ordered_score +
        0.10 * alias_boost_val
    )
    final_score = round(min(final_score, 1.0), 4)

    reason_labels = _generate_reason_labels(
        source_tokens_set, g_tokens_list, source_norm,
        entry["normalized"], char_similarity_score, ordered_score, alias_boost_val,
    )

    match_method = _determine_match_method(alias_boost_val, token_overlap_score, char_similarity_score, ordered_score)
    confidence_bucket = _classify_confidence(final_score)

    return {
        "glossary_term_id": entry["id"],
        "glossary_field_key": entry["field_key"],
        "label": entry["label"],
        "confidence_score": final_score,
        "confidence_pct": int(round(final_score * 100)),
        "confidence_bucket": confidence_bucket,
        "match_method": match_method,
        "reason_labels": reason_labels,
        "_components": {
            "token_overlap": round(token_overlap_score, 4),
            "char_similarity": round(char_similarity_score, 4),
            "ordered_phrase": round(ordered_score, 4),
            "alias_boost": round(alias_boost_val, 4),
        },
        "matched_tokens": sorted(matched),
    }


def _match_source_against_glossary(source_field, glossary_index, alias_map):
    source_norm = normalize_field_name(source_field)
    source_tokens_list = _extract_tokens(source_field)
    source_tokens_set = set(source_tokens_list)

    all_candidates = []

    for entry in glossary_index:
        result = _score_glossary_candidate(
            source_norm, source_tokens_list, source_tokens_set, entry, alias_map,
        )
        if result:
            all_candidates.append(result)

    all_candidates.sort(key=lambda c: (-c["confidence_score"], c["glossary_field_key"]))

    seen_keys = set()
    deduped = []
    for c in all_candidates:
        if c["glossary_field_key"] not in seen_keys:
            seen_keys.add(c["glossary_field_key"])
            deduped.append(c)

    top = deduped[:5]

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
                }
                for c in top
            ],
            "_meta": {
                "source_normalized": source_norm,
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
        "candidates": [],
        "_meta": {
            "source_normalized": source_norm,
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
        """SELECT normalized_alias, term_id
           FROM glossary_aliases
           WHERE workspace_id = %s AND deleted_at IS NULL""",
        (workspace_id,),
    )
    alias_map = {}
    for row in cur.fetchall():
        alias_map[row[0]] = row[1]

    suggestions = []
    counts = {
        "alias_exact": 0, "alias_normalized": 0,
        "phrase_fuzzy": 0, "token_overlap": 0, "none": 0,
    }
    bucket_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "HIDDEN": 0}

    for source_field in source_fields:
        result = _match_source_against_glossary(source_field, glossary_index, alias_map)

        method = result.get("match_method", "none")
        counts[method] = counts.get(method, 0) + 1
        bucket = result.get("confidence_bucket", "HIDDEN")
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        suggestions.append(result)

    diagnostics = {
        "run_mode": run_mode,
        "has_field_meta": has_field_meta,
        "field_meta_count": len(field_meta_fields),
        "glossary_index_size": len(glossary_index),
        "glossary_terms_count": len(glossary_term_list),
        "aliases_count": len(alias_map),
        "total_headers": len(source_fields),
        "counts": counts,
        "confidence_buckets": bucket_counts,
    }

    total_matched = sum(v for k, v in counts.items() if k != "none")
    logger.info(
        "[SUGGEST] run_complete: mode=%s, fields=%d, matched=%d, unmatched=%d, buckets=%s",
        run_mode, len(source_fields), total_matched, counts.get("none", 0),
        bucket_counts,
    )

    return suggestions, diagnostics

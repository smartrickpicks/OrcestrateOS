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
        return set()
    words = re.findall(r'[a-z]{2,}', text.lower())
    return {w for w in words if w not in _STOP_WORDS and len(w) > 1}


def _make_ngrams(tokens, min_n=1, max_n=4):
    token_list = sorted(tokens)
    ngrams = set()
    for n in range(min_n, min(max_n + 1, len(token_list) + 1)):
        for i in range(len(token_list) - n + 1):
            ngrams.add(" ".join(token_list[i:i + n]))
    return ngrams


def normalize_field_name(name):
    s = name.strip()
    s = re.sub(r'__c$', '', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = s.replace('_', ' ').replace('-', ' ')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


def _levenshtein_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


def _build_field_meta_index(field_meta_fields):
    index = []
    for fm in field_meta_fields:
        fk = fm.get("field_key", "")
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
        top_def_tokens = set(sorted(def_tokens, key=lambda w: len(w), reverse=True)[:15])
        opt_tokens = set()
        for opt in opts[:20]:
            opt_tokens.update(_extract_tokens(str(opt)))

        all_tokens = label_tokens | fk_tokens
        keyword_tokens = all_tokens | top_def_tokens | opt_tokens

        cat_kws_set = set()
        for cat_name, cat_words in DOCUMENT_TYPE_KEYWORDS.items():
            cat_tokens_check = label_tokens | fk_tokens | _extract_tokens(sheet)
            if any(cw in cat_tokens_check for cw in cat_words):
                cat_kws_set.update(cat_words)

        keyword_tokens |= cat_kws_set

        label_ngrams = _make_ngrams(label_tokens, 1, 3)
        fk_ngrams = _make_ngrams(fk_tokens, 1, 3)

        index.append({
            "field_key": fk,
            "label": label,
            "normalized": normalized,
            "fk_normalized": fk_normalized,
            "definition": defn[:200],
            "category": category,
            "sheet": sheet,
            "label_tokens": label_tokens,
            "keyword_tokens": keyword_tokens,
            "label_ngrams": label_ngrams | fk_ngrams,
            "domain_keywords": cat_kws_set,
        })
    return index


def _score_candidate(source_text, source_norm, source_tokens, fm_entry, alias_map):
    candidates = []

    alias_hit = alias_map.get(source_norm)
    if alias_hit and alias_hit == fm_entry["field_key"]:
        return {
            "field_key": fm_entry["field_key"],
            "label": fm_entry["label"],
            "score": 1.0,
            "method": "alias_exact",
            "reason": "Exact alias match",
            "matched_tokens": [],
        }

    if source_norm == fm_entry["normalized"] or source_norm == fm_entry["fk_normalized"]:
        return {
            "field_key": fm_entry["field_key"],
            "label": fm_entry["label"],
            "score": 1.0,
            "method": "exact",
            "reason": "Exact label match",
            "matched_tokens": [],
        }

    fuzzy_label = _levenshtein_ratio(source_norm, fm_entry["normalized"])
    fuzzy_fk = _levenshtein_ratio(source_norm, fm_entry["fk_normalized"])
    fuzzy_best = max(fuzzy_label, fuzzy_fk)
    if fuzzy_best >= 0.7:
        return {
            "field_key": fm_entry["field_key"],
            "label": fm_entry["label"],
            "score": round(fuzzy_best, 3),
            "method": "fuzzy",
            "reason": "Fuzzy match (%.0f%% similar)" % (fuzzy_best * 100),
            "matched_tokens": [],
        }

    if not source_tokens:
        return None

    source_ngrams = _make_ngrams(source_tokens, 1, 3)
    ngram_overlap = source_ngrams & fm_entry["label_ngrams"]
    if ngram_overlap:
        max_ngram_len = max(len(ng.split()) for ng in ngram_overlap)
        overlap_score = min(0.3 + max_ngram_len * 0.15 + len(ngram_overlap) * 0.05, 0.85)
        matched = sorted(ngram_overlap, key=lambda x: len(x), reverse=True)[:5]
        return {
            "field_key": fm_entry["field_key"],
            "label": fm_entry["label"],
            "score": round(overlap_score, 3),
            "method": "normalized_phrase",
            "reason": "Phrase overlap: %s" % ", ".join(matched[:3]),
            "matched_tokens": matched,
        }

    kw_overlap = source_tokens & fm_entry["keyword_tokens"]
    if len(kw_overlap) >= 1:
        base = len(kw_overlap) * 0.12
        domain_hit = source_tokens & fm_entry.get("domain_keywords", set())
        boost = len(domain_hit) * 0.08
        score = min(base + boost, 0.6)
        if score >= 0.15:
            matched = sorted(kw_overlap)
            return {
                "field_key": fm_entry["field_key"],
                "label": fm_entry["label"],
                "score": round(score, 3),
                "method": "token_overlap",
                "reason": "Token overlap: %s" % ", ".join(matched[:5]),
                "matched_tokens": matched[:5],
            }

    return None


def _match_source_against_index(source_field, fm_index, alias_map, glossary_term_list):
    source_norm = normalize_field_name(source_field)
    source_tokens = _extract_tokens(source_field)

    all_candidates = []

    for fm_entry in fm_index:
        result = _score_candidate(source_field, source_norm, source_tokens, fm_entry, alias_map)
        if result:
            all_candidates.append(result)

    for gt in glossary_term_list:
        if source_norm == gt["normalized"]:
            all_candidates.append({
                "field_key": gt["field_key"],
                "label": gt.get("display_name", gt["field_key"]),
                "score": 1.0,
                "method": "glossary_exact",
                "reason": "Glossary term exact match",
                "matched_tokens": [],
            })
        else:
            fuzzy = _levenshtein_ratio(source_norm, gt["normalized"])
            if fuzzy >= 0.65:
                all_candidates.append({
                    "field_key": gt["field_key"],
                    "label": gt.get("display_name", gt["field_key"]),
                    "score": round(fuzzy, 3),
                    "method": "glossary_fuzzy",
                    "reason": "Glossary fuzzy (%.0f%%)" % (fuzzy * 100),
                    "matched_tokens": [],
                })

    all_candidates.sort(key=lambda c: c["score"], reverse=True)

    seen_keys = set()
    deduped = []
    for c in all_candidates:
        if c["field_key"] not in seen_keys:
            seen_keys.add(c["field_key"])
            deduped.append(c)

    top = deduped[:5]

    if top:
        best = top[0]
        return {
            "source_field": source_field,
            "suggested_term_id": best["field_key"],
            "suggested_label": best["label"],
            "match_score": best["score"],
            "match_method": best["method"],
            "match_reason": best["reason"],
            "candidates": [
                {
                    "term_id": c["field_key"],
                    "label": c["label"],
                    "score": c["score"],
                    "method": c["method"],
                    "reason": c["reason"],
                }
                for c in top
            ],
            "_meta": {
                "source_normalized": source_norm,
                "matched_keywords": best.get("matched_tokens", []),
                "reason": best["reason"],
            },
        }

    return {
        "source_field": source_field,
        "suggested_term_id": None,
        "suggested_label": None,
        "match_score": 0.0,
        "match_method": "none",
        "match_reason": "No matching canonical field found",
        "candidates": [],
        "_meta": {
            "source_normalized": source_norm,
            "matched_keywords": [],
            "reason": "No match",
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


def _build_term_keywords(term_entry, field_meta_fields):
    tokens = set()
    label = term_entry.get("display_name") or term_entry.get("field_key", "")
    tokens.update(_extract_tokens(label))
    tokens.update(_extract_tokens(term_entry.get("field_key", "")))
    category = term_entry.get("category", "")
    cat_kws = DOCUMENT_TYPE_KEYWORDS.get(category, [])
    tokens.update(cat_kws)
    if field_meta_fields:
        fk_norm = normalize_field_name(term_entry.get("field_key", ""))
        for fm in field_meta_fields:
            fm_norm = normalize_field_name(fm.get("field_key", ""))
            if fm_norm == fk_norm:
                tokens.update(_extract_tokens(fm.get("field_label", "")))
                defn = fm.get("definition", "")
                if defn:
                    def_tokens = _extract_tokens(defn)
                    top_def = sorted(def_tokens, key=lambda w: len(w), reverse=True)[:12]
                    tokens.update(top_def)
                opts = fm.get("options") or []
                for opt in opts[:20]:
                    tokens.update(_extract_tokens(str(opt)))
                break
    return tokens


def _build_term_list_with_keywords(terms_rows, field_meta_fields):
    term_list = []
    for t in terms_rows:
        entry = {
            "id": t[0],
            "field_key": t[1],
            "display_name": t[2] or t[1],
            "category": t[3] or "",
            "normalized": normalize_field_name(t[1]),
        }
        entry["_keywords"] = _build_term_keywords(entry, field_meta_fields)
        term_list.append(entry)
    return term_list


def _keyword_score_v2(source_norm, term_keywords):
    if not term_keywords:
        return 0.0
    source_words = set(source_norm.split())
    if not source_words:
        return 0.0
    matched = sum(1 for kw in term_keywords if kw in source_words)
    overlap = len(source_words & term_keywords)
    base = matched * 0.08
    boost = overlap * 0.18
    return min(base + boost, 0.6)


def _match_source_field(source_norm, term_list, alias_map):
    alias_term_id = alias_map.get(source_norm)
    if alias_term_id:
        term_match = next((t for t in term_list if t["id"] == alias_term_id), None)
        if term_match:
            return {
                "suggested_term_id": term_match["id"],
                "match_score": 1.0,
                "match_method": "exact",
                "candidates": [{"term_id": term_match["id"], "score": 1.0, "method": "exact"}],
                "_matched_keywords": [],
            }

    candidates = []
    for term in term_list:
        if source_norm == term["normalized"]:
            candidates.append({
                "term_id": term["id"],
                "score": 1.0,
                "method": "exact",
            })
            continue

        fuzzy_score = _levenshtein_ratio(source_norm, term["normalized"])
        if fuzzy_score >= 0.6:
            candidates.append({
                "term_id": term["id"],
                "score": round(fuzzy_score, 3),
                "method": "fuzzy",
            })
            continue

        kw_score = _keyword_score_v2(source_norm, term.get("_keywords", set()))
        if kw_score >= 0.2:
            source_words = set(source_norm.split())
            matched_kws = sorted(source_words & term.get("_keywords", set()))
            candidates.append({
                "term_id": term["id"],
                "score": round(kw_score, 3),
                "method": "keyword",
                "_matched_keywords": matched_kws,
            })

    candidates.sort(key=lambda c: c["score"], reverse=True)
    top3 = candidates[:3]

    if top3:
        best = top3[0]
        matched_kws = best.pop("_matched_keywords", [])
        for c in top3:
            c.pop("_matched_keywords", None)
        return {
            "suggested_term_id": best["term_id"],
            "match_score": best["score"],
            "match_method": best["method"],
            "candidates": top3,
            "_matched_keywords": matched_kws,
        }
    return {
        "suggested_term_id": None,
        "match_score": 0.0,
        "match_method": "none",
        "candidates": [],
        "_matched_keywords": [],
    }


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

    fm_index = _build_field_meta_index(field_meta_fields) if has_field_meta else []

    cur.execute(
        """SELECT id, field_key, display_name, category
           FROM glossary_terms
           WHERE workspace_id = %s AND deleted_at IS NULL""",
        (workspace_id,),
    )
    terms = cur.fetchall()
    glossary_term_list = _build_glossary_term_list(terms) if terms else []

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
    counts = {"exact": 0, "alias_exact": 0, "fuzzy": 0, "normalized_phrase": 0,
              "token_overlap": 0, "glossary_exact": 0, "glossary_fuzzy": 0, "none": 0}

    for source_field in source_fields:
        if fm_index:
            result = _match_source_against_index(source_field, fm_index, alias_map, glossary_term_list)
        else:
            source_norm = normalize_field_name(source_field)
            old_result = _match_source_field(source_norm, _build_term_list_with_keywords(terms or [], field_meta_fields), alias_map)
            matched_kws = old_result.pop("_matched_keywords", [])
            result = {
                "source_field": source_field,
                "suggested_term_id": old_result["suggested_term_id"],
                "suggested_label": None,
                "match_score": old_result["match_score"],
                "match_method": old_result["match_method"],
                "match_reason": old_result["match_method"],
                "candidates": old_result["candidates"],
                "_meta": {
                    "source_normalized": source_norm,
                    "matched_keywords": matched_kws,
                    "reason": old_result["match_method"],
                },
            }

        method = result.get("match_method", "none")
        counts[method] = counts.get(method, 0) + 1
        suggestions.append(result)

    diagnostics = {
        "run_mode": run_mode,
        "has_field_meta": has_field_meta,
        "field_meta_count": len(field_meta_fields),
        "fm_index_size": len(fm_index),
        "glossary_terms_count": len(glossary_term_list),
        "aliases_count": len(alias_map),
        "total_headers": len(source_fields),
        "counts": counts,
    }

    total_matched = sum(v for k, v in counts.items() if k != "none")
    logger.info(
        "[SUGGEST] run_complete: mode=%s, fields=%d, matched=%d, unmatched=%d, methods=%s",
        run_mode, len(source_fields), total_matched, counts.get("none", 0),
        {k: v for k, v in counts.items() if v > 0},
    )

    return suggestions, diagnostics

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
    stop = {
        "the", "this", "that", "and", "for", "from", "with", "are", "was",
        "will", "has", "have", "been", "not", "its", "into", "used", "can",
        "may", "when", "which", "also", "each", "such", "than", "any",
        "all", "but", "does", "field", "value", "stores", "record",
        "data", "set", "based", "other", "only", "how", "about",
    }
    return {w for w in words if w not in stop and len(w) > 1}


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


def normalize_field_name(name):
    s = name.strip()
    s = re.sub(r'__c$', '', s)
    s = re.sub(r'([a-z])([A-Z])', r'\1 \2', s)
    s = s.replace('_', ' ').replace('-', ' ')
    s = re.sub(r'\s+', ' ', s).strip().lower()
    return s


def _levenshtein_ratio(a, b):
    return SequenceMatcher(None, a, b).ratio()


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
    if not terms:
        logger.info("[SUGGEST] No glossary terms found for workspace %s", workspace_id)
        return [], {
            "run_mode": run_mode,
            "has_field_meta": has_field_meta,
            "error": "No glossary terms found",
        }

    term_list = _build_term_list_with_keywords(terms, field_meta_fields)

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
    counts = {"exact": 0, "fuzzy": 0, "keyword": 0, "none": 0}

    for source_field in source_fields:
        source_norm = normalize_field_name(source_field)
        result = _match_source_field(source_norm, term_list, alias_map)
        matched_kws = result.pop("_matched_keywords", [])
        result["source_field"] = source_field
        result["_meta"] = {
            "source_normalized": source_norm,
            "matched_keywords": matched_kws,
        }
        suggestions.append(result)
        counts[result["match_method"]] = counts.get(result["match_method"], 0) + 1

    diagnostics = {
        "run_mode": run_mode,
        "has_field_meta": has_field_meta,
        "field_meta_count": len(field_meta_fields),
        "glossary_terms_count": len(term_list),
        "aliases_count": len(alias_map),
        "total_headers": len(source_fields),
        "counts": counts,
    }

    logger.info(
        "[SUGGEST] run_complete: mode=%s, fields=%d, exact=%d, fuzzy=%d, keyword=%d, none=%d",
        run_mode, len(source_fields),
        counts["exact"], counts["fuzzy"], counts["keyword"], counts["none"],
    )

    return suggestions, diagnostics

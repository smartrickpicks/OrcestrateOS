"""
Deterministic Preflight Engine for Orchestrate OS.

Locked thresholds (P1E):
  Page mode:
    SEARCHABLE: chars_on_page >= 50 AND image_coverage_ratio <= 0.70
    SCANNED:    chars_on_page < 50 AND image_coverage_ratio >= 0.30
    else MIXED

  Doc mode aggregation:
    SEARCHABLE: >= 80% pages are SEARCHABLE
    SCANNED:    >= 80% pages are SCANNED
    else MIXED

  Gate (locked policy — single authoritative path):
    RED:    replacement_char_ratio > 0.05 OR control_char_ratio > 0.03
    YELLOW: not RED AND (doc_mode == MIXED OR avg_chars_per_page < 30 OR >80% pages have <10 chars)
    GREEN:  otherwise

  mojibake_ratio is a display-only metric; it feeds INTO replacement_char_ratio
  but does NOT independently trigger RED or YELLOW.
"""
import hashlib
import logging
import re

logger = logging.getLogger(__name__)

PAGE_CHARS_MIN_SEARCHABLE = 50
PAGE_IMAGE_MAX_SEARCHABLE = 0.70
PAGE_CHARS_MAX_SCANNED = 50
PAGE_IMAGE_MIN_SCANNED = 0.30

DOC_MODE_SUPERMAJORITY = 0.80

GATE_RED_REPLACEMENT_RATIO = 0.05
GATE_RED_CONTROL_RATIO = 0.03
GATE_YELLOW_AVG_CHARS = 30
GATE_YELLOW_SPARSE_RATIO = 0.80
GATE_YELLOW_SPARSE_CHARS = 10

MAX_CORRUPTION_SAMPLES = 20
SAMPLE_SNIPPET_RADIUS = 40


def classify_page(chars_on_page, image_coverage_ratio):
    if chars_on_page >= PAGE_CHARS_MIN_SEARCHABLE and image_coverage_ratio <= PAGE_IMAGE_MAX_SEARCHABLE:
        return "SEARCHABLE"
    if chars_on_page < PAGE_CHARS_MAX_SCANNED and image_coverage_ratio >= PAGE_IMAGE_MIN_SCANNED:
        return "SCANNED"
    return "MIXED"


def classify_document(page_modes):
    if not page_modes:
        return "MIXED"
    total = len(page_modes)
    searchable_count = sum(1 for m in page_modes if m == "SEARCHABLE")
    scanned_count = sum(1 for m in page_modes if m == "SCANNED")
    if searchable_count / total >= DOC_MODE_SUPERMAJORITY:
        return "SEARCHABLE"
    if scanned_count / total >= DOC_MODE_SUPERMAJORITY:
        return "SCANNED"
    return "MIXED"


_MOJIBAKE_SEQUENCES = [
    '\u00c3\u00a9', '\u00c3\u00a0', '\u00c3\u00a8', '\u00c3\u00b1',
    '\u00c3\u00bc', '\u00c3\u00b6', '\u00c3\u00a4', '\u00c3\u00ad',
    '\u00c3\u00b3', '\u00c3\u00ba', '\u00c3\u0089', '\u00c3\u0096',
    '\u00c3\u009c', '\u00c2\u00a0', '\u00c2\u00ab', '\u00c2\u00bb',
    '\u00c2\u00b7', '\u00e2\u0080\u0099', '\u00e2\u0080\u009c',
    '\u00e2\u0080\u009d', '\u00e2\u0080\u0093', '\u00e2\u0080\u0094',
    '\u00e2\u0080\u00a2', '\u00e2\u0080\u00a6', '\u00ef\u00bf\u00bd',
    '\u00ef\u00ac\u0081', '\u00ef\u00ac\u0082',
]

_MOJIBAKE_RE = re.compile(
    r'[\u00c0-\u00c3][\u0080-\u00bf]'
    r'|[\u00e2][\u0080-\u0082][\u0080-\u00bf]'
    r'|[\u00ef][\u00ac\u00bf][\u0080-\u00bf]'
    r'|\ufffe|\ufeff'
    r'|\ufffd'
)

_TOFU_RANGES = re.compile(
    r'[\u2400-\u243f]'
    r'|[\ue000-\uf8ff]'
    r'|[\U000f0000-\U000fffff]'
)

_LATIN_EXT_CLUSTER_RE = re.compile(
    r'[\u0100-\u024F\u0300-\u036F]{3,}'
)

_REPLACEMENT_CHAR_RE = re.compile(r'\ufffd')

_CONTROL_CHAR_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


def compute_text_metrics(pages_text):
    total_chars = 0
    replacement_chars = 0
    control_chars = 0
    mojibake_chars = 0
    for text in pages_text:
        total_chars += len(text)
        replacement_chars += text.count('\ufffd')
        mojibake_hits = _MOJIBAKE_RE.findall(text)
        mojibake_chars += len(mojibake_hits)
        tofu_hits = _TOFU_RANGES.findall(text)
        mojibake_chars += len(tofu_hits)
        for seq in _MOJIBAKE_SEQUENCES:
            mojibake_chars += text.count(seq)
        for cluster in _LATIN_EXT_CLUSTER_RE.finditer(text):
            mojibake_chars += len(cluster.group())
        for ch in text:
            code = ord(ch)
            if code < 32 and code not in (9, 10, 13):
                control_chars += 1
    if total_chars == 0:
        return 0.0, 0.0, 0.0
    replacement_chars += mojibake_chars
    return replacement_chars / total_chars, control_chars / total_chars, mojibake_chars / total_chars


def extract_corruption_samples(pages_text, max_samples=MAX_CORRUPTION_SAMPLES):
    samples = []
    for page_idx, text in enumerate(pages_text):
        if len(samples) >= max_samples:
            break
        page_num = page_idx + 1
        for m in _REPLACEMENT_CHAR_RE.finditer(text):
            if len(samples) >= max_samples:
                break
            start = max(0, m.start() - SAMPLE_SNIPPET_RADIUS)
            end = min(len(text), m.end() + SAMPLE_SNIPPET_RADIUS)
            samples.append({
                "page": page_num,
                "issue_type": "replacement_char",
                "char_start": m.start(),
                "char_end": m.end(),
                "snippet": text[start:end],
            })
        for m in _CONTROL_CHAR_RE.finditer(text):
            if len(samples) >= max_samples:
                break
            start = max(0, m.start() - SAMPLE_SNIPPET_RADIUS)
            end = min(len(text), m.end() + SAMPLE_SNIPPET_RADIUS)
            samples.append({
                "page": page_num,
                "issue_type": "control_char",
                "char_start": m.start(),
                "char_end": m.end(),
                "snippet": text[start:end],
            })
        for m in _LATIN_EXT_CLUSTER_RE.finditer(text):
            if len(samples) >= max_samples:
                break
            start = max(0, m.start() - SAMPLE_SNIPPET_RADIUS)
            end = min(len(text), m.end() + SAMPLE_SNIPPET_RADIUS)
            samples.append({
                "page": page_num,
                "issue_type": "latin_ext_cluster",
                "char_start": m.start(),
                "char_end": m.end(),
                "snippet": text[start:end],
            })
        for m in _MOJIBAKE_RE.finditer(text):
            if len(samples) >= max_samples:
                break
            start = max(0, m.start() - SAMPLE_SNIPPET_RADIUS)
            end = min(len(text), m.end() + SAMPLE_SNIPPET_RADIUS)
            samples.append({
                "page": page_num,
                "issue_type": "mojibake_sequence",
                "char_start": m.start(),
                "char_end": m.end(),
                "snippet": text[start:end],
            })
    return samples


def compute_gate(doc_mode, replacement_char_ratio, control_char_ratio,
                 avg_chars_per_page, page_char_counts):
    reasons = []
    trace = []

    r1 = replacement_char_ratio > GATE_RED_REPLACEMENT_RATIO
    trace.append({
        "rule": "replacement_char_ratio > %.2f" % GATE_RED_REPLACEMENT_RATIO,
        "value": round(replacement_char_ratio, 6),
        "threshold": GATE_RED_REPLACEMENT_RATIO,
        "result": "FAIL" if r1 else "PASS",
        "level": "RED",
    })
    if r1:
        reasons.append("replacement_char_ratio_exceeded:%.4f>%.4f" % (replacement_char_ratio, GATE_RED_REPLACEMENT_RATIO))

    r2 = control_char_ratio > GATE_RED_CONTROL_RATIO
    trace.append({
        "rule": "control_char_ratio > %.2f" % GATE_RED_CONTROL_RATIO,
        "value": round(control_char_ratio, 6),
        "threshold": GATE_RED_CONTROL_RATIO,
        "result": "FAIL" if r2 else "PASS",
        "level": "RED",
    })
    if r2:
        reasons.append("control_char_ratio_exceeded:%.4f>%.4f" % (control_char_ratio, GATE_RED_CONTROL_RATIO))

    if reasons:
        return "RED", reasons, trace

    y1 = doc_mode == "MIXED"
    trace.append({
        "rule": "doc_mode == MIXED",
        "value": doc_mode,
        "threshold": "MIXED",
        "result": "FAIL" if y1 else "PASS",
        "level": "YELLOW",
    })
    if y1:
        reasons.append("doc_mode_mixed")

    y2 = avg_chars_per_page < GATE_YELLOW_AVG_CHARS
    trace.append({
        "rule": "avg_chars_per_page < %d" % GATE_YELLOW_AVG_CHARS,
        "value": round(avg_chars_per_page, 2),
        "threshold": GATE_YELLOW_AVG_CHARS,
        "result": "FAIL" if y2 else "PASS",
        "level": "YELLOW",
    })
    if y2:
        reasons.append("avg_chars_per_page_low:%.1f<%d" % (avg_chars_per_page, GATE_YELLOW_AVG_CHARS))

    sparse_ratio = 0.0
    if page_char_counts:
        sparse_pages = sum(1 for c in page_char_counts if c < GATE_YELLOW_SPARSE_CHARS)
        sparse_ratio = sparse_pages / len(page_char_counts)
    y3 = sparse_ratio > GATE_YELLOW_SPARSE_RATIO
    trace.append({
        "rule": ">%.0f%% pages have <%d chars" % (GATE_YELLOW_SPARSE_RATIO * 100, GATE_YELLOW_SPARSE_CHARS),
        "value": round(sparse_ratio, 4),
        "threshold": GATE_YELLOW_SPARSE_RATIO,
        "result": "FAIL" if y3 else "PASS",
        "level": "YELLOW",
    })
    if y3:
        reasons.append("sparse_pages_exceeded:%.2f>%.2f" % (sparse_ratio, GATE_YELLOW_SPARSE_RATIO))

    if reasons:
        return "YELLOW", reasons, trace

    return "GREEN", ["all_checks_passed"], trace


def derive_cache_identity(workspace_id, file_url):
    raw = "%s|%s" % (workspace_id or "", file_url or "")
    h = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return "doc_derived_%s" % h


_GARBAGE_RE = re.compile(
    r'^[\d\.\(\)\-\s]+$'
    r'|^[ivxlcdm]+[\.\)]\s*$'
    r'|^§\s*\d'
    r'|^\d+\.\d+'
    r'|^https?://'
    r'|^www\.'
    r'|@[a-zA-Z0-9]'
    r'|^\W+$',
    re.IGNORECASE,
)


def _is_low_signal(text):
    if _GARBAGE_RE.search(text):
        return True
    alpha = sum(1 for c in text if c.isalpha())
    if len(text) > 0 and alpha / len(text) < 0.4:
        return True
    if len(text) < 3:
        return True
    return False


def _extract_candidate_headers(full_text):
    raw_candidates = set()
    lines = full_text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or len(line) > 80:
            continue
        if len(line) < 3:
            continue
        words = line.split()
        if len(words) <= 5:
            cleaned = re.sub(r'[:\-\s]+$', '', line).strip()
            if cleaned and len(cleaned) >= 3:
                raw_candidates.add(cleaned)
        parts = re.split(r'\t|  {2,}|\|', line)
        for part in parts:
            part = part.strip()
            if 3 <= len(part) <= 60 and len(part.split()) <= 5:
                raw_candidates.add(part)

    filtered = [c for c in raw_candidates if not _is_low_signal(c)]
    low_signal = [c for c in raw_candidates if _is_low_signal(c)]

    result = sorted(filtered)[:200]
    return result, sorted(low_signal)[:50]


def run_preflight(pages_data):
    if not pages_data:
        return {
            "doc_mode": "MIXED",
            "gate_color": "RED",
            "gate_reasons": ["no_pages"],
            "decision_trace": [],
            "corruption_samples": [],
            "page_classifications": [],
            "metrics": {},
        }

    page_modes = []
    page_char_counts = []
    pages_text = []
    page_results = []

    for p in pages_data:
        text = p.get("text", "")
        char_count = p.get("char_count", len(text))
        image_ratio = p.get("image_coverage_ratio", 0.0)
        mode = classify_page(char_count, image_ratio)
        page_modes.append(mode)
        page_char_counts.append(char_count)
        pages_text.append(text)
        page_results.append({
            "page": p.get("page", 0),
            "mode": mode,
            "char_count": char_count,
            "image_coverage_ratio": image_ratio,
        })

    doc_mode = classify_document(page_modes)
    replacement_ratio, control_ratio, mojibake_ratio = compute_text_metrics(pages_text)
    total_chars = sum(page_char_counts)
    avg_chars = total_chars / len(page_char_counts) if page_char_counts else 0.0

    gate_color, gate_reasons, decision_trace = compute_gate(
        doc_mode, replacement_ratio, control_ratio,
        avg_chars, page_char_counts
    )

    corruption_samples = extract_corruption_samples(pages_text)

    full_text = "\n".join(pages_text)
    extracted_headers, low_signal_headers = _extract_candidate_headers(full_text)

    sf_match = _run_salesforce_match(extracted_headers, full_text)

    return {
        "doc_mode": doc_mode,
        "gate_color": gate_color,
        "gate_reasons": gate_reasons,
        "decision_trace": decision_trace,
        "corruption_samples": corruption_samples,
        "salesforce_match": sf_match,
        "page_classifications": page_results,
        "extracted_text": full_text[:50000],
        "extracted_headers": extracted_headers,
        "low_signal_headers": low_signal_headers,
        "metrics": {
            "total_pages": len(pages_data),
            "total_chars": total_chars,
            "avg_chars_per_page": round(avg_chars, 2),
            "replacement_char_ratio": round(replacement_ratio, 6),
            "control_char_ratio": round(control_ratio, 6),
            "mojibake_ratio": round(mojibake_ratio, 6),
            "searchable_pages": sum(1 for m in page_modes if m == "SEARCHABLE"),
            "scanned_pages": sum(1 for m in page_modes if m == "SCANNED"),
            "mixed_pages": sum(1 for m in page_modes if m == "MIXED"),
        },
    }


_SF_ENTITY_HINTS = [
    "account name", "account", "client name", "client", "company name",
    "company", "legal name", "legal entity", "entity name", "entity",
    "artist", "artist name", "vendor", "vendor name", "counterparty",
    "customer", "customer name", "payee", "payee name", "licensee",
    "licensor", "party name",
]

_SF_STOP_LABELS = {
    "account name", "account name:", "account number", "account number:",
    "account", "account:", "client name", "client name:", "client",
    "client:", "company name", "company name:", "company", "company:",
    "vendor name", "vendor name:", "vendor", "vendor:", "artist name",
    "artist name:", "artist", "artist:", "entity name", "entity name:",
    "entity", "entity:", "legal name", "legal name:", "legal entity",
    "legal entity:", "counterparty", "counterparty:", "customer name",
    "customer name:", "customer", "customer:", "payee name", "payee name:",
    "payee", "payee:", "licensee", "licensee:", "licensor", "licensor:",
    "party name", "party name:", "payments/accounting", "n/a", "na",
    "none", "tbd", "unknown",
}

_LABEL_VALUE_RE = re.compile(
    r'(?:account\s*name|account|client\s*name|client|company\s*name|company'
    r'|legal\s*name|legal\s*entity|entity\s*name|entity|artist\s*name|artist'
    r'|vendor\s*name|vendor|counterparty|customer\s*name|customer'
    r'|payee\s*name|payee|licensee|licensor|party\s*name)'
    r'\s*[:;\-–—]\s*(.+)',
    re.IGNORECASE,
)


def _normalize_candidate(text):
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[;:,]+$', '', text).strip()
    return text


def extract_account_candidates(full_text, extracted_headers):
    """Extract actual account-name values from body text, not labels.

    Priority:
      a) Value-after-label patterns ("Account Name: 1888 Records" → "1888 Records")
      b) Standalone entity-like lines
      c) Fallback to headers only if no values found

    Returns deduplicated, normalized list of candidate strings.
    """
    value_candidates = []
    seen_lower = set()

    lines = full_text.split("\n") if full_text else []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = _LABEL_VALUE_RE.search(line)
        if m:
            val = _normalize_candidate(m.group(1))
            if val and len(val) >= 2 and val.lower() not in _SF_STOP_LABELS:
                if val.lower() not in seen_lower:
                    seen_lower.add(val.lower())
                    value_candidates.append(val)

    if value_candidates:
        return value_candidates

    header_values = []
    for h in extracted_headers:
        normed = _normalize_candidate(h)
        if normed and normed.lower() not in _SF_STOP_LABELS and normed.lower() not in seen_lower:
            h_lower = normed.lower().strip()
            is_label = False
            for hint in _SF_ENTITY_HINTS:
                if h_lower == hint or h_lower == hint + ":":
                    is_label = True
                    break
            if not is_label:
                seen_lower.add(normed.lower())
                header_values.append(normed)

    if header_values:
        return header_values[:10]

    fallback = []
    for h in extracted_headers[:5]:
        normed = _normalize_candidate(h)
        if normed and normed.lower() not in seen_lower:
            seen_lower.add(normed.lower())
            fallback.append(normed)
    return fallback


def _run_salesforce_match(extracted_headers, full_text=""):
    """Run Salesforce account resolver on extracted candidate values.

    Extracts actual account-name values from body text (label:value patterns)
    rather than matching raw header labels against the resolver.

    Returns a list of match result dicts shaped for the matrix renderer:
        [{ source_field, suggested_label, match_method, match_score,
           confidence_pct, match_status, classification, candidates, explanation }]
    """
    try:
        from server.resolvers.salesforce import resolve_account, is_resolver_enabled
    except ImportError:
        logger.debug("[PREFLIGHT-SF] salesforce resolver not available")
        return []

    if not is_resolver_enabled():
        logger.debug("[PREFLIGHT-SF] resolver not enabled (index not loaded)")
        return []

    candidates = extract_account_candidates(full_text, extracted_headers)
    if not candidates:
        return []

    results = []
    for candidate in candidates:
        res = resolve_account(candidate)
        top_name = ""
        if res.get("candidates"):
            top_name = res["candidates"][0].get("account_name", "")

        score = res.get("score", 0.0)
        pct = round(score * 100)

        if res["classification"] == "matched":
            match_status = "match"
            match_method = res["candidates"][0].get("match_tier", "exact") if res.get("candidates") else "exact"
        elif res["classification"] == "ambiguous":
            match_status = "review"
            match_method = res["candidates"][0].get("match_tier", "fuzzy") if res.get("candidates") else "fuzzy"
        else:
            match_status = "no-match"
            match_method = "none"

        results.append({
            "source_field": candidate,
            "suggested_label": top_name or "\u2014",
            "match_method": match_method,
            "match_score": score,
            "confidence_pct": pct,
            "match_status": match_status,
            "classification": res["classification"],
            "candidates": res.get("candidates", []),
            "explanation": res.get("explanation", ""),
            "provider": res.get("provider", ""),
        })

    results.sort(key=lambda r: (
        0 if r["match_status"] == "review" else 1 if r["match_status"] == "no-match" else 2,
        -r["confidence_pct"],
        r["source_field"].lower(),
    ))

    return results

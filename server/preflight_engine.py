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

from server.preflight_rules import classify_contract, get_expected_schedule_types, get_schedule_type_priority

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


# ---------------------------------------------------------------------------
# Track-listing / schedule-of-songs section detection
# ---------------------------------------------------------------------------
_TRACK_SECTION_HEADER_RE = re.compile(
    r'(?:track\s*list|song\s*list|list\s+of\s+(?:songs|tracks|recordings|masters)'
    r'|schedule\s+of\s+(?:songs|tracks|recordings|masters)'
    r'|annexure|appendix|exhibit)\s*',
    re.IGNORECASE,
)
_NUMBERED_LINE_RE = re.compile(
    r'^\s*(?:\d{1,4}[\.\)\-]|\d{1,4}\s+[A-Z])',
)
_SR_NO_HEADER_RE = re.compile(
    r'sr\.?\s*no|s\.?\s*no|song\s*title|track\s*(?:title|name)|artist\s*name',
    re.IGNORECASE,
)


def _detect_track_listing_lines(full_text):
    """Return a set of line indices that belong to track-listing / song-schedule sections.

    Detection strategy:
    1. Look for section headers (Track List, Annexure, etc.) or table headers (Sr. No., Song Title)
    2. After a header, consume consecutive short numbered/titled lines as track entries
    3. Also detect dense runs of numbered short lines even without an explicit header
    """
    if not full_text:
        return set()

    lines = full_text.split("\n")
    track_lines = set()

    # --- Strategy 1: Header-triggered sections ---
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if _TRACK_SECTION_HEADER_RE.search(line) or _SR_NO_HEADER_RE.search(line):
            # Mark the header line itself
            track_lines.add(i)
            # Consume following lines that look like track entries
            j = i + 1
            consecutive_short = 0
            while j < len(lines):
                tl = lines[j].strip()
                if not tl:
                    # blank line — tolerate up to 2 consecutive blanks
                    if j + 1 < len(lines) and not lines[j + 1].strip():
                        if j + 2 < len(lines) and not lines[j + 2].strip():
                            break  # 3+ blanks = section ended
                    j += 1
                    continue
                if len(tl) > 120:
                    break  # long prose line = new section
                # Break on contract section headers (e.g. "SECTION 2: Payment")
                if re.match(r'^\s*(?:SECTION|ARTICLE|CLAUSE|PART|CHAPTER)\s+\d', tl, re.IGNORECASE):
                    break
                # Break on ALL-CAPS headers that signal a new contract section
                if tl == tl.upper() and len(tl) >= 5 and not _NUMBERED_LINE_RE.match(tl):
                    break
                words = tl.split()
                if len(words) <= 8 or _NUMBERED_LINE_RE.match(tl):
                    track_lines.add(j)
                    consecutive_short += 1
                    j += 1
                else:
                    # non-track line — break if we already have entries
                    if consecutive_short >= 3:
                        break
                    j += 1
            i = j
        else:
            i += 1

    # --- Strategy 2: Dense numbered-line runs without explicit header ---
    run_start = None
    run_count = 0
    for i, raw_line in enumerate(lines):
        line = raw_line.strip()
        if _NUMBERED_LINE_RE.match(line) and len(line) <= 80 and len(line.split()) <= 8:
            if run_start is None:
                run_start = i
            run_count += 1
        else:
            if run_count >= 8:
                for k in range(run_start, run_start + run_count):
                    track_lines.add(k)
            run_start = None
            run_count = 0
    if run_count >= 8:
        for k in range(run_start, run_start + run_count):
            track_lines.add(k)

    return track_lines


def _strip_track_listing_text(full_text):
    """Return full_text with track-listing lines blanked out."""
    if not full_text:
        return full_text
    track_indices = _detect_track_listing_lines(full_text)
    if not track_indices:
        return full_text
    lines = full_text.split("\n")
    for idx in track_indices:
        if idx < len(lines):
            lines[idx] = ""
    return "\n".join(lines)


def _extract_candidate_headers(full_text):
    raw_candidates = set()
    lines = full_text.split("\n")
    track_lines = _detect_track_listing_lines(full_text)
    for line_idx, raw_line in enumerate(lines):
        if line_idx in track_lines:
            continue
        line = raw_line.strip()
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
    resolution_story = build_resolution_story(sf_match, full_text)
    opportunity_spine = build_opportunity_spine(full_text, resolution_story)
    schedule_structure = build_schedule_structure(full_text, resolution_story, opportunity_spine)

    contract_type_val = _opp_check_value(opportunity_spine, "OPP_CONTRACT_TYPE")
    contract_classification = classify_contract(contract_type_val, full_text)

    financials_readiness = build_financials_readiness(full_text, opportunity_spine)
    addons_readiness = build_addons_readiness(full_text, opportunity_spine)
    health_score = compute_preflight_health_score(
        gate_color, opportunity_spine, schedule_structure,
        financials_readiness, addons_readiness, resolution_story,
    )

    return {
        "doc_mode": doc_mode,
        "gate_color": gate_color,
        "gate_reasons": gate_reasons,
        "decision_trace": decision_trace,
        "corruption_samples": corruption_samples,
        "salesforce_match": sf_match,
        "resolution_story": resolution_story,
        "opportunity_spine": opportunity_spine,
        "schedule_structure": schedule_structure,
        "contract_classification": contract_classification,
        "financials_readiness": financials_readiness,
        "addons_readiness": addons_readiness,
        "health_score": health_score,
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

_STRICT_LABEL_VALUE_RE = re.compile(
    r'^\s*(?:Account\s*Name(?:_c|__c)?|Company\s*Name(?:_c|__c)?'
    r'|Artist\s*Name(?:\s*\(pka\s+or\s+dba\))?|Legal\s*Name)'
    r'\s*[:\-]\s*(.+?)\s*$',
    re.IGNORECASE,
)

_PROSE_START_WORDS = {"record", "records", "agreement", "whereas", "means", "term", "party", "parties", "shall", "includes", "including"}

_PROSE_FRAGMENTS = [
    "means every form of",
    "this agreement",
    "hereof",
    "whereas",
    "herein",
    "hereunder",
    "pursuant to",
    "in connection with",
    "notwithstanding",
]

_GENERIC_SINGLE_TOKENS = {"record", "records", "account", "accounts", "company", "companies", "artist", "artists", "vendor", "vendors", "name", "entity"}

_HARD_DENYLIST = {
    "distribution", "trademark", "delay", "image", "mean",
    "prosecute", "secrets", "master", "territory", "term",
    "schedule", "exhibit", "section", "clause", "paragraph",
    "article", "appendix", "annex", "recital", "preamble",
    "definitions", "notices", "whereas", "agreement", "contract",
    "license", "rights", "obligations", "representations",
    "warranties", "indemnification", "confidential",
    "termination", "governing", "jurisdiction", "arbitration",
    "force majeure", "amendment", "waiver", "assignment",
    "counterparts", "entire agreement", "severability",
    "survival", "headings", "notices", "miscellaneous",
}


_BORNE_PHRASE_PATTERNS = [
    "to be borne by",
    "borne by the",
    "shall be borne by",
    "costs borne by",
    "expenses borne by",
]


def _is_borne_in_verb_context(candidate, full_text):
    if not full_text or candidate.lower().strip() != "borne":
        return False
    text_lower = full_text.lower()
    for phrase in _BORNE_PHRASE_PATTERNS:
        if phrase in text_lower:
            return True
    return False


def _is_generic_noise(val):
    low = val.lower().strip()
    if low in _HARD_DENYLIST:
        return True
    tokens = low.split()
    if len(tokens) == 1:
        if low in _GENERIC_SINGLE_TOKENS:
            return True
        if low.isupper() and len(low) <= 6:
            return True
    return False


def _normalize_candidate(text):
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'[;:,]+$', '', text).strip()
    return text


def _is_prose(val):
    low = val.lower()
    tokens = low.split()
    if not tokens:
        return True
    if tokens[0] in _PROSE_START_WORDS:
        return True
    for frag in _PROSE_FRAGMENTS:
        if frag in low:
            return True
    if len(tokens) > 6:
        return True
    has_quotes = '"' in val or '\u201c' in val or '\u201d' in val
    verb_words = {"means", "shall", "includes", "including", "agrees", "acknowledges"}
    if has_quotes and any(t in verb_words for t in tokens):
        return True
    alnum_count = sum(1 for c in val if c.isalnum())
    if len(val) > 0 and alnum_count / len(val) < 0.5:
        return True
    return False


def _is_valid_value(val):
    if not val or len(val) < 4:
        return False
    tokens = val.split()
    if len(tokens) < 2 and not any(c.isalnum() for c in val):
        return False
    if len(tokens) == 1 and val.lower() in _GENERIC_SINGLE_TOKENS:
        return False
    if val.lower() in _SF_STOP_LABELS:
        return False
    if _is_prose(val):
        return False
    return True


def _csv_phrase_scan(full_text):
    """Scan full_text for exact CSV account name phrases (word-boundary, case-insensitive).

    Track-listing sections (song titles, artist names in schedules) are stripped
    before scanning to prevent music metadata from matching Salesforce accounts.
    """
    # Strip track-listing sections so song titles / artist names don't match
    full_text = _strip_track_listing_text(full_text)

    try:
        from server.resolvers.account_index import get_index
    except ImportError:
        return []

    idx = get_index()
    if not idx.loaded:
        return []

    hits = []
    seen_lower = set()
    text_lower = full_text.lower() if full_text else ""
    if not text_lower:
        return []

    for rec in idx.all_records():
        for name_attr in ("account_name", "artist_name", "company_name", "legal_name"):
            name = getattr(rec, name_attr, "")
            if not name or len(name) < 3:
                continue
            name_low = name.lower()
            if name_low in seen_lower:
                continue
            if name_low in _GENERIC_SINGLE_TOKENS:
                continue
            # Suppress single-word person-name-like matches (e.g. "Sanjay", "Dilip")
            # that are too ambiguous to be reliable counterparty identifiers.
            name_tokens = name_low.split()
            if len(name_tokens) == 1 and not _COMPANY_MARKERS_RE.search(name):
                continue
            pos = text_lower.find(name_low)
            if pos < 0:
                continue
            before_ok = pos == 0 or not text_lower[pos - 1].isalnum()
            end = pos + len(name_low)
            after_ok = end >= len(text_lower) or not text_lower[end].isalnum()
            if before_ok and after_ok:
                seen_lower.add(name_low)
                hits.append(name)

    hits.sort(key=lambda n: (-len(n), n.lower()))
    return hits


def extract_account_candidates(full_text, extracted_headers):
    """Extract actual account-name values from body text using strict rules.

    Priority:
      1) CSV-first exact phrase scan — highest confidence
      2) Strict label:value extraction with anchored labels and prose rejection
      3) Fallback to non-label headers (last resort)

    Returns list of dicts: [{"value": str, "source_type": str}]
    where source_type is one of: strict_label_value, csv_phrase_hit, header_fallback
    """
    all_candidates = []
    seen_lower = set()

    csv_hits = _csv_phrase_scan(full_text)
    for hit in csv_hits:
        normed = _normalize_candidate(hit)
        if normed and normed.lower() not in seen_lower:
            if _is_generic_noise(normed):
                continue
            seen_lower.add(normed.lower())
            all_candidates.append({"value": normed, "source_type": "csv_phrase_hit"})

    lines = full_text.split("\n") if full_text else []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = _STRICT_LABEL_VALUE_RE.match(line)
        if m:
            val = _normalize_candidate(m.group(1))
            if _is_valid_value(val) and val.lower() not in seen_lower:
                seen_lower.add(val.lower())
                all_candidates.append({"value": val, "source_type": "strict_label_value"})

    if all_candidates:
        return all_candidates

    header_values = []
    for h in extracted_headers:
        normed = _normalize_candidate(h)
        if not normed or normed.lower() in seen_lower:
            continue
        if normed.lower() in _SF_STOP_LABELS:
            continue
        h_lower = normed.lower()
        is_label = any(h_lower == hint or h_lower == hint + ":" for hint in _SF_ENTITY_HINTS)
        if is_label:
            continue
        if _is_generic_noise(normed):
            continue
        if normed.lower() in _GENERIC_SINGLE_TOKENS:
            continue
        if _is_prose(normed):
            continue
        seen_lower.add(normed.lower())
        header_values.append({"value": normed, "source_type": "header_fallback"})

    return header_values[:10]


_SOURCE_TYPE_PRIORITY = {
    "recital_party": 0,
    "strict_label_value": 1,
    "csv_phrase_hit": 2,
    "header_fallback": 3,
}


_CMG_KNOWN_ALIASES = {
    "ostereo limited",
    "ostereo publishing limited",
    "asterio limited",
    "asterio publishing limited",
}

_CMG_ACCOUNT_TYPES = {
    "division",
}


def _is_cmg_side(candidate_name, sf_candidates):
    name_lower = candidate_name.lower().strip()
    if name_lower in _CMG_KNOWN_ALIASES:
        return True
    for c in sf_candidates:
        acct_type = (c.get("type") or "").strip().lower()
        if acct_type in _CMG_ACCOUNT_TYPES:
            return True
    return False


_AGREEMENT_TYPE_KEYWORDS = {
    "distribution": ["distribution agreement", "distribution deal", "distribution contract", "distribution"],
    "license": ["license agreement", "licensing agreement", "licence agreement", "license"],
    "recording": ["recording agreement", "recording contract", "recording"],
    "publishing": ["publishing agreement", "publishing contract", "publishing deal", "publishing"],
    "management": ["management agreement", "management contract", "management"],
    "service": ["service agreement", "services agreement", "service contract"],
    "amendment": ["amendment", "addendum", "modification agreement"],
    "termination": ["termination agreement", "termination notice", "termination"],
}

_SUBTYPE_KEYWORD_MAP = {
    "Distribution": [
        "distribution agreement", "digital distribution", "digital distribution agreement",
        "distribution", "download and streaming of records", "records monetisation",
        "records monetization", "channels monetisation", "channels monetization",
    ],
    "Sync": [
        "sync licensing", "sync license", "sync licence", "synch licensing",
        "synch license", "synch licences", "synch licenses", "synchronization",
        "synchronisation", "synch revenue", "sync revenue",
    ],
    "Licensing Agreement": [
        "licensing agreement", "license agreement", "licence agreement",
        "exclusive license", "exclusive licence", "exclusive right", "exclusive rights",
        "non-exclusive license", "non-exclusive licence",
    ],
    "Pub Admin": [
        "admin publishing", "administration publishing", "publishing administration",
        "pub admin",
    ],
    "Co-Pub": [
        "co-publishing", "co publishing", "co-pub", "copub",
    ],
    "CMA": [
        "cma", "catalog management agreement",
    ],
    "CPA": [
        "cpa", "catalog participation agreement",
    ],
    "CMA/CPA": [
        "cma/cpa", "cma and cpa", "cma + cpa", "combined cma cpa",
    ],
    "Distribution w/ CMA and CPA": [
        "distribution with cma and cpa", "distribution w/ cma and cpa",
    ],
    "Distro CMA": [
        "distro cma", "distribution cma",
    ],
    "Label Ventures": [
        "label ventures", "label venture", "joint venture",
        "label services", "label service", "label services agreement",
    ],
    "Profit Participation Agreement": [
        "profit participation agreement", "profit participation", "profit share",
    ],
    "Side Artist": [
        "side artist", "featured artist",
    ],
    "Assignment": [
        "assignment agreement", "assignment of rights", "assignment",
    ],
    "LE Revision": [
        "le revision", "legal entity revision", "legal entity change",
    ],
    "Other": [
        "other subtype", "other agreement",
    ],
}

_SUBTYPE_REVIEW_DELTA = 0.15
_SUBTYPE_CANDIDATE_THRESHOLD = 0.20

_TERRITORY_PATTERNS = [
    (re.compile(r'\b(?:worldwide|world-wide|the\s+world)\b', re.IGNORECASE), "Worldwide"),
    (re.compile(r'\b(?:united\s+states|USA|U\.S\.A|U\.S\.)\b', re.IGNORECASE), "United States"),
    (re.compile(r'\b(?:united\s+kingdom|UK|U\.K\.)\b', re.IGNORECASE), "United Kingdom"),
    (re.compile(r'\b(?:european\s+union|EU|europe)\b', re.IGNORECASE), "Europe"),
    (re.compile(r'\b(?:north\s+america)\b', re.IGNORECASE), "North America"),
    (re.compile(r'\b(?:asia[\s-]*pacific|APAC)\b', re.IGNORECASE), "Asia-Pacific"),
]

_EFFECTIVE_DATE_RE = re.compile(
    r'(?:effective\s+(?:date|as\s+of)|as\s+of|dated?\s+(?:as\s+of\s+)?|made\s+(?:on\s+)?(?:the\s+)?|entered\s+into\s+(?:as\s+of\s+)?(?:the\s+)?)'
    r'\s*[:;]?\s*'
    r'(\d{1,2}[\s/\-\.]+(?:January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s/\-\.,]+\d{2,4}'
    r'|\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}'
    r'|(?:January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}[\s,]+\d{2,4}'
    r'|\d{1,2}(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(?:January|February|March|April|May|June|July|August|September|October|November|December|'
    r'Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s,]+\d{2,4})',
    re.IGNORECASE,
)

_TERM_DURATION_RE = re.compile(
    r'(?:(?:initial|minimum|the)?\s*term\s+(?:(?:of\s+)?(?:this\s+)?(?:agreement\s+)?(?:shall\s+be|is|commencing)\s+|of\s+)|'
    r'period\s+of\s+|duration\s+of\s+|for\s+a\s+period\s+of\s+)'
    r'(\d+)\s*(years?|months?|weeks?|days?)',
    re.IGNORECASE,
)

_TERM_PHRASE_RE = re.compile(
    r'(\d+)\s*[\-\(]?\s*(?:year|month|week|day)s?\s*(?:term|period|duration)',
    re.IGNORECASE,
)

_PERPETUAL_RE = re.compile(
    r'\b(?:perpetual|in\s+perpetuity|life\s+of\s+copyright)\b',
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Evidence context enrichment — attaches surrounding contract text to checks
# ---------------------------------------------------------------------------
_EVIDENCE_CONTEXT_RADIUS = 300  # chars before/after match to capture


def _find_evidence_context(full_text, search_terms):
    """Find the best matching passage in full_text for any of the search_terms.

    Returns a dict with the evidence context, or empty dict if nothing found.
    """
    if not full_text or not search_terms:
        return {}
    text_lower = full_text.lower()
    for term in search_terms:
        if not term or len(term) < 3:
            continue
        term_lower = term.lower()
        pos = text_lower.find(term_lower)
        if pos < 0:
            continue
        # Expand to paragraph boundaries
        start = max(0, pos - _EVIDENCE_CONTEXT_RADIUS)
        end = min(len(full_text), pos + len(term) + _EVIDENCE_CONTEXT_RADIUS)
        # Snap to newlines for cleaner excerpts
        nl_before = full_text.rfind("\n", start, pos)
        if nl_before >= start:
            start = nl_before + 1
        nl_after = full_text.find("\n", pos + len(term), end)
        if nl_after > 0 and nl_after <= end:
            end = nl_after
        snippet = full_text[start:end].strip()
        return {
            "evidence_context": snippet,
            "evidence_match_term": term,
            "evidence_char_offset": pos,
        }
    return {}


def _enrich_checks_with_evidence(checks, full_text):
    """Post-process checks to attach evidence_context from the source document."""
    if not full_text:
        return checks
    for ck in checks:
        if ck.get("evidence_context"):
            continue  # already has evidence
        search_terms = []
        # Try evidence hints first (actual matched keywords from _extract_* functions)
        hints = ck.pop("_evidence_hints", None)
        if hints:
            search_terms.extend(hints)
        # Try the value
        val = ck.get("value")
        if val and isinstance(val, str) and len(val) >= 3:
            search_terms.append(val)
        # Try keywords from the reason field (quoted terms like 'distribution agreement')
        reason = ck.get("reason", "")
        import re as _re
        quoted = _re.findall(r"'([^']{3,})'", reason)
        search_terms.extend(quoted)
        # Try the label as last resort
        label = ck.get("label", "")
        if label:
            search_terms.append(label)
        evidence = _find_evidence_context(full_text, search_terms)
        ck.update(evidence)
    return checks


def _extract_contract_type(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    result = _guess_agreement_type(full_text)
    if result == "unknown":
        return {"status": "fail", "confidence": 0, "value": None, "reason": "Contract type not detected in text"}
    text_lower = full_text.lower()
    lines = text_lower.split("\n")
    title_zone = "\n".join(lines[:10])
    best_kw = ""
    for kw in _AGREEMENT_TYPE_KEYWORDS.get(result, []):
        if kw in title_zone:
            return {"status": "pass", "confidence": 0.95, "value": result, "reason": f"'{kw}' found in title block"}
        if kw in text_lower and not best_kw:
            best_kw = kw
    if best_kw:
        return {"status": "review", "confidence": 0.6, "value": result, "reason": f"'{best_kw}' found in body text only"}
    return {"status": "fail", "confidence": 0, "value": None, "reason": "Contract type not detected"}


def _extract_contract_subtype(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available", "candidates": []}
    text_lower = full_text.lower()
    lines = text_lower.split("\n")
    title_zone = "\n".join(lines[:10])
    preamble_zone = "\n".join(lines[:35])

    scores = {}
    evidence_map = {}
    for canonical, keywords in _SUBTYPE_KEYWORD_MAP.items():
        best_score = 0.0
        hits = []
        for kw in keywords:
            if kw in title_zone:
                w = 0.40
                hits.append(f"title: {kw}")
            elif kw in preamble_zone:
                w = 0.25
                hits.append(f"preamble: {kw}")
            elif kw in text_lower:
                w = 0.15
                hits.append(f"body: {kw}")
            else:
                w = 0.0
            if w > best_score:
                best_score = w
        if hits:
            base = best_score
            bonus = min(len(hits) - 1, 3) * 0.08
            total = round(min(base + bonus, 1.0), 4)
            scores[canonical] = total
            evidence_map[canonical] = hits

    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    candidates = []
    for val, conf in ranked:
        if conf >= _SUBTYPE_CANDIDATE_THRESHOLD or len(candidates) < 1:
            candidates.append({
                "value": val,
                "confidence": round(conf, 2),
                "evidence": evidence_map.get(val, []),
            })
    candidates = [c for c in candidates if c["confidence"] > 0]

    if not candidates:
        return {
            "status": "review", "confidence": 0.3, "value": None,
            "reason": "No specific subtype phrase detected",
            "candidates": [],
        }

    top = candidates[0]
    if len(candidates) == 1:
        status = "pass"
        reason = f"Subtype '{top['value']}' detected"
    else:
        delta = top["confidence"] - candidates[1]["confidence"]
        above_threshold = [c for c in candidates if c["confidence"] >= _SUBTYPE_CANDIDATE_THRESHOLD]
        if delta > _SUBTYPE_REVIEW_DELTA and len(above_threshold) <= 1:
            status = "pass"
            reason = f"Subtype '{top['value']}' detected (clear winner)"
        else:
            alts = ", ".join(c["value"] for c in candidates[:3])
            status = "review"
            reason = f"Multiple plausible subtypes detected — analyst confirmation required ({alts})"

    return {
        "status": status,
        "confidence": top["confidence"],
        "value": top["value"],
        "reason": reason,
        "candidates": candidates,
    }


def _extract_effective_date(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    m = _EFFECTIVE_DATE_RE.search(full_text[:5000])
    if m:
        date_str = m.group(1).strip().rstrip(",. ")
        return {"status": "pass", "confidence": 0.9, "value": date_str, "reason": "Date found near effective date marker"}
    return {"status": "fail", "confidence": 0, "value": None, "reason": "No effective date found"}


def _extract_term(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    if _PERPETUAL_RE.search(full_text):
        return {"status": "pass", "confidence": 0.9, "value": "Perpetual", "reason": "Perpetual/life-of-copyright term detected"}
    m = _TERM_DURATION_RE.search(full_text)
    if m:
        val = f"{m.group(1)} {m.group(2).lower()}"
        return {"status": "pass", "confidence": 0.85, "value": val, "reason": f"Term duration '{val}' detected"}
    m2 = _TERM_PHRASE_RE.search(full_text)
    if m2:
        val = f"{m2.group(1)} year(s)"
        return {"status": "review", "confidence": 0.6, "value": val, "reason": f"Possible term '{val}' detected from phrase pattern"}
    return {"status": "fail", "confidence": 0, "value": None, "reason": "No term/duration found"}


def _extract_territory(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    territory_ctx_re = re.compile(
        r'(?:territory|territories|licensed\s+territory|distribution\s+territory)\s*[:;]?\s*(.{1,200})',
        re.IGNORECASE,
    )
    ctx_match = territory_ctx_re.search(full_text)
    search_zone = ctx_match.group(1) if ctx_match else full_text

    found = []
    for pattern, label in _TERRITORY_PATTERNS:
        if pattern.search(search_zone):
            found.append(label)
    if not found:
        for pattern, label in _TERRITORY_PATTERNS:
            if pattern.search(full_text):
                found.append(label)

    if not found:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No territory references found"}
    unique = list(dict.fromkeys(found))
    if "Worldwide" in unique:
        return {"status": "pass", "confidence": 0.9, "value": "Worldwide", "reason": "'Worldwide' territory detected"}
    if len(unique) == 1:
        return {"status": "pass", "confidence": 0.75, "value": unique[0], "reason": f"Territory '{unique[0]}' detected"}
    return {"status": "review", "confidence": 0.55, "value": ", ".join(unique[:4]), "reason": f"Multiple territories detected: {', '.join(unique[:4])}"}


def _check_role_linkage(resolution_story):
    if not resolution_story:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No resolution story available"}
    legal = resolution_story.get("legal_entity_account")
    cparties = resolution_story.get("counterparties", [])
    unresolved = resolution_story.get("unresolved_counterparties", [])
    manual_req = resolution_story.get("requires_manual_confirmation", False)

    has_legal = legal is not None
    has_counter = len(cparties) > 0 or len(unresolved) > 0 or manual_req

    if has_legal and has_counter:
        if len(cparties) > 0:
            return {"status": "pass", "confidence": 0.9, "value": "Legal entity + counterparty resolved", "reason": "Both legal entity and counterparty identified"}
        return {"status": "review", "confidence": 0.6, "value": "Legal entity resolved, counterparty unresolved", "reason": "Legal entity found; counterparty requires manual confirmation"}
    if has_legal and not has_counter:
        return {"status": "review", "confidence": 0.4, "value": "Legal entity only", "reason": "Legal entity found but no counterparty identified"}
    if not has_legal and has_counter:
        return {"status": "fail", "confidence": 0.2, "value": "No legal entity", "reason": "No CMG legal entity resolved"}
    return {"status": "fail", "confidence": 0, "value": None, "reason": "No role linkage — neither legal entity nor counterparty resolved"}


_OPP_CRITICAL_CHECKS = {"OPP_CONTRACT_TYPE", "OPP_ROLE_LINKAGE"}


def build_opportunity_spine(full_text, resolution_story):
    checks = [
        {"code": "OPP_CONTRACT_TYPE", "label": "Contract Type", **_extract_contract_type(full_text)},
        {"code": "OPP_CONTRACT_SUBTYPE", "label": "Contract Subtype", **_extract_contract_subtype(full_text)},
        {"code": "OPP_EFFECTIVE_DATE", "label": "Effective Date", **_extract_effective_date(full_text)},
        {"code": "OPP_TERM", "label": "Term", **_extract_term(full_text)},
        {"code": "OPP_TERRITORY", "label": "Territory", **_extract_territory(full_text)},
        {"code": "OPP_ROLE_LINKAGE", "label": "Role Linkage", **_check_role_linkage(resolution_story)},
    ]
    _enrich_checks_with_evidence(checks, full_text)

    passed = sum(1 for c in checks if c["status"] == "pass")
    review = sum(1 for c in checks if c["status"] == "review")
    failed = sum(1 for c in checks if c["status"] == "fail")

    has_critical_fail = any(
        c["status"] == "fail" and c["code"] in _OPP_CRITICAL_CHECKS for c in checks
    )

    if has_critical_fail:
        overall = "fail"
    elif failed > 0 or review > 0:
        overall = "review"
    else:
        overall = "pass"

    return {
        "status": overall,
        "checks": checks,
        "summary": {"passed": passed, "review": review, "failed": failed},
    }


_SCHEDULE_TYPE_KEYWORDS = {
    "distro_sync_existing_masters": [
        "distro & sync", "distribution and sync", "distro and sync",
        "existing masters", "master exploitation", "digital exploitation",
        "for digital distribution", "download and streaming of records",
        "for synch licenses", "for sync licenses", "synch licenses", "synch license",
        "synch revenue", "sync revenue",
    ],
    "catalog_acquisition_masters": [
        "catalog acquisition", "acquisition schedule", "schedule 1",
        "schedule i", "masters acquisition",
    ],
    "termination_schedule": [
        "termination schedule", "termination notice", "offboard",
        "actual termination date", "termination date",
    ],
    "general_schedule": [
        "schedule", "exhibit", "appendix", "annex",
    ],
}

_OWNERSHIP_KEYWORDS = [
    "master ownership", "composition ownership", "asset owner",
    "acquired", "ownership split", "split", "rights ownership",
]

_LIFECYCLE_KEYWORDS = [
    "termination notice", "offboard date", "actual termination date",
    "effective date", "delivery date", "commencement",
]


def _opp_check_value(opportunity_spine, check_code):
    if not opportunity_spine:
        return None
    checks = opportunity_spine.get("checks", [])
    for ck in checks:
        if ck.get("code") == check_code:
            return ck.get("value")
    return None


def _extract_schedule_presence(full_text, opportunity_spine):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    m = re.search(r'\b(schedule|exhibit|appendix|annex)\b', full_text, re.IGNORECASE)
    ctype = (_opp_check_value(opportunity_spine, "OPP_CONTRACT_TYPE") or "").lower()
    if m:
        return {"status": "pass", "confidence": 0.9, "value": "Schedule references detected", "reason": "Found schedule/exhibit references in document text", "_evidence_hints": [m.group(0)]}
    if ctype in {"termination", "amendment"}:
        return {"status": "review", "confidence": 0.5, "value": None, "reason": "No explicit schedule markers; may be valid for termination/amendment form"}
    return {"status": "fail", "confidence": 0.0, "value": None, "reason": "No schedule/exhibit markers detected"}


def _extract_schedule_type(full_text, contract_type_value=None):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available", "candidates": []}

    text_lower = full_text.lower()
    lines = text_lower.split("\n")
    title_zone = "\n".join(lines[:10])
    preamble_zone = "\n".join(lines[:35])
    scores = {}
    evidence_map = {}

    for stype, keywords in _SCHEDULE_TYPE_KEYWORDS.items():
        best = 0.0
        hits = []
        for kw in keywords:
            if kw in title_zone:
                w = 0.40
                hits.append(f"title: {kw}")
            elif kw in preamble_zone:
                w = 0.25
                hits.append(f"preamble: {kw}")
            elif kw in text_lower:
                w = 0.15
                hits.append(f"body: {kw}")
            else:
                w = 0.0
            if w > best:
                best = w
        if hits:
            bonus = min(len(hits) - 1, 3) * 0.08
            scores[stype] = round(min(best + bonus, 1.0), 4)
            evidence_map[stype] = hits

    expected = get_expected_schedule_types(contract_type_value) if contract_type_value else []
    priority_order = get_schedule_type_priority()

    specific_types = [s for s in scores if s != "general_schedule"]
    if specific_types and "general_schedule" in scores:
        best_specific_score = max(scores[s] for s in specific_types)
        if best_specific_score >= scores["general_schedule"]:
            del scores["general_schedule"]
            evidence_map.pop("general_schedule", None)
        elif expected:
            expected_with_scores = [s for s in specific_types if s in expected and scores[s] > 0]
            if expected_with_scores:
                del scores["general_schedule"]
                evidence_map.pop("general_schedule", None)

    def _rank_key(item):
        val, conf = item
        priority_idx = priority_order.index(val) if val in priority_order else len(priority_order)
        return (-conf, priority_idx, val)

    ranked = sorted(scores.items(), key=_rank_key)
    candidates = [
        {"value": val, "confidence": round(conf, 2), "evidence": evidence_map.get(val, [])}
        for val, conf in ranked if conf >= _SUBTYPE_CANDIDATE_THRESHOLD
    ]
    if not candidates and ranked:
        val, conf = ranked[0]
        candidates = [{"value": val, "confidence": round(conf, 2), "evidence": evidence_map.get(val, [])}]

    if not candidates:
        return {"status": "review", "confidence": 0.3, "value": None, "reason": "No clear schedule type markers found", "candidates": []}

    top = candidates[0]
    if len(candidates) == 1:
        return {"status": "pass", "confidence": top["confidence"], "value": top["value"], "reason": f"Schedule type '{top['value']}' detected", "candidates": candidates}

    delta = top["confidence"] - candidates[1]["confidence"]
    if delta > _SUBTYPE_REVIEW_DELTA:
        return {"status": "pass", "confidence": top["confidence"], "value": top["value"], "reason": f"Schedule type '{top['value']}' detected (clear winner)", "candidates": candidates}
    alts = ", ".join(c["value"] for c in candidates[:3])
    return {"status": "review", "confidence": top["confidence"], "value": top["value"], "reason": f"Multiple schedule types detected — analyst confirmation required ({alts})", "candidates": candidates}


def _extract_ownership_signals(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    hits = [kw for kw in _OWNERSHIP_KEYWORDS if kw in full_text.lower()]
    if len(hits) >= 2:
        return {"status": "pass", "confidence": 0.85, "value": ", ".join(hits[:3]), "reason": f"Ownership markers detected ({len(hits)} hits)", "_evidence_hints": hits[:3]}
    if len(hits) == 1:
        return {"status": "review", "confidence": 0.55, "value": hits[0], "reason": "Limited ownership evidence; verify schedule rows manually", "_evidence_hints": hits}
    return {"status": "fail", "confidence": 0.0, "value": None, "reason": "No ownership markers detected"}


def _extract_lifecycle_signals(full_text):
    if not full_text:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    hits = [kw for kw in _LIFECYCLE_KEYWORDS if kw in full_text.lower()]
    if len(hits) >= 2:
        return {"status": "pass", "confidence": 0.8, "value": ", ".join(hits[:3]), "reason": f"Lifecycle timing markers detected ({len(hits)} hits)", "_evidence_hints": hits[:3]}
    if len(hits) == 1:
        return {"status": "review", "confidence": 0.5, "value": hits[0], "reason": "Single lifecycle marker detected; review timing fields", "_evidence_hints": hits}
    return {"status": "review", "confidence": 0.35, "value": None, "reason": "No lifecycle markers detected"}


def _check_schedule_role_alignment(resolution_story):
    if not resolution_story:
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No resolution story available"}
    legal = resolution_story.get("legal_entity_account")
    counterparty_count = len(resolution_story.get("counterparties", []))
    unresolved = len(resolution_story.get("unresolved_counterparties", []))
    if legal and counterparty_count > 0:
        return {"status": "pass", "confidence": 0.9, "value": "Legal + counterparty resolved", "reason": "Schedule routing can be anchored to resolved parties"}
    if legal and unresolved > 0:
        return {"status": "review", "confidence": 0.6, "value": "Counterparty unresolved", "reason": "Legal entity resolved but counterparty needs manual onboarding"}
    if legal:
        return {"status": "review", "confidence": 0.5, "value": "Legal entity only", "reason": "Counterparty not resolved; schedule ownership requires review"}
    return {"status": "fail", "confidence": 0.2, "value": "No legal entity", "reason": "No legal entity resolved for schedule alignment"}


_SCH_CRITICAL_CHECKS = {"SCH_PRESENCE", "SCH_ROLE_ALIGNMENT"}


def build_schedule_structure(full_text, resolution_story, opportunity_spine):
    contract_type_val = _opp_check_value(opportunity_spine, "OPP_CONTRACT_TYPE")
    checks = [
        {"code": "SCH_PRESENCE", "label": "Schedule Presence", **_extract_schedule_presence(full_text, opportunity_spine)},
        {"code": "SCH_TYPE", "label": "Schedule Type", **_extract_schedule_type(full_text, contract_type_val)},
        {"code": "SCH_OWNERSHIP", "label": "Ownership Signals", **_extract_ownership_signals(full_text)},
        {"code": "SCH_LIFECYCLE", "label": "Lifecycle Signals", **_extract_lifecycle_signals(full_text)},
        {"code": "SCH_ROLE_ALIGNMENT", "label": "Role Alignment", **_check_schedule_role_alignment(resolution_story)},
    ]
    _enrich_checks_with_evidence(checks, full_text)

    passed = sum(1 for c in checks if c["status"] == "pass")
    review = sum(1 for c in checks if c["status"] == "review")
    failed = sum(1 for c in checks if c["status"] == "fail")
    has_critical_fail = any(c["status"] == "fail" and c["code"] in _SCH_CRITICAL_CHECKS for c in checks)

    if has_critical_fail:
        overall = "fail"
    elif failed > 0 or review > 0:
        overall = "review"
    else:
        overall = "pass"

    return {
        "status": overall,
        "checks": checks,
        "summary": {"passed": passed, "review": review, "failed": failed},
    }


def _guess_agreement_type(full_text):
    if not full_text:
        return "unknown"
    text_lower = full_text.lower()
    lines = text_lower.split("\n")
    title_zone = "\n".join(lines[:10]) if lines else ""

    best_type = "unknown"
    best_weight = 0.0

    for atype, keywords in _AGREEMENT_TYPE_KEYWORDS.items():
        for kw in keywords:
            title_weight = 3.0 if kw in title_zone else 0.0
            body_weight = 1.0 if kw in text_lower else 0.0
            weight = title_weight + body_weight
            if weight > best_weight:
                best_weight = weight
                best_type = atype

    return best_type


_BETWEEN_AND_RE = re.compile(
    r'(?:between|BETWEEN|By\s+and\s+Between|BY\s+AND\s+BETWEEN)\s+'
    r'(.+?)\s+(?:and|AND|&)\s+(.+?)(?:\s*[\(\,\.]|$)',
    re.IGNORECASE | re.MULTILINE,
)

_PARTY_ZONE_RE = re.compile(
    r'(?:(?:BETWEEN|between|By and Between|BY AND BETWEEN|PARTIES|parties)\s*[:\-]?\s*\n?)'
    r'((?:.*\n){1,10})',
    re.MULTILINE,
)

_LABEL_PARTY_RE = re.compile(
    r'([A-Z][A-Za-z\s&\.\,\']+?)\s*\(\s*"?\s*'
    r'(?:Owner|Company|Label|Licensor|Licensee|Publisher|Distributor|Artist|Producer|Manager)'
    r'\s*"?\s*\)',
    re.IGNORECASE,
)

_COMPANY_MARKERS_RE = re.compile(
    r'\b(?:ltd|limited|inc|incorporated|llc|corp|corporation|gmbh|plc|pty|'
    r's\.a\.|sa|bv|ag|entertainments|entertainment|records|recordings|'
    r'music|media|studios|productions|publishing|group)\b',
    re.IGNORECASE,
)

_BANNED_PARTY_MARKERS = re.compile(
    r'\b(?:schedule|definitions|revenue\s+shares?|bank|account\s*(?:number|no|name|#)|'
    r'sort\s*code|iban|swift|routing|wire\s*transfer|ach|beneficiary|'
    r'page|pages|channels?|means|exhibit|appendix|annex|attachment|'
    r'recital|preamble|article|section|clause|paragraph|notices)\b',
    re.IGNORECASE,
)

_COLON_LABEL_RE = re.compile(
    r'^[A-Za-z\s]+:\s',
)

_PROSE_CLAUSE_RE = re.compile(
    r'\b(?:shall|provided that|in accordance|pursuant to|notwithstanding|'
    r'agrees? to|represents|warrants|acknowledges|except as|'
    r'without limiting|to the extent|in consideration|in witness|'
    r'hereby|hereunder|hereto|hereof|therein|thereof|whereas|'
    r'now therefore|witnesseth|effective as of|dated as of|'
    r'entered into|made and entered|for the purpose|subject to)\b',
    re.IGNORECASE,
)

_RECITAL_ADDRESS_RE = re.compile(
    r'\b(?:street|st\.|avenue|ave\.|road|rd\.|boulevard|blvd|suite|floor|'
    r'p\.?o\.?\s*box|zip|postal|state of|county of|province|country|'
    r'california|new york|texas|florida|illinois|tennessee|georgia|'
    r'nashville|los angeles|united states|united kingdom|uk|usa|'
    r'u\.s\.a|u\.k\.|canada|australia|india|germany|france|'
    r'\d{5}[\-]?\d{0,4})\b',
    re.IGNORECASE,
)

_PAGINATION_RE = re.compile(r'(?:page|pg\.?)\s*\d+\s*(?:of\s*\d+)?', re.IGNORECASE)

_GENERIC_ROLE_NOUNS = {
    "owner", "company", "label", "licensor", "licensee", "publisher",
    "distributor", "artist", "producer", "manager", "party", "parties",
    "recipient", "sender", "buyer", "seller", "lender", "borrower",
}

_MAX_RECITAL_PARTIES = 6
_PREAMBLE_LINES = 35


def normalize_party_candidate(raw):
    raw = raw.strip()
    raw = re.sub(r'^\d+[\.\)]\s*', '', raw)
    raw = re.sub(
        r'\s*\(\s*"?\s*(?:the\s+)?(?:Owner|Company|Label|Licensor|Licensee|'
        r'Publisher|Distributor|Artist|Producer|Manager)\s*"?\s*\)',
        '', raw, flags=re.IGNORECASE,
    ).strip()
    raw = raw.strip("()\"'").strip()
    raw = re.sub(r'\s*\(.*?\)\s*$', '', raw).strip()
    raw = re.sub(r'^(and|AND|&)\s+', '', raw).strip()
    raw = re.sub(r',?\s*(?:of|located at|at)\s+\d.*$', '', raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r',?\s*(?:a|an)\s+(?:company|corporation|partnership|firm|entity)\s+.*$', '', raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r',?\s*(?:with|having|whose|located|organized|incorporated|formed)\s+.*$', '', raw, flags=re.IGNORECASE).strip()
    raw = re.sub(r'\s*[,;]+\s*$', '', raw).strip()
    raw = re.sub(r'^["\']|["\']$', '', raw).strip()
    return raw


def is_plausible_party_name(name):
    if not name or len(name) < 3 or len(name) > 100:
        return False
    low = name.lower().strip()
    if _BANNED_PARTY_MARKERS.search(name):
        return False
    if _COLON_LABEL_RE.match(name):
        return False
    if _PROSE_CLAUSE_RE.search(name):
        return False
    if _RECITAL_ADDRESS_RE.search(name):
        return False
    if _PAGINATION_RE.search(name):
        return False
    if name.endswith(':'):
        return False
    if any(c < ' ' and c not in ('\n', '\r', '\t') for c in name):
        return False
    if re.match(r'^[^a-zA-Z0-9]+$', name):
        return False
    if low in ("and", "or", "by", "between", "of", "the"):
        return False
    if low in _GENERIC_ROLE_NOUNS:
        return False
    if low.startswith(("hereinafter", "the ", "this ", "whereas")):
        return False
    word_count = len(low.split())
    if word_count > 10:
        return False
    if not re.search(r'[A-Z]', name):
        return False
    if low.endswith("...") or low.startswith("..."):
        return False
    if " and " in low or " & " in low:
        return False
    if low in _HARD_DENYLIST or low in _GENERIC_SINGLE_TOKENS:
        return False
    if _COMPANY_MARKERS_RE.search(name):
        return True
    words = name.split()
    if len(words) >= 2:
        title_words = [w for w in words if w and w[0].isupper()]
        if len(title_words) >= 2:
            return True
        if len(title_words) >= 1 and len(words) <= 3:
            return True
    if len(words) == 1 and words[0][0].isupper() and len(words[0]) >= 4:
        return True
    return False


def _extract_recital_parties(full_text):
    if not full_text:
        return []
    parties = []
    seen = set()

    preamble_lines = full_text.split("\n")[:_PREAMBLE_LINES]
    preamble_text = "\n".join(preamble_lines)

    for m in _BETWEEN_AND_RE.finditer(preamble_text):
        for g in (m.group(1), m.group(2)):
            name = normalize_party_candidate(g)
            if not is_plausible_party_name(name):
                continue
            norm = name.lower().strip()
            if norm not in seen:
                seen.add(norm)
                parties.append(name)

    for m in _LABEL_PARTY_RE.finditer(preamble_text):
        name = normalize_party_candidate(m.group(1))
        if not is_plausible_party_name(name):
            continue
        norm = name.lower().strip()
        if norm not in seen:
            seen.add(norm)
            parties.append(name)

    for m in _PARTY_ZONE_RE.finditer(preamble_text):
        block = m.group(1)
        for line in block.split("\n"):
            line = normalize_party_candidate(line)
            if not is_plausible_party_name(line):
                continue
            norm = line.lower().strip()
            if norm not in seen:
                seen.add(norm)
                parties.append(line)
            if len(parties) >= _MAX_RECITAL_PARTIES:
                break
        if len(parties) >= _MAX_RECITAL_PARTIES:
            break

    return parties[:_MAX_RECITAL_PARTIES]


def _build_onboarding_recommendation(name, agreement_type):
    if not name:
        return None
    has_company_marker = bool(_COMPANY_MARKERS_RE.search(name))
    if agreement_type == "distribution" and has_company_marker:
        acct_type = "Record Label"
    elif has_company_marker:
        acct_type = "Company"
    else:
        acct_type = "Artist"

    return {
        "suggested_account_name": name,
        "suggested_account_type": acct_type,
        "suggested_contact_name": None,
        "reason": f"Extracted from contract party block but not found in Salesforce account index.",
    }


def build_resolution_story(sf_match_results, full_text):
    if not sf_match_results:
        return {
            "legal_entity_account": None,
            "counterparties": [],
            "business_unit": None,
            "parent_account": None,
            "agreement_type_guess": _guess_agreement_type(full_text),
            "reasoning_steps": ["No account candidates were extracted from this document."],
            "analyst_actions": ["Manual lookup required — no automatic resolution available."],
            "requires_manual_confirmation": True,
            "recital_parties": [],
            "new_entry_detected": False,
            "unresolved_counterparties": [],
            "onboarding_recommendation": None,
        }

    try:
        from server.resolvers.context_scorer import REVIEW_THRESHOLD
    except ImportError:
        REVIEW_THRESHOLD = 0.40

    legal_entity = None
    counterparties = []
    reasoning = []
    actions = []

    cmg_candidates = []
    non_cmg_candidates = []

    for row in sf_match_results:
        if not row.get("visible", True):
            continue
        sf_cands = row.get("candidates", [])
        candidate_name = row.get("source_field", "")
        is_cmg = _is_cmg_side(candidate_name, sf_cands)
        if is_cmg:
            for sc in sf_cands:
                if _is_cmg_side(sc.get("account_name", ""), [sc]):
                    is_cmg = True
                    break
        top_name = row.get("suggested_label", "")
        if top_name == "\u2014":
            top_name = candidate_name
        if sf_cands:
            sf_top = sf_cands[0]
            if _is_cmg_side(sf_top.get("account_name", ""), [sf_top]):
                is_cmg = True

        entry = {
            "name": top_name if top_name != "\u2014" else candidate_name,
            "confidence": round(row.get("match_score", 0.0), 4),
            "match_status": row.get("match_status", "no-match"),
            "source_type": row.get("source_type", "header_fallback"),
            "cmg_side": is_cmg,
            "identity_confidence_pct": row.get("identity_confidence_pct"),
            "context_risk_penalty_pct": row.get("context_risk_penalty_pct", 0),
            "final_confidence_pct": row.get("final_confidence_pct"),
        }
        if sf_cands:
            entry["id"] = sf_cands[0].get("account_id") or None
        else:
            entry["id"] = None

        if is_cmg:
            cmg_candidates.append((entry, row))
        else:
            non_cmg_candidates.append((entry, row))

    cmg_candidates.sort(key=lambda x: (
        0 if x[0]["match_status"] == "match" else 1 if x[0]["match_status"] == "review" else 2,
        -x[0]["confidence"],
    ))

    if cmg_candidates:
        legal_entity = cmg_candidates[0][0]
        src_row = cmg_candidates[0][1]
        src_label = _source_type_label(legal_entity["source_type"])
        reasoning.append(
            f'"{legal_entity["name"]}" identified as CMG-side entity via {src_label} — assigned as legal entity.'
        )
        if legal_entity["match_status"] == "match":
            actions.append(
                f'Legal entity "{legal_entity["name"]}" passed CMG-side match — no action required.'
            )
        else:
            actions.append(
                f'Legal entity "{legal_entity["name"]}" is in "{legal_entity["match_status"]}" status — confirm assignment.'
            )

    for entry, row in non_cmg_candidates:
        composite = entry["confidence"]
        if composite >= REVIEW_THRESHOLD:
            counterparties.append(entry)
            src_label = _source_type_label(entry["source_type"])
            reasoning.append(
                f'"{entry["name"]}" extracted via {src_label} — assigned as counterparty.'
            )
            if entry["match_status"] == "match":
                actions.append(
                    f'Counterparty "{entry["name"]}" passed automatic match — no action required.'
                )
            else:
                actions.append(
                    f'Counterparty "{entry["name"]}" is in "{entry["match_status"]}" status — review match.'
                )

    for row in sf_match_results:
        if not row.get("visible", True):
            continue
        sbd = row.get("scoring_breakdown", {})
        if sbd.get("service_context_penalty", 0) > 0:
            reasoning.append(
                f'"{row["source_field"]}" suppressed — service-context penalty applied ({sbd["service_context_penalty"]}).'
            )
        if sbd.get("address_evidence", 0) > 0:
            addr_label = "full address match" if sbd["address_evidence"] >= 0.25 else "partial address match"
            reasoning.append(
                f'Address evidence ({addr_label}, {sbd["address_evidence"]}) found near "{row["source_field"]}".'
            )

    requires_manual = False
    if legal_entity is None:
        requires_manual = True
        reasoning.append("No CMG-side candidate passed threshold — manual identification required.")
        actions.append("Manual lookup required — identify the CMG-side legal entity for this contract.")
    elif legal_entity["match_status"] != "match":
        requires_manual = True

    if not counterparties:
        reasoning.append("No counterparty candidates met the confidence threshold.")
        actions.append("No counterparty detected. Verify this is a unilateral document or identify counterparty manually.")

    close_scores = []
    for entry, _ in non_cmg_candidates:
        if entry["match_status"] == "review":
            close_scores.append(entry)
    if len(close_scores) >= 2:
        scores = [e["confidence"] for e in close_scores]
        if max(scores) - min(scores) < 0.10:
            requires_manual = True

    has_any_penalty = any(
        row.get("context_risk_penalty_pct", 0) > 0
        for row in sf_match_results if row.get("visible", True)
    )
    if has_any_penalty:
        reasoning.append(
            "Final confidence is identity evidence adjusted by context risk penalties (e.g., service/platform context)."
        )

    agreement_type = _guess_agreement_type(full_text)

    recital_parties = _extract_recital_parties(full_text)

    new_entry_detected = False
    unresolved_counterparties = []
    onboarding_recommendation = None

    if legal_entity is not None and recital_parties:
        resolved_names_lower = set()
        if legal_entity:
            resolved_names_lower.add(legal_entity["name"].lower())
        for cp in counterparties:
            resolved_names_lower.add(cp["name"].lower())
        for sf_row in sf_match_results:
            if sf_row.get("visible", True):
                resolved_names_lower.add(sf_row.get("source_field", "").lower())
                sl = sf_row.get("suggested_label", "")
                if sl and sl != "\u2014":
                    resolved_names_lower.add(sl.lower())

        for party_name in recital_parties:
            if not is_plausible_party_name(party_name):
                continue
            party_lower = party_name.lower()
            if party_lower in _CMG_KNOWN_ALIASES:
                continue
            is_resolved = False
            for rn in resolved_names_lower:
                if party_lower == rn or party_lower in rn or rn in party_lower:
                    is_resolved = True
                    break
            if not is_resolved:
                unresolved_counterparties.append(party_name)

        if unresolved_counterparties and not counterparties:
            first_plausible = None
            for uc in unresolved_counterparties:
                if is_plausible_party_name(uc):
                    first_plausible = uc
                    break
            if first_plausible:
                new_entry_detected = True
                onboarding_recommendation = _build_onboarding_recommendation(
                    first_plausible, agreement_type
                )
                reasoning.append(
                    f'Party "{first_plausible}" found in contract party block but not matched in Salesforce index — new entry detected.'
                )
                actions.append(
                    "New counterparty not found in Salesforce index. Create Account + Contact before proceeding."
                )
                requires_manual = True

    return {
        "legal_entity_account": legal_entity,
        "counterparties": counterparties,
        "business_unit": None,
        "parent_account": None,
        "agreement_type_guess": agreement_type,
        "reasoning_steps": reasoning,
        "analyst_actions": actions,
        "requires_manual_confirmation": requires_manual,
        "recital_parties": recital_parties,
        "new_entry_detected": new_entry_detected,
        "unresolved_counterparties": unresolved_counterparties,
        "onboarding_recommendation": onboarding_recommendation,
    }


def _source_type_label(source_type):
    labels = {
        "recital_party": "contract party/recital block extraction",
        "strict_label_value": "strict label:value extraction",
        "csv_phrase_hit": "CSV phrase scan (known account match)",
        "header_fallback": "header fallback extraction",
    }
    return labels.get(source_type, source_type)


def _run_salesforce_match(extracted_headers, full_text=""):
    """Run multi-account Salesforce matching with composite context scoring.

    Each candidate is scored using:
        composite = name_evidence + address_evidence + account_context - service_penalty

    Multiple accounts can be returned if each has sufficient evidence.
    Service-name false positives (Spotify, Amazon Music, etc.) are penalized.

    Returns a list of match result dicts shaped for the matrix renderer:
        [{ source_field, suggested_label, match_method, match_score,
           confidence_pct, match_status, classification, candidates,
           explanation, evidence_chips, scoring_breakdown, visible,
           source_type }]
    """
    try:
        from server.resolvers.salesforce import resolve_account, is_resolver_enabled
    except ImportError:
        logger.debug("[PREFLIGHT-SF] salesforce resolver not available")
        return []

    if not is_resolver_enabled():
        logger.debug("[PREFLIGHT-SF] resolver not enabled (index not loaded)")
        return []

    try:
        from server.resolvers.context_scorer import score_candidate, DISPLAY_THRESHOLD
    except ImportError:
        logger.debug("[PREFLIGHT-SF] context scorer not available, falling back")
        DISPLAY_THRESHOLD = 0.25
        score_candidate = None

    candidate_dicts = extract_account_candidates(full_text, extracted_headers)
    if not candidate_dicts:
        return []

    recital_parties = _extract_recital_parties(full_text)
    recital_lower = {p.lower() for p in recital_parties}

    _MAX_RESOLVER_CANDIDATES = 24
    candidate_dicts = candidate_dicts[:_MAX_RESOLVER_CANDIDATES]

    results = []
    for cand_info in candidate_dicts:
        candidate = cand_info["value"]
        source_type = cand_info["source_type"]
        is_generic = _is_generic_noise(candidate)

        if _is_borne_in_verb_context(candidate, full_text):
            continue

        is_recital = source_type == "recital_party" or candidate.lower() in recital_lower

        res = resolve_account(candidate)
        top_name = ""
        if res.get("candidates"):
            top_name = res["candidates"][0].get("account_name", "")

        name_score = res.get("score", 0.0)
        name_tier = "none"
        if res.get("candidates"):
            name_tier = res["candidates"][0].get("match_tier", "none")

        effective_source = "recital_party" if is_recital else source_type

        if score_candidate is not None:
            ctx = score_candidate(full_text, candidate, name_score, name_tier,
                                  source_type=effective_source, is_generic_token=is_generic)
            composite = ctx["composite_score"]
            match_status = ctx["match_status"]
            evidence_chips = ctx["evidence_chips"]
            visible = ctx["visible"]
            name_evidence = ctx["name_evidence"]
            address_evidence = ctx["address_evidence"]
            account_ctx = ctx["account_context_evidence"]
            svc_penalty = ctx["service_context_penalty"]
            scoring_breakdown = {
                "name_evidence": name_evidence,
                "address_evidence": address_evidence,
                "account_context_evidence": account_ctx,
                "service_context_penalty": svc_penalty,
            }
        else:
            composite = name_score
            if res["classification"] == "matched":
                match_status = "match"
            elif res["classification"] == "ambiguous":
                match_status = "review"
            else:
                match_status = "no-match"
            evidence_chips = []
            visible = True
            name_evidence = name_score
            address_evidence = 0.0
            account_ctx = 0.0
            svc_penalty = 0.0
            scoring_breakdown = {"name_evidence": name_score}

        identity_raw = name_evidence + address_evidence + account_ctx
        _POSITIVE_MAX = 0.55 + 0.30 + 0.20
        identity_confidence_pct = round(min(identity_raw / _POSITIVE_MAX, 1.0) * 100)
        context_risk_penalty_pct = round(svc_penalty * 100)
        final_confidence_pct = round(composite * 100)

        if res["classification"] == "matched":
            match_method = res["candidates"][0].get("match_tier", "exact") if res.get("candidates") else "exact"
        elif res["classification"] == "ambiguous":
            match_method = res["candidates"][0].get("match_tier", "fuzzy") if res.get("candidates") else "fuzzy"
        else:
            match_method = "none"

        results.append({
            "source_field": candidate,
            "suggested_label": top_name or "\u2014",
            "match_method": match_method,
            "match_score": composite,
            "name_score": name_score,
            "confidence_pct": final_confidence_pct,
            "identity_confidence_pct": identity_confidence_pct,
            "context_risk_penalty_pct": context_risk_penalty_pct,
            "final_confidence_pct": final_confidence_pct,
            "match_status": match_status,
            "classification": res["classification"],
            "candidates": res.get("candidates", []),
            "explanation": res.get("explanation", ""),
            "provider": res.get("provider", ""),
            "evidence_chips": evidence_chips,
            "scoring_breakdown": scoring_breakdown,
            "visible": visible,
            "source_type": effective_source,
            "label_value_hit": source_type == "strict_label_value",
            "recital_party_hit": is_recital,
        })

    results.sort(key=lambda r: (
        _SOURCE_TYPE_PRIORITY.get(r.get("source_type", "header_fallback"), 3),
        0 if r["match_status"] == "review" else 1 if r["match_status"] == "no-match" else 2,
        -r["confidence_pct"],
        r["source_field"].lower(),
    ))

    return results


_FINANCIAL_AMOUNT_KW = [
    "advance", "fee", "payment", "compensation", "consideration",
    "amount", "sum", "price", "cost", "budget", "deposit",
]
_FINANCIAL_RATE_KW = [
    "royalty", "rate", "percentage", "percent", "share", "split",
    "commission", "margin", "revenue share",
]
_PAYMENT_TERM_KW = [
    "net 30", "net 60", "net 90", "payable", "quarterly", "monthly",
    "annually", "semi-annual", "accounting period", "payment terms",
    "within", "days of", "upon receipt", "invoic",
]
_CURRENCY_KW = [
    "usd", "eur", "gbp", "cad", "aud", "jpy", "currency",
    "dollar", "euro", "pound", "sterling",
]
_CURRENCY_SYMBOLS = ["$", "€", "£", "¥"]


def _extract_financial_amounts(text):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    lower = text.lower()
    amount_pat = re.compile(r'[\$€£¥]\s*[\d,]+(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(?:dollars|usd|eur|gbp)')
    amounts_found = amount_pat.findall(lower)
    matched_kw = [kw for kw in _FINANCIAL_AMOUNT_KW if kw in lower]
    kw_hits = len(matched_kw)
    hints = amounts_found[:2] + matched_kw[:2]
    if amounts_found and kw_hits >= 1:
        return {"status": "pass", "confidence": min(0.95, 0.75 + kw_hits * 0.05 + len(amounts_found) * 0.03), "value": f"{len(amounts_found)} amounts, {kw_hits} keywords", "reason": "Financial amounts and keywords detected", "_evidence_hints": hints}
    if amounts_found or kw_hits >= 1:
        return {"status": "review", "confidence": 0.4 + min(0.3, kw_hits * 0.1), "value": f"{len(amounts_found)} amounts, {kw_hits} keywords", "reason": "Partial financial signals", "_evidence_hints": hints}
    return {"status": "fail", "confidence": 0.1, "value": None, "reason": "No financial amount signals detected"}


def _extract_financial_rates(text):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    lower = text.lower()
    rate_pat = re.compile(r'\d+(?:\.\d+)?\s*%|(?:royalty|rate|share|split)\s+(?:of\s+)?\d')
    rates_found = rate_pat.findall(lower)
    matched_kw = [kw for kw in _FINANCIAL_RATE_KW if kw in lower]
    kw_hits = len(matched_kw)
    hints = rates_found[:2] + matched_kw[:2]
    if rates_found and kw_hits >= 2:
        return {"status": "pass", "confidence": min(0.95, 0.7 + kw_hits * 0.05), "value": f"{len(rates_found)} rates, {kw_hits} keywords", "reason": "Financial rates and keywords detected", "_evidence_hints": hints}
    if rates_found or kw_hits >= 1:
        return {"status": "review", "confidence": 0.3 + min(0.3, kw_hits * 0.1), "value": f"{len(rates_found)} rates, {kw_hits} keywords", "reason": "Partial rate signals", "_evidence_hints": hints}
    return {"status": "fail", "confidence": 0.1, "value": None, "reason": "No rate signals detected"}


def _extract_payment_terms(text):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    lower = text.lower()
    matched_kw = [kw for kw in _PAYMENT_TERM_KW if kw in lower]
    kw_hits = len(matched_kw)
    if kw_hits >= 3:
        return {"status": "pass", "confidence": min(0.95, 0.6 + kw_hits * 0.07), "value": f"{kw_hits} payment term signals", "reason": "Payment terms well-defined", "_evidence_hints": matched_kw[:3]}
    if kw_hits >= 1:
        return {"status": "review", "confidence": 0.3 + kw_hits * 0.1, "value": f"{kw_hits} payment term signals", "reason": "Partial payment terms", "_evidence_hints": matched_kw[:3]}
    return {"status": "fail", "confidence": 0.1, "value": None, "reason": "No payment term signals"}


def _extract_currency_signals(text):
    if not text or not text.strip():
        return {"status": "review", "confidence": 0.2, "value": None, "reason": "No text available"}
    lower = text.lower()
    matched_kw = [kw for kw in _CURRENCY_KW if kw in lower]
    matched_sym = [s for s in _CURRENCY_SYMBOLS if s in text]
    kw_hits = len(matched_kw)
    sym_hits = len(matched_sym)
    total = kw_hits + sym_hits
    hints = matched_kw[:2] + matched_sym[:2]
    if total >= 1:
        return {"status": "pass", "confidence": min(0.95, 0.6 + total * 0.1), "value": f"{total} currency signals", "reason": "Currency identified", "_evidence_hints": hints}
    return {"status": "review", "confidence": 0.2, "value": None, "reason": "No explicit currency signals"}


def _check_financial_completeness(text, opportunity_spine):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": "0/3 pillars", "reason": "No text for completeness check"}
    lower = text.lower()
    contract_type = _opp_check_value(opportunity_spine, "OPP_CONTRACT_TYPE") if opportunity_spine else None
    is_termination = contract_type and "termination" in str(contract_type).lower()
    has_amounts = bool(re.search(r'[\$€£¥]\s*[\d,]+|\d[\d,]+\s*(?:dollars|usd)', lower))
    has_rates = bool(re.search(r'\d+(?:\.\d+)?\s*%', lower))
    has_terms = any(kw in lower for kw in ["payable", "quarterly", "monthly", "net 30", "net 60", "payment terms", "accounting period"])
    pillars = sum([has_amounts, has_rates, has_terms])
    if is_termination:
        if pillars >= 1:
            return {"status": "pass", "confidence": 0.8, "value": f"{pillars}/3 pillars (termination lenient)", "reason": "Termination contract — reduced financial requirements"}
        return {"status": "review", "confidence": 0.5, "value": f"{pillars}/3 pillars (termination)", "reason": "Termination with no financial signals"}
    if pillars >= 3:
        return {"status": "pass", "confidence": 0.95, "value": "3/3 pillars", "reason": "Full financial completeness"}
    if pillars >= 2:
        return {"status": "pass", "confidence": 0.75, "value": f"{pillars}/3 pillars", "reason": "Most financial pillars present"}
    if pillars >= 1:
        return {"status": "review", "confidence": 0.45, "value": f"{pillars}/3 pillars", "reason": "Partial financial coverage"}
    return {"status": "fail", "confidence": 0.1, "value": "0/3 pillars", "reason": "No financial completeness"}


def build_financials_readiness(full_text, opportunity_spine):
    checks = [
        {"code": "FIN_AMOUNTS", "label": "Financial Amounts", **_extract_financial_amounts(full_text)},
        {"code": "FIN_RATES", "label": "Financial Rates", **_extract_financial_rates(full_text)},
        {"code": "FIN_PAYMENT_TERMS", "label": "Payment Terms", **_extract_payment_terms(full_text)},
        {"code": "FIN_CURRENCY", "label": "Currency Signals", **_extract_currency_signals(full_text)},
        {"code": "FIN_COMPLETENESS", "label": "Financial Completeness", **_check_financial_completeness(full_text, opportunity_spine)},
    ]
    _enrich_checks_with_evidence(checks, full_text)
    passed = sum(1 for c in checks if c["status"] == "pass")
    review = sum(1 for c in checks if c["status"] == "review")
    failed = sum(1 for c in checks if c["status"] == "fail")
    if passed >= 4:
        overall = "pass"
    elif failed >= 3:
        overall = "fail"
    else:
        overall = "review"
    return {
        "status": overall,
        "checks": checks,
        "summary": {"passed": passed, "review": review, "failed": failed},
    }


_ADDON_TYPE_KW = [
    "add-on", "addon", "amendment", "rider", "supplemental",
    "addendum", "supplement", "additional services", "synchronization",
    "sync", "modification", "extension",
]
_ADDON_RIGHTS_KW = [
    "synchronization", "mechanical", "performance", "digital",
    "distribution", "streaming", "download", "reproduction",
    "master use", "sync rights", "neighboring", "publishing",
    "broadcasting", "theatrical", "sublicens",
]
_ADDON_PRICING_KW = [
    "additional fee", "supplemental", "per use", "flat fee",
    "add-on price", "addon fee", "incremental", "surcharge",
]
_ADDON_DATE_KW = [
    "effective date", "commencement", "renewal", "term extension",
    "option period", "expiration", "valid from", "valid until",
]


def _extract_addon_type_signals(text):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    lower = text.lower()
    matched_kw = [kw for kw in _ADDON_TYPE_KW if kw in lower]
    kw_hits = len(matched_kw)
    if kw_hits >= 3:
        return {"status": "pass", "confidence": min(0.95, 0.6 + kw_hits * 0.07), "value": f"{kw_hits} addon type signals", "reason": "Add-on type clearly identified", "_evidence_hints": matched_kw[:3]}
    if kw_hits >= 1:
        return {"status": "review", "confidence": 0.3 + kw_hits * 0.1, "value": f"{kw_hits} addon type signals", "reason": "Partial add-on type signals", "_evidence_hints": matched_kw[:3]}
    return {"status": "fail", "confidence": 0.1, "value": None, "reason": "No add-on type signals"}


def _extract_addon_rights(text):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": None, "reason": "No text available"}
    lower = text.lower()
    matched_kw = [kw for kw in _ADDON_RIGHTS_KW if kw in lower]
    kw_hits = len(matched_kw)
    if kw_hits >= 3:
        return {"status": "pass", "confidence": min(0.95, 0.65 + kw_hits * 0.05), "value": f"{kw_hits} rights signals", "reason": "Rights well-defined", "_evidence_hints": matched_kw[:3]}
    if kw_hits >= 1:
        return {"status": "review", "confidence": 0.3 + kw_hits * 0.1, "value": f"{kw_hits} rights signals", "reason": "Partial rights coverage", "_evidence_hints": matched_kw[:3]}
    return {"status": "fail", "confidence": 0.1, "value": None, "reason": "No rights signals"}


def _extract_addon_pricing(text):
    if not text or not text.strip():
        return {"status": "review", "confidence": 0.2, "value": None, "reason": "No text available"}
    lower = text.lower()
    amount_pat = re.compile(r'[\$€£¥]\s*[\d,]+(?:\.\d+)?|\d[\d,]*(?:\.\d+)?\s*(?:dollars|usd|eur|gbp)')
    amounts = amount_pat.findall(lower)
    matched_kw = [kw for kw in _ADDON_PRICING_KW if kw in lower]
    kw_hits = len(matched_kw)
    hints = amounts[:2] + matched_kw[:2]
    if amounts and kw_hits >= 1:
        return {"status": "pass", "confidence": min(0.95, 0.6 + kw_hits * 0.1), "value": f"{len(amounts)} amounts, {kw_hits} pricing keywords", "reason": "Add-on pricing identified", "_evidence_hints": hints}
    if amounts or kw_hits >= 1:
        return {"status": "review", "confidence": 0.35, "value": f"{len(amounts)} amounts, {kw_hits} pricing keywords", "reason": "Partial pricing signals", "_evidence_hints": hints}
    return {"status": "review", "confidence": 0.2, "value": None, "reason": "No explicit pricing"}


def _extract_addon_dates(text):
    if not text or not text.strip():
        return {"status": "review", "confidence": 0.2, "value": None, "reason": "No text available"}
    lower = text.lower()
    matched_kw = [kw for kw in _ADDON_DATE_KW if kw in lower]
    kw_hits = len(matched_kw)
    date_pat = re.compile(r'(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2},?\s+\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}')
    dates = date_pat.findall(lower)
    total = kw_hits + len(dates)
    hints = matched_kw[:2] + dates[:2]
    if total >= 2:
        return {"status": "pass", "confidence": min(0.95, 0.5 + total * 0.1), "value": f"{kw_hits} date keywords, {len(dates)} dates", "reason": "Add-on dates well-defined", "_evidence_hints": hints}
    if total >= 1:
        return {"status": "review", "confidence": 0.35, "value": f"{kw_hits} date keywords, {len(dates)} dates", "reason": "Partial date coverage", "_evidence_hints": hints}
    return {"status": "review", "confidence": 0.2, "value": None, "reason": "No explicit dates"}


def _check_addon_completeness(text, opportunity_spine):
    if not text or not text.strip():
        return {"status": "fail", "confidence": 0, "value": "0/3 pillars", "reason": "No text for completeness check"}
    contract_type = _opp_check_value(opportunity_spine, "OPP_CONTRACT_TYPE") if opportunity_spine else None
    is_termination = contract_type and "termination" in str(contract_type).lower()
    if is_termination:
        return {"status": "pass", "confidence": 0.8, "value": "N/A (termination)", "reason": "Add-on completeness not applicable for termination contracts"}
    lower = text.lower()
    has_type = any(kw in lower for kw in _ADDON_TYPE_KW)
    has_rights = any(kw in lower for kw in _ADDON_RIGHTS_KW)
    has_pricing = any(kw in lower for kw in _ADDON_PRICING_KW) or bool(re.search(r'[\$€£¥]\s*[\d,]+', text))
    pillars = sum([has_type, has_rights, has_pricing])
    if pillars >= 3:
        return {"status": "pass", "confidence": 0.9, "value": "3/3 pillars", "reason": "Full add-on completeness"}
    if pillars >= 2:
        return {"status": "pass", "confidence": 0.7, "value": f"{pillars}/3 pillars", "reason": "Most add-on pillars present"}
    if pillars >= 1:
        return {"status": "review", "confidence": 0.4, "value": f"{pillars}/3 pillars", "reason": "Partial add-on coverage"}
    return {"status": "fail", "confidence": 0.1, "value": "0/3 pillars", "reason": "No add-on completeness"}


def build_addons_readiness(full_text, opportunity_spine):
    checks = [
        {"code": "ADDON_TYPE", "label": "Add-on Type Signals", **_extract_addon_type_signals(full_text)},
        {"code": "ADDON_RIGHTS", "label": "Add-on Rights", **_extract_addon_rights(full_text)},
        {"code": "ADDON_PRICING", "label": "Add-on Pricing", **_extract_addon_pricing(full_text)},
        {"code": "ADDON_DATES", "label": "Add-on Dates", **_extract_addon_dates(full_text)},
        {"code": "ADDON_COMPLETENESS", "label": "Add-on Completeness", **_check_addon_completeness(full_text, opportunity_spine)},
    ]
    _enrich_checks_with_evidence(checks, full_text)
    passed = sum(1 for c in checks if c["status"] == "pass")
    review = sum(1 for c in checks if c["status"] == "review")
    failed = sum(1 for c in checks if c["status"] == "fail")
    if passed >= 4:
        overall = "pass"
    elif failed >= 3:
        overall = "fail"
    else:
        overall = "review"
    return {
        "status": overall,
        "checks": checks,
        "summary": {"passed": passed, "review": review, "failed": failed},
    }


def _module_score(module):
    if not module:
        return 0.0
    checks = module.get("checks", [])
    if not checks:
        return 0.0
    total = 0.0
    for c in checks:
        st = c.get("status", "fail")
        conf = float(c.get("confidence", 0))
        if st == "pass":
            total += conf
        elif st == "review":
            total += conf * 0.5
    return total / len(checks)


def _entity_score(story):
    if not story:
        return 0.0
    has_legal = bool(story.get("legal_entity_account"))
    has_counter = bool(story.get("counterparties"))
    if has_legal and has_counter:
        return 1.0
    if has_legal:
        return 0.6
    if has_counter:
        return 0.3
    return 0.0


_GATE_PENALTIES = {"GREEN": 0.0, "YELLOW": 0.15, "RED": 0.35}

_SECTION_WEIGHTS = {
    "opportunity_spine": 0.25,
    "schedule_structure": 0.15,
    "financials_readiness": 0.25,
    "addons_readiness": 0.15,
    "entity_resolution": 0.20,
}


def compute_preflight_health_score(gate_color, opportunity_spine, schedule_structure, financials_readiness, addons_readiness, resolution_story):
    from server.contract_health_runtime import (
        calibrate_contract_health_score,
        classify_contract_health_band,
        get_calibration_version,
    )

    section_scores = {
        "opportunity_spine": _module_score(opportunity_spine),
        "schedule_structure": _module_score(schedule_structure),
        "financials_readiness": _module_score(financials_readiness),
        "addons_readiness": _module_score(addons_readiness),
        "entity_resolution": _entity_score(resolution_story),
    }

    raw = sum(section_scores[k] * _SECTION_WEIGHTS[k] for k in _SECTION_WEIGHTS)
    gate_penalty = _GATE_PENALTIES.get(gate_color, 0.0)
    penalized = max(0.0, raw - gate_penalty)
    calibrated = calibrate_contract_health_score(penalized)
    band = classify_contract_health_band(calibrated)

    return {
        "raw_score": round(raw, 6),
        "calibrated_score": round(calibrated, 6),
        "band": band,
        "calibration_version": get_calibration_version(),
        "section_scores": {k: round(v, 6) for k, v in section_scores.items()},
        "gate_penalty": gate_penalty,
    }

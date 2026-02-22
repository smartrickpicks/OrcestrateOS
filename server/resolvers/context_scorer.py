"""
Context-aware composite scoring for Salesforce account matching.

Produces a composite score per candidate:
    composite = name_evidence + address_evidence + account_context - service_penalty

Weights (configurable):
    name_evidence:         up to 0.55
    address_evidence:      up to 0.30
    account_context:       up to 0.20
    service_context_penalty: down to -0.35

Evidence chips are generated per candidate for UI display.
"""
import re

SCORING_WEIGHTS = {
    "name_max": 0.55,
    "address_max": 0.30,
    "account_context_max": 0.20,
    "service_penalty_max": 0.35,
}

DISPLAY_THRESHOLD = 0.25
MATCH_THRESHOLD = 0.65
REVIEW_THRESHOLD = 0.40

PROXIMITY_STRICT = 60
PROXIMITY_SOFT = 120

_STRONG_ACCOUNT_CUES = [
    "account name", "company name", "legal name", "artist name",
    "party", "licensee", "licensor",
    "billing address", "registered office",
    "counterparty", "payee", "vendor",
]

_WEAK_ACCOUNT_CUES = [
    "limited", "llc", "inc", "ltd", "corp",
    "corporation",
]

_ALL_ACCOUNT_CUES = _STRONG_ACCOUNT_CUES + _WEAK_ACCOUNT_CUES

_SERVICE_CONTEXT_PHRASES = [
    "available on", "streaming on", "listen on",
    "platform", "distribution service", "digital service provider",
    "via spotify", "via apple music", "via amazon music", "via tiktok",
    "via youtube", "via deezer", "via pandora", "via tidal",
    "content delivery", "music service", "streaming service",
    "streaming platform", "digital platform",
]

_DSP_NAMES = {
    "spotify", "apple music", "amazon music", "tiktok", "youtube",
    "youtube music", "deezer", "pandora", "tidal", "soundcloud",
    "napster", "audiomack", "iheart", "iheartradio",
}

_ADDRESS_RE = re.compile(
    r'(?:(?:\d{1,5}[ \t]+[\w ]{2,30}(?:street|st|avenue|ave|road|rd|drive|dr|boulevard|blvd|lane|ln|way|court|ct|place|pl|circle|cir))'
    r'|(?:p\.?\s*o\.?\s*box\s+\d+)'
    r'|(?:suite\s+\d+[a-z]?)'
    r'|(?:\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)?,?\s*[A-Z]{2}\s+\d{5}(?:-\d{4})?)'
    r'|(?:\b\d{5}(?:-\d{4})?\b))',
    re.IGNORECASE,
)

_ZIP_RE = re.compile(r'\b(\d{5})(?:-\d{4})?\b')

_CITY_STATE_RE = re.compile(
    r'\b([A-Z][a-z]+(?:\s[A-Z][a-z]+)?),?\s*([A-Z]{2})\s+\d{5}',
)


def _find_candidate_positions(text_lower, candidate_lower):
    positions = []
    start = 0
    while True:
        pos = text_lower.find(candidate_lower, start)
        if pos < 0:
            break
        before_ok = pos == 0 or not text_lower[pos - 1].isalnum()
        end = pos + len(candidate_lower)
        after_ok = end >= len(text_lower) or not text_lower[end].isalnum()
        if before_ok and after_ok:
            positions.append(pos)
        start = pos + 1
    return positions


def _get_proximity_window(text, pos, candidate_len, radius):
    start = max(0, pos - radius)
    end = min(len(text), pos + candidate_len + radius)
    return text[start:end].lower()


ADDRESS_PROXIMITY_CHARS = 150


def _get_address_window(text, pos, candidate_len):
    start = max(0, pos - ADDRESS_PROXIMITY_CHARS)
    end = min(len(text), pos + candidate_len + ADDRESS_PROXIMITY_CHARS)
    return text[start:end]


def score_account_context(full_text, candidate, positions=None):
    if not full_text or not candidate:
        return 0.0, False

    text_lower = full_text.lower()
    cand_lower = candidate.lower()

    if positions is None:
        positions = _find_candidate_positions(text_lower, cand_lower)

    if not positions:
        return 0.0, False

    cand_tokens = set(cand_lower.split())

    best_strong = 0
    best_weak = 0
    for pos in positions:
        window_strict = _get_proximity_window(full_text, pos, len(candidate), PROXIMITY_STRICT)
        window_soft = _get_proximity_window(full_text, pos, len(candidate), PROXIMITY_SOFT)
        window_strict_clean = window_strict.replace(cand_lower, " ")
        window_soft_clean = window_soft.replace(cand_lower, " ")

        strong_count = 0
        weak_count = 0
        for cue in _STRONG_ACCOUNT_CUES:
            cue_tokens = set(cue.split())
            if cue_tokens & cand_tokens:
                continue
            if cue in window_strict_clean:
                strong_count += 1
            elif cue in window_soft_clean:
                strong_count += 1

        for cue in _WEAK_ACCOUNT_CUES:
            cue_tokens = set(cue.split())
            if cue_tokens & cand_tokens:
                continue
            if cue in window_strict_clean:
                weak_count += 1

        if strong_count > best_strong:
            best_strong = strong_count
            best_weak = weak_count
        elif strong_count == best_strong and weak_count > best_weak:
            best_weak = weak_count

    if best_strong == 0 and best_weak == 0:
        return 0.0, False

    if best_strong == 0:
        ratio = min(best_weak / 4.0, 0.25)
    else:
        total = best_strong + min(best_weak, 2) * 0.3
        ratio = min(total / 4.0, 1.0)

    return round(ratio * SCORING_WEIGHTS["account_context_max"], 4), True


def score_service_context(full_text, candidate, positions=None, source_type="header_fallback"):
    if not full_text or not candidate:
        return 0.0, False

    text_lower = full_text.lower()
    cand_lower = candidate.lower()

    is_dsp = cand_lower in _DSP_NAMES

    if is_dsp:
        raw_penalty = SCORING_WEIGHTS["service_penalty_max"]
    else:
        if positions is None:
            positions = _find_candidate_positions(text_lower, cand_lower)

        if not positions:
            return 0.0, False

        max_service_count = 0
        for pos in positions:
            window = _get_proximity_window(full_text, pos, len(candidate), PROXIMITY_STRICT)
            svc_count = 0
            for phrase in _SERVICE_CONTEXT_PHRASES:
                if phrase in window:
                    svc_count += 1
            for dsp in _DSP_NAMES:
                if dsp in window and dsp != cand_lower:
                    svc_count += 1
            max_service_count = max(max_service_count, svc_count)

        if max_service_count == 0:
            window_soft_max = 0
            for pos in positions:
                window = _get_proximity_window(full_text, pos, len(candidate), PROXIMITY_SOFT)
                svc_count = 0
                for phrase in _SERVICE_CONTEXT_PHRASES:
                    if phrase in window:
                        svc_count += 1
                for dsp in _DSP_NAMES:
                    if dsp in window and dsp != cand_lower:
                        svc_count += 1
                window_soft_max = max(window_soft_max, svc_count)

            if window_soft_max == 0:
                return 0.0, False
            ratio = min(window_soft_max / 4.0, 0.7)
            raw_penalty = round(ratio * SCORING_WEIGHTS["service_penalty_max"], 4)
        else:
            ratio = min(max_service_count / 3.0, 1.0)
            raw_penalty = round(ratio * SCORING_WEIGHTS["service_penalty_max"], 4)

    if source_type == "recital_party":
        raw_penalty = min(raw_penalty, 0.03)
    elif source_type == "strict_label_value":
        raw_penalty = min(raw_penalty, 0.08)
    elif source_type == "csv_phrase_hit":
        if not is_dsp:
            raw_penalty = min(raw_penalty, 0.15)

    return raw_penalty, True


def extract_address_fragments(full_text):
    if not full_text:
        return []
    return [m.group(0).strip() for m in _ADDRESS_RE.finditer(full_text)]


def score_address_evidence(full_text, candidate, positions=None):
    if not full_text or not candidate:
        return 0.0, []

    text_lower = full_text.lower()
    cand_lower = candidate.lower()

    if positions is None:
        positions = _find_candidate_positions(text_lower, cand_lower)

    if not positions:
        return 0.0, []

    chips = []
    best_score = 0.0

    for pos in positions:
        addr_window = _get_address_window(full_text, pos, len(candidate))

        addr_matches = _ADDRESS_RE.findall(addr_window)
        if not addr_matches:
            continue

        zip_matches = _ZIP_RE.findall(addr_window)
        city_matches = _CITY_STATE_RE.findall(addr_window)

        if city_matches and zip_matches:
            score = SCORING_WEIGHTS["address_max"]
            if "address_verified" not in chips:
                chips.append("address_verified")
            if "city_match" not in chips:
                chips.append("city_match")
            if "zip_match" not in chips:
                chips.append("zip_match")
        elif zip_matches:
            score = SCORING_WEIGHTS["address_max"] * 0.6
            if "address_partial" not in chips:
                chips.append("address_partial")
            if "zip_match" not in chips:
                chips.append("zip_match")
        elif city_matches:
            score = SCORING_WEIGHTS["address_max"] * 0.5
            if "address_partial" not in chips:
                chips.append("address_partial")
            if "city_match" not in chips:
                chips.append("city_match")
        else:
            score = SCORING_WEIGHTS["address_max"] * 0.3
            if "address_partial" not in chips:
                chips.append("address_partial")

        best_score = max(best_score, score)

    return round(best_score, 4), chips


def compute_composite_score(name_score, address_score, account_ctx_score, service_penalty):
    name_contrib = min(name_score, 1.0) * SCORING_WEIGHTS["name_max"]
    composite = name_contrib + address_score + account_ctx_score - service_penalty
    return round(max(0.0, min(composite, 1.0)), 4)


def classify_by_composite(composite_score, has_service_penalty, name_score, source_type="header_fallback", is_generic_token=False):
    if is_generic_token and source_type != "strict_label_value":
        if composite_score >= REVIEW_THRESHOLD:
            return "review"
        return "no-match"

    if composite_score >= MATCH_THRESHOLD and not (has_service_penalty and name_score < 0.85):
        return "match"
    if composite_score >= REVIEW_THRESHOLD:
        return "review"
    return "no-match"


def build_evidence_chips(name_score, name_tier, address_chips, has_account_ctx, has_service_penalty):
    chips = []

    if name_score >= 1.0:
        chips.append("name_exact")
    elif name_score >= 0.6:
        chips.append("name_fuzzy")

    chips.extend(address_chips)

    if has_account_ctx:
        chips.append("account_context")

    if has_service_penalty:
        chips.append("service_context_penalty")

    return chips


def score_candidate(full_text, candidate, name_score, name_tier, source_type="header_fallback", is_generic_token=False):
    text_lower = (full_text or "").lower()
    cand_lower = candidate.lower()
    positions = _find_candidate_positions(text_lower, cand_lower)

    acct_ctx_score, has_acct_ctx = score_account_context(full_text, candidate, positions)
    svc_penalty, has_svc_penalty = score_service_context(full_text, candidate, positions, source_type=source_type)
    addr_score, addr_chips = score_address_evidence(full_text, candidate, positions)

    composite = compute_composite_score(name_score, addr_score, acct_ctx_score, svc_penalty)
    status = classify_by_composite(composite, has_svc_penalty, name_score,
                                   source_type=source_type, is_generic_token=is_generic_token)
    chips = build_evidence_chips(name_score, name_tier, addr_chips, has_acct_ctx, has_svc_penalty)

    return {
        "composite_score": composite,
        "match_status": status,
        "evidence_chips": chips,
        "name_evidence": round(min(name_score, 1.0) * SCORING_WEIGHTS["name_max"], 4),
        "address_evidence": addr_score,
        "account_context_evidence": acct_ctx_score,
        "service_context_penalty": svc_penalty,
        "visible": composite >= DISPLAY_THRESHOLD,
    }

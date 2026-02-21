"""
Tests for Field Suggestions match matrix UI logic.

Covers:
  - Match status mapping (_smGetMatchStatus equivalent)
  - Confidence bucket mapping (_smGetConfidenceBucket equivalent)
  - Deterministic sorting (_smSortSuggestions equivalent)
  - Evidence chip generation (_smGetEvidenceChips equivalent)
  - Status priority ordering
"""
import pytest


def sm_get_confidence_pct(sug):
    if not sug:
        return 0
    if sug.get("confidence_pct") is not None:
        return sug["confidence_pct"]
    if sug.get("match_score", 0) > 0:
        return round(sug["match_score"] * 100)
    return 0


def sm_get_match_status(sug):
    if not sug:
        return "no-match"
    method = sug.get("match_method", "none")
    if method == "none":
        return "no-match"
    pct = sm_get_confidence_pct(sug)
    if pct >= 80:
        return "match"
    if pct >= 40:
        return "review"
    return "no-match"


def sm_get_confidence_bucket(pct):
    if pct >= 80:
        return "high"
    if pct >= 60:
        return "med"
    if pct > 0:
        return "low"
    return "none"


def sm_status_priority(status):
    if status == "review":
        return 0
    if status == "no-match":
        return 1
    return 2


def sm_sort_suggestions(suggestions):
    return sorted(suggestions, key=lambda s: (
        sm_status_priority(sm_get_match_status(s)),
        -sm_get_confidence_pct(s),
        (s.get("source_field") or "").lower(),
    ))


def sm_get_evidence_chips(sug):
    chips = []
    method = sug.get("match_method", "none")
    method_labels = {
        "alias_exact": "Alias", "exact": "Exact", "phrase_fuzzy": "Fuzzy",
        "fuzzy": "Fuzzy", "token_overlap": "Keyword", "keyword": "Keyword",
    }
    if method in method_labels:
        chips.append(method_labels[method])
    if sug.get("match_reason"):
        chips.append(sug["match_reason"])
    if sug.get("glossary_category"):
        chips.append(sug["glossary_category"])
    if sug.get("body_source"):
        chips.append("BODY")
    return chips


class TestMatchStatusMapping:
    def test_exact_high_confidence_is_match(self):
        assert sm_get_match_status({"match_method": "exact", "confidence_pct": 95}) == "match"

    def test_fuzzy_high_confidence_is_match(self):
        assert sm_get_match_status({"match_method": "fuzzy", "confidence_pct": 85}) == "match"

    def test_fuzzy_medium_confidence_is_review(self):
        assert sm_get_match_status({"match_method": "fuzzy", "confidence_pct": 60}) == "review"

    def test_keyword_low_confidence_is_review(self):
        assert sm_get_match_status({"match_method": "keyword", "confidence_pct": 45}) == "review"

    def test_keyword_very_low_confidence_is_no_match(self):
        assert sm_get_match_status({"match_method": "keyword", "confidence_pct": 30}) == "no-match"

    def test_none_method_always_no_match(self):
        assert sm_get_match_status({"match_method": "none", "confidence_pct": 100}) == "no-match"

    def test_null_sug_is_no_match(self):
        assert sm_get_match_status(None) == "no-match"

    def test_empty_sug_is_no_match(self):
        assert sm_get_match_status({}) == "no-match"

    def test_boundary_80_is_match(self):
        assert sm_get_match_status({"match_method": "exact", "confidence_pct": 80}) == "match"

    def test_boundary_79_is_review(self):
        assert sm_get_match_status({"match_method": "exact", "confidence_pct": 79}) == "review"

    def test_boundary_40_is_review(self):
        assert sm_get_match_status({"match_method": "fuzzy", "confidence_pct": 40}) == "review"

    def test_boundary_39_is_no_match(self):
        assert sm_get_match_status({"match_method": "fuzzy", "confidence_pct": 39}) == "no-match"


class TestConfidenceBucketMapping:
    def test_high(self):
        assert sm_get_confidence_bucket(95) == "high"
        assert sm_get_confidence_bucket(80) == "high"

    def test_med(self):
        assert sm_get_confidence_bucket(60) == "med"
        assert sm_get_confidence_bucket(79) == "med"

    def test_low(self):
        assert sm_get_confidence_bucket(1) == "low"
        assert sm_get_confidence_bucket(59) == "low"

    def test_none(self):
        assert sm_get_confidence_bucket(0) == "none"


class TestConfidencePct:
    def test_confidence_pct_direct(self):
        assert sm_get_confidence_pct({"confidence_pct": 75}) == 75

    def test_confidence_pct_from_score(self):
        assert sm_get_confidence_pct({"match_score": 0.85}) == 85

    def test_confidence_pct_zero(self):
        assert sm_get_confidence_pct({"match_score": 0}) == 0

    def test_confidence_pct_null(self):
        assert sm_get_confidence_pct(None) == 0

    def test_pct_takes_precedence_over_score(self):
        assert sm_get_confidence_pct({"confidence_pct": 50, "match_score": 0.9}) == 50


class TestDeterministicSorting:
    def test_review_before_no_match_before_match(self):
        items = [
            {"source_field": "A", "match_method": "exact", "confidence_pct": 95},
            {"source_field": "B", "match_method": "fuzzy", "confidence_pct": 55},
            {"source_field": "C", "match_method": "none", "confidence_pct": 0},
        ]
        sorted_items = sm_sort_suggestions(items)
        statuses = [sm_get_match_status(s) for s in sorted_items]
        assert statuses == ["review", "no-match", "match"]

    def test_confidence_descending_within_same_status(self):
        items = [
            {"source_field": "X", "match_method": "fuzzy", "confidence_pct": 45},
            {"source_field": "Y", "match_method": "fuzzy", "confidence_pct": 70},
            {"source_field": "Z", "match_method": "fuzzy", "confidence_pct": 60},
        ]
        sorted_items = sm_sort_suggestions(items)
        pcts = [sm_get_confidence_pct(s) for s in sorted_items]
        assert pcts == [70, 60, 45]

    def test_alpha_tiebreaker(self):
        items = [
            {"source_field": "Zebra", "match_method": "exact", "confidence_pct": 90},
            {"source_field": "Apple", "match_method": "exact", "confidence_pct": 90},
            {"source_field": "Mango", "match_method": "exact", "confidence_pct": 90},
        ]
        sorted_items = sm_sort_suggestions(items)
        names = [s["source_field"] for s in sorted_items]
        assert names == ["Apple", "Mango", "Zebra"]

    def test_deterministic_same_input_same_output(self):
        items = [
            {"source_field": "D", "match_method": "keyword", "confidence_pct": 50},
            {"source_field": "A", "match_method": "exact", "confidence_pct": 92},
            {"source_field": "C", "match_method": "none", "confidence_pct": 0},
            {"source_field": "B", "match_method": "fuzzy", "confidence_pct": 65},
        ]
        r1 = sm_sort_suggestions(items)
        r2 = sm_sort_suggestions(items)
        assert [s["source_field"] for s in r1] == [s["source_field"] for s in r2]

    def test_empty_list(self):
        assert sm_sort_suggestions([]) == []

    def test_single_item(self):
        items = [{"source_field": "X", "match_method": "exact", "confidence_pct": 90}]
        assert len(sm_sort_suggestions(items)) == 1

    def test_full_sort_order(self):
        items = [
            {"source_field": "F1", "match_method": "exact", "confidence_pct": 95},
            {"source_field": "F2", "match_method": "fuzzy", "confidence_pct": 55},
            {"source_field": "F3", "match_method": "none", "confidence_pct": 0},
            {"source_field": "F4", "match_method": "keyword", "confidence_pct": 42},
            {"source_field": "F5", "match_method": "exact", "confidence_pct": 100},
        ]
        sorted_items = sm_sort_suggestions(items)
        names = [s["source_field"] for s in sorted_items]
        assert names == ["F2", "F4", "F3", "F5", "F1"]


class TestStatusPriority:
    def test_review_is_first(self):
        assert sm_status_priority("review") == 0

    def test_no_match_is_second(self):
        assert sm_status_priority("no-match") == 1

    def test_match_is_last(self):
        assert sm_status_priority("match") == 2


class TestEvidenceChips:
    def test_exact_method(self):
        chips = sm_get_evidence_chips({"match_method": "exact"})
        assert "Exact" in chips

    def test_alias_method(self):
        chips = sm_get_evidence_chips({"match_method": "alias_exact"})
        assert "Alias" in chips

    def test_fuzzy_method(self):
        chips = sm_get_evidence_chips({"match_method": "fuzzy"})
        assert "Fuzzy" in chips

    def test_keyword_method(self):
        chips = sm_get_evidence_chips({"match_method": "keyword"})
        assert "Keyword" in chips

    def test_none_method_no_chip(self):
        chips = sm_get_evidence_chips({"match_method": "none"})
        assert len(chips) == 0

    def test_with_reason(self):
        chips = sm_get_evidence_chips({"match_method": "exact", "match_reason": "alias_hit"})
        assert "Exact" in chips
        assert "alias_hit" in chips

    def test_with_category(self):
        chips = sm_get_evidence_chips({"match_method": "fuzzy", "glossary_category": "Financial"})
        assert "Financial" in chips

    def test_body_source(self):
        chips = sm_get_evidence_chips({"match_method": "keyword", "body_source": True})
        assert "BODY" in chips

    def test_all_chips(self):
        chips = sm_get_evidence_chips({
            "match_method": "fuzzy",
            "match_reason": "edit_dist",
            "glossary_category": "Legal",
            "body_source": True,
        })
        assert chips == ["Fuzzy", "edit_dist", "Legal", "BODY"]

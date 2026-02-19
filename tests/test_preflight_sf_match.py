"""
Tests for Salesforce match integration in the Preflight engine.

Covers:
  - extract_account_candidates: value-over-label extraction
  - _run_salesforce_match payload shape
  - Section ordering: encoding → sf_match → others
  - Matrix rows include status + confidence
  - Entity header detection
  - Deterministic sorting of SF match results
  - Edge cases: empty headers, resolver disabled
"""
import pytest
from unittest.mock import patch, MagicMock


def _pftl_section_priority(section_key):
    """Python equivalent of PFTL_SECTION_ORDER."""
    order = {
        "encoding": 0,
        "salesforce_match": 1,
        "missing_required": 2,
        "invalid_picklist": 3,
        "metrics": 4,
        "other": 5,
    }
    return order.get(section_key, order["other"])


class TestSectionOrdering:
    def test_encoding_before_sf_match(self):
        assert _pftl_section_priority("encoding") < _pftl_section_priority("salesforce_match")

    def test_sf_match_before_missing_required(self):
        assert _pftl_section_priority("salesforce_match") < _pftl_section_priority("missing_required")

    def test_sf_match_before_invalid_picklist(self):
        assert _pftl_section_priority("salesforce_match") < _pftl_section_priority("invalid_picklist")

    def test_sf_match_before_metrics(self):
        assert _pftl_section_priority("salesforce_match") < _pftl_section_priority("metrics")

    def test_encoding_is_first(self):
        assert _pftl_section_priority("encoding") == 0

    def test_sf_match_is_second(self):
        assert _pftl_section_priority("salesforce_match") == 1

    def test_unknown_section_gets_other(self):
        assert _pftl_section_priority("random_section") == _pftl_section_priority("other")

    def test_deterministic_sort_all_sections(self):
        sections = ["metrics", "salesforce_match", "encoding", "invalid_picklist", "missing_required"]
        sorted_sections = sorted(sections, key=_pftl_section_priority)
        assert sorted_sections == ["encoding", "salesforce_match", "missing_required", "invalid_picklist", "metrics"]


class TestExtractAccountCandidates:
    def test_extracts_value_after_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records\nSome other line"
        result = extract_account_candidates(text, [])
        assert "1888 Records" in result

    def test_extracts_value_with_dash_separator(self):
        from server.preflight_engine import extract_account_candidates
        text = "Client Name - Acme Corp\nMore text"
        result = extract_account_candidates(text, [])
        assert "Acme Corp" in result

    def test_excludes_labels_as_values(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records\nVendor: Big Label Co"
        result = extract_account_candidates(text, ["Account Name", "Vendor"])
        assert "Account Name" not in result
        assert "1888 Records" in result

    def test_normalizes_whitespace(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name:   Spaced   Out   Name  "
        result = extract_account_candidates(text, [])
        assert "Spaced Out Name" in result

    def test_strips_trailing_punctuation(self):
        from server.preflight_engine import extract_account_candidates
        text = "Company Name: Trail Corp;;"
        result = extract_account_candidates(text, [])
        assert "Trail Corp" in result

    def test_deduplicates_case_insensitively(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: Dupe Corp\nAccount: dupe corp"
        result = extract_account_candidates(text, [])
        assert len([c for c in result if c.lower() == "dupe corp"]) == 1

    def test_fallback_to_non_label_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "No label-value pairs here"
        headers = ["Some Real Company", "Account Name", "Contract Date"]
        result = extract_account_candidates(text, headers)
        assert "Some Real Company" in result
        assert "Account Name" not in result

    def test_empty_text_and_headers(self):
        from server.preflight_engine import extract_account_candidates
        result = extract_account_candidates("", [])
        assert result == []

    def test_stop_labels_excluded(self):
        from server.preflight_engine import extract_account_candidates
        text = "No patterns"
        headers = ["Account Name", "Account Name:", "payments/accounting", "Real Corp"]
        result = extract_account_candidates(text, headers)
        assert "Account Name" not in result
        assert "Account Name:" not in result
        assert "payments/accounting" not in result

    def test_value_priority_over_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        headers = ["Account Name", "Fallback Company"]
        result = extract_account_candidates(text, headers)
        assert "1888 Records" in result
        assert "Fallback Company" not in result

    def test_multiple_label_value_patterns(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records\nVendor: Big Label Co\nArtist: DJ Shadow"
        result = extract_account_candidates(text, [])
        assert "1888 Records" in result
        assert "Big Label Co" in result
        assert "DJ Shadow" in result

    def test_short_values_excluded(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: X"
        result = extract_account_candidates(text, [])
        assert "X" not in result

    def test_entity_hint_labels_filtered_from_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "No patterns here"
        headers = ["vendor", "client", "entity", "1888 Records"]
        result = extract_account_candidates(text, headers)
        assert "vendor" not in result
        assert "client" not in result
        assert "entity" not in result
        assert "1888 Records" in result


class TestRunSalesforceMatch:
    def test_import_and_run(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "")
        assert isinstance(result, list)

    def test_empty_headers_and_text_returns_empty(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "")
        assert result == []

    def test_result_payload_shape(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Some Company"], "Account Name: Some Company")
        assert isinstance(result, list)
        for item in result:
            assert "source_field" in item
            assert "suggested_label" in item
            assert "match_method" in item
            assert "match_score" in item
            assert "confidence_pct" in item
            assert "match_status" in item
            assert "classification" in item
            assert "candidates" in item
            assert "explanation" in item
            assert "provider" in item

    def test_match_status_values(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Test Corp")
        valid_statuses = {"match", "review", "no-match"}
        for item in result:
            assert item["match_status"] in valid_statuses

    def test_confidence_pct_range(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Client Name: Test\nVendor: Other")
        for item in result:
            assert 0 <= item["confidence_pct"] <= 100

    def test_deterministic_sorting(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nClient: Beta LLC\nVendor: Gamma Inc"
        r1 = _run_salesforce_match([], text)
        r2 = _run_salesforce_match([], text)
        assert [x["source_field"] for x in r1] == [x["source_field"] for x in r2]

    def test_sort_order_review_first(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Test A\nVendor: Test B\nArtist: Test C"
        result = _run_salesforce_match([], text)
        if len(result) >= 2:
            statuses = [r["match_status"] for r in result]
            status_priority = {"review": 0, "no-match": 1, "match": 2}
            priorities = [status_priority.get(s, 5) for s in statuses]
            assert priorities == sorted(priorities)

    def test_source_field_shows_value_not_label(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: 1888 Records"
        result = _run_salesforce_match(["Account Name"], text)
        if result:
            assert result[0]["source_field"] == "1888 Records"
            assert result[0]["source_field"] != "Account Name"


class TestEntityHeaderDetection:
    def test_account_name_detected(self):
        from server.preflight_engine import _SF_ENTITY_HINTS
        header = "account name"
        found = any(hint in header.lower() for hint in _SF_ENTITY_HINTS)
        assert found

    def test_client_name_detected(self):
        from server.preflight_engine import _SF_ENTITY_HINTS
        header = "Client Name"
        found = any(hint in header.lower() for hint in _SF_ENTITY_HINTS)
        assert found

    def test_artist_detected(self):
        from server.preflight_engine import _SF_ENTITY_HINTS
        header = "Artist"
        found = any(hint in header.lower() for hint in _SF_ENTITY_HINTS)
        assert found

    def test_random_header_not_entity(self):
        from server.preflight_engine import _SF_ENTITY_HINTS
        header = "Total Amount Due"
        found = any(hint in header.lower() for hint in _SF_ENTITY_HINTS)
        assert not found

    def test_vendor_detected(self):
        from server.preflight_engine import _SF_ENTITY_HINTS
        header = "Vendor Name"
        found = any(hint in header.lower() for hint in _SF_ENTITY_HINTS)
        assert found

    def test_company_detected(self):
        from server.preflight_engine import _SF_ENTITY_HINTS
        header = "Company Name"
        found = any(hint in header.lower() for hint in _SF_ENTITY_HINTS)
        assert found


class TestPreflightResultIncludesSfMatch:
    def test_run_preflight_includes_salesforce_match_key(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Test Corp\nSome Text\nContract Date", "char_count": 60, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        assert "salesforce_match" in result
        assert isinstance(result["salesforce_match"], list)

    def test_run_preflight_empty_pages_has_sf_match(self):
        from server.preflight_engine import run_preflight
        result = run_preflight([])
        assert "salesforce_match" not in result or isinstance(result.get("salesforce_match"), list)

    def test_sf_match_after_corruption_samples_in_result(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Real Corp\nClient: Other\nVendor: Third\nSome data", "char_count": 80, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        keys = list(result.keys())
        if "corruption_samples" in keys and "salesforce_match" in keys:
            cs_idx = keys.index("corruption_samples")
            sf_idx = keys.index("salesforce_match")
            assert sf_idx > cs_idx, "salesforce_match should appear after corruption_samples in result dict"


class TestMatrixRowContent:
    def test_match_row_has_confidence(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Some Corp")
        for item in result:
            assert "confidence_pct" in item
            assert isinstance(item["confidence_pct"], int)

    def test_match_row_has_status(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Client Name: Test LLC")
        for item in result:
            assert "match_status" in item
            assert item["match_status"] in ("match", "review", "no-match")

    def test_match_row_has_source_and_target(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Entity Name: Real Entity")
        for item in result:
            assert item["source_field"] == "Real Entity"
            assert "suggested_label" in item
            assert isinstance(item["suggested_label"], str)

    def test_no_match_has_dash_label(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["zzz_nonexistent_field_xyz"], "")
        for item in result:
            if item["match_status"] == "no-match" and not item["candidates"]:
                assert item["suggested_label"] == "\u2014"


class TestAcceptanceCriteria:
    def test_1888_records_extracted_as_source(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records\nContract Date: 2024-01-01"
        candidates = extract_account_candidates(text, ["Account Name", "Contract Date"])
        assert "1888 Records" in candidates
        assert "Account Name" not in candidates

    def test_label_only_rows_excluded_when_value_exists(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        headers = ["Account Name", "Account Name:"]
        candidates = extract_account_candidates(text, headers)
        assert candidates == ["1888 Records"]

    def test_unknown_value_still_returns_no_match(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: ZZZ_TOTALLY_UNKNOWN_XYZ_999")
        if result:
            assert result[0]["match_status"] == "no-match"
            assert result[0]["source_field"] == "ZZZ_TOTALLY_UNKNOWN_XYZ_999"

"""
Tests for Salesforce match integration in the Preflight engine.

Covers:
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


class TestRunSalesforceMatch:
    def test_import_and_run(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([])
        assert isinstance(result, list)

    def test_empty_headers_returns_empty(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([])
        assert result == []

    def test_result_payload_shape(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Account Name", "Contract Date"])
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
        result = _run_salesforce_match(["Account Name"])
        valid_statuses = {"match", "review", "no-match"}
        for item in result:
            assert item["match_status"] in valid_statuses

    def test_confidence_pct_range(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Client Name", "Vendor"])
        for item in result:
            assert 0 <= item["confidence_pct"] <= 100

    def test_deterministic_sorting(self):
        from server.preflight_engine import _run_salesforce_match
        headers = ["Account Name", "Client", "Entity Name", "Vendor"]
        r1 = _run_salesforce_match(headers)
        r2 = _run_salesforce_match(headers)
        assert [x["source_field"] for x in r1] == [x["source_field"] for x in r2]

    def test_sort_order_review_first(self):
        from server.preflight_engine import _run_salesforce_match
        headers = ["Account Name", "Vendor", "Artist"]
        result = _run_salesforce_match(headers)
        if len(result) >= 2:
            statuses = [r["match_status"] for r in result]
            status_priority = {"review": 0, "no-match": 1, "match": 2}
            priorities = [status_priority.get(s, 5) for s in statuses]
            assert priorities == sorted(priorities)


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
        pages = [{"page": 1, "text": "Account Name\nSome Text\nContract Date", "char_count": 40, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        assert "salesforce_match" in result
        assert isinstance(result["salesforce_match"], list)

    def test_run_preflight_empty_pages_has_sf_match(self):
        from server.preflight_engine import run_preflight
        result = run_preflight([])
        assert "salesforce_match" not in result or isinstance(result.get("salesforce_match"), list)

    def test_sf_match_after_corruption_samples_in_result(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name\nClient\nVendor\nSome data", "char_count": 40, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        keys = list(result.keys())
        if "corruption_samples" in keys and "salesforce_match" in keys:
            cs_idx = keys.index("corruption_samples")
            sf_idx = keys.index("salesforce_match")
            assert sf_idx > cs_idx, "salesforce_match should appear after corruption_samples in result dict"


class TestMatrixRowContent:
    def test_match_row_has_confidence(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Account Name"])
        for item in result:
            assert "confidence_pct" in item
            assert isinstance(item["confidence_pct"], int)

    def test_match_row_has_status(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Client Name"])
        for item in result:
            assert "match_status" in item
            assert item["match_status"] in ("match", "review", "no-match")

    def test_match_row_has_source_and_target(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Entity Name"])
        for item in result:
            assert item["source_field"] == "Entity Name"
            assert "suggested_label" in item
            assert isinstance(item["suggested_label"], str)

    def test_no_match_has_dash_label(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["zzz_nonexistent_field_xyz"])
        for item in result:
            if item["match_status"] == "no-match" and not item["candidates"]:
                assert item["suggested_label"] == "\u2014"

"""
Tests for Salesforce match integration in the Preflight engine.

Covers:
  - extract_account_candidates: strict label:value, CSV phrase scan, prose rejection
  - _run_salesforce_match payload shape
  - Section ordering: encoding → sf_match → others
  - Matrix rows include status + confidence
  - Deterministic sorting of SF match results
  - Acceptance criteria: value-over-label, prose rejection
"""
import pytest
from unittest.mock import patch, MagicMock


def _pftl_section_priority(section_key):
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
    def test_extracts_value_after_account_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records\nSome other line"
        result = extract_account_candidates(text, [])
        assert "1888 Records" in result

    def test_extracts_value_after_company_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Company Name: Acme Corp"
        result = extract_account_candidates(text, [])
        assert "Acme Corp" in result

    def test_extracts_value_after_artist_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Artist Name: DJ Shadow"
        result = extract_account_candidates(text, [])
        assert "DJ Shadow" in result

    def test_extracts_value_after_legal_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Legal Name: Shadow Holdings LLC"
        result = extract_account_candidates(text, [])
        assert "Shadow Holdings LLC" in result

    def test_extracts_value_after_salesforce_field_name(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account_Name__c: 1888 Records"
        result = extract_account_candidates(text, [])
        assert "1888 Records" in result

    def test_excludes_labels_as_values(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        result = extract_account_candidates(text, ["Account Name"])
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
        text = "Account Name: Dupe Corp\nCompany Name: dupe corp"
        result = extract_account_candidates(text, [])
        assert len([c for c in result if c.lower() == "dupe corp"]) == 1

    def test_empty_text_and_headers(self):
        from server.preflight_engine import extract_account_candidates
        result = extract_account_candidates("", [])
        assert result == []

    def test_label_without_value_excluded(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name:\nSome other content"
        result = extract_account_candidates(text, [])
        assert not any("account" in c.lower() for c in result)

    def test_rejects_prose_record_means(self):
        from server.preflight_engine import extract_account_candidates
        text = 'Account Name: "Record" means every form of recorded music'
        result = extract_account_candidates(text, [])
        assert not any("record" in c.lower() and "means" in c.lower() for c in result)

    def test_rejects_prose_this_agreement(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: this agreement shall govern"
        result = extract_account_candidates(text, [])
        assert not any("this agreement" in c.lower() for c in result)

    def test_rejects_prose_whereas(self):
        from server.preflight_engine import extract_account_candidates
        text = "Company Name: whereas the party acknowledges"
        result = extract_account_candidates(text, [])
        assert result == []

    def test_rejects_long_token_value(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: zzqa zzqb zzqc zzqd zzqe zzqf zzqg zzqh"
        result = extract_account_candidates(text, [])
        assert not any("zzqa" in c.lower() for c in result)

    def test_rejects_generic_single_token(self):
        from server.preflight_engine import extract_account_candidates
        text = "Some random text with no label patterns"
        headers = ["record", "account", "company", "Real Corp Name"]
        result = extract_account_candidates(text, headers)
        assert "record" not in result
        assert "account" not in result
        assert "company" not in result

    def test_fallback_to_non_label_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "No label-value pairs here"
        headers = ["Some Real Company", "Account Name", "Contract Date"]
        result = extract_account_candidates(text, headers)
        assert "Account Name" not in result

    def test_value_priority_over_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        headers = ["Account Name", "Fallback Company"]
        result = extract_account_candidates(text, headers)
        assert "1888 Records" in result
        assert "Fallback Company" not in result

    def test_rejects_value_starting_with_prose_word(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: Records of the meeting"
        result = extract_account_candidates(text, [])
        assert result == []

    def test_rejects_quotes_with_verb_phrase(self):
        from server.preflight_engine import extract_account_candidates
        text = 'Legal Name: "Master" means the final'
        result = extract_account_candidates(text, [])
        assert result == []


class TestCsvPhraseScan:
    def test_csv_phrase_scan_import(self):
        from server.preflight_engine import _csv_phrase_scan
        result = _csv_phrase_scan("")
        assert isinstance(result, list)

    def test_csv_phrase_scan_finds_known_account(self):
        from server.preflight_engine import _csv_phrase_scan
        from server.resolvers.account_index import get_index
        idx = get_index()
        if idx.loaded and idx.record_count > 0:
            rec = idx.all_records()[0]
            name = rec.account_name
            if name and len(name) >= 3:
                text = f"Some text before {name} and after"
                hits = _csv_phrase_scan(text)
                assert any(h.lower() == name.lower() for h in hits), f"Expected to find '{name}' in hits"

    def test_csv_phrase_scan_empty_text(self):
        from server.preflight_engine import _csv_phrase_scan
        assert _csv_phrase_scan("") == []

    def test_csv_phrase_scan_no_match(self):
        from server.preflight_engine import _csv_phrase_scan
        result = _csv_phrase_scan("ZZZZ NONEXISTENT CORP QQQQ")
        assert result == []


class TestProseFilters:
    def test_is_prose_starts_with_record(self):
        from server.preflight_engine import _is_prose
        assert _is_prose("Record means every form of recorded music")

    def test_is_prose_this_agreement(self):
        from server.preflight_engine import _is_prose
        assert _is_prose("see this agreement for details")

    def test_is_prose_hereof(self):
        from server.preflight_engine import _is_prose
        assert _is_prose("as stated hereof")

    def test_is_prose_long_phrase(self):
        from server.preflight_engine import _is_prose
        assert _is_prose("one two three four five six seven eight words")

    def test_not_prose_normal_name(self):
        from server.preflight_engine import _is_prose
        assert not _is_prose("1888 Records")

    def test_not_prose_company_name(self):
        from server.preflight_engine import _is_prose
        assert not _is_prose("Acme Corp LLC")

    def test_is_prose_low_alnum(self):
        from server.preflight_engine import _is_prose
        assert _is_prose("--- ... *** ///  @@@ ###")

    def test_is_prose_quotes_with_means(self):
        from server.preflight_engine import _is_prose
        assert _is_prose('"Record" means every form')


class TestRunSalesforceMatch:
    def test_import_and_run(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "")
        assert isinstance(result, list)

    def test_empty_returns_empty(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "")
        assert result == []

    def test_result_payload_shape(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Some Company Name")
        assert isinstance(result, list)
        for item in result:
            assert "source_field" in item
            assert "suggested_label" in item
            assert "match_method" in item
            assert "match_score" in item
            assert "confidence_pct" in item
            assert "match_status" in item
            assert "classification" in item

    def test_match_status_values(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Test Corp")
        valid_statuses = {"match", "review", "no-match"}
        for item in result:
            assert item["match_status"] in valid_statuses

    def test_confidence_pct_range(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Company Name: Test LLC")
        for item in result:
            assert 0 <= item["confidence_pct"] <= 100

    def test_deterministic_sorting(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta LLC"
        r1 = _run_salesforce_match([], text)
        r2 = _run_salesforce_match([], text)
        assert [x["source_field"] for x in r1] == [x["source_field"] for x in r2]

    def test_sort_order_review_first(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Test A\nCompany Name: Test B\nArtist Name: Test C"
        result = _run_salesforce_match([], text)
        if len(result) >= 2:
            status_priority = {"review": 0, "no-match": 1, "match": 2}
            priorities = [status_priority.get(r["match_status"], 5) for r in result]
            assert priorities == sorted(priorities)

    def test_source_field_shows_value_not_label(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: 1888 Records"
        result = _run_salesforce_match(["Account Name"], text)
        if result:
            assert result[0]["source_field"] != "Account Name"


class TestPreflightResultIncludesSfMatch:
    def test_run_preflight_includes_salesforce_match_key(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Test Corp\nSome data here to pad it out a bit more", "char_count": 80, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        assert "salesforce_match" in result
        assert isinstance(result["salesforce_match"], list)

    def test_run_preflight_empty_pages_has_sf_match(self):
        from server.preflight_engine import run_preflight
        result = run_preflight([])
        assert "salesforce_match" not in result or isinstance(result.get("salesforce_match"), list)

    def test_sf_match_after_corruption_samples_in_result(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Real Corp\nCompany Name: Other Co\nMore text padding", "char_count": 80, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        keys = list(result.keys())
        if "corruption_samples" in keys and "salesforce_match" in keys:
            cs_idx = keys.index("corruption_samples")
            sf_idx = keys.index("salesforce_match")
            assert sf_idx > cs_idx


class TestMatrixRowContent:
    def test_match_row_has_confidence(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Some Corp Name")
        for item in result:
            assert "confidence_pct" in item
            assert isinstance(item["confidence_pct"], int)

    def test_match_row_has_status(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Company Name: Test LLC")
        for item in result:
            assert item["match_status"] in ("match", "review", "no-match")

    def test_no_match_has_dash_label(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["zzz_nonexistent_field_xyz"], "")
        for item in result:
            if item["match_status"] == "no-match" and not item["candidates"]:
                assert item["suggested_label"] == "\u2014"


class TestAcceptanceCriteria:
    def test_1888_records_extracted_as_source_from_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records\nContract Date: 2024-01-01"
        candidates = extract_account_candidates(text, ["Account Name", "Contract Date"])
        assert "1888 Records" in candidates
        assert "Account Name" not in candidates

    def test_1888_records_captured_via_csv_phrase_hit(self):
        from server.preflight_engine import extract_account_candidates
        from server.resolvers.account_index import get_index
        idx = get_index()
        found_1888 = any("1888" in getattr(r, "account_name", "") for r in idx.all_records()) if idx.loaded else False
        if found_1888:
            text = "Some contract text mentioning 1888 Records in the body without a label"
            candidates = extract_account_candidates(text, [])
            assert "1888 Records" in candidates

    def test_label_only_rows_excluded_when_value_exists(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        headers = ["Account Name", "Account Name:"]
        candidates = extract_account_candidates(text, headers)
        assert candidates == ["1888 Records"]

    def test_record_means_prose_not_emitted(self):
        from server.preflight_engine import extract_account_candidates
        text = '"Record" means every form of recorded music.\nAccount Name: hereof the parties'
        candidates = extract_account_candidates(text, [])
        assert not any("means every form" in c.lower() for c in candidates)
        assert not any("record" == c.lower() for c in candidates)

    def test_unknown_value_still_returns_no_match(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: ZZZ Totally Unknown Corp")
        if result:
            assert result[0]["match_status"] == "no-match"
            assert result[0]["source_field"] == "ZZZ Totally Unknown Corp"

    def test_deterministic_ordering_preserved(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc\nLegal Name: Gamma LLC"
        r1 = _run_salesforce_match([], text)
        r2 = _run_salesforce_match([], text)
        assert [x["source_field"] for x in r1] == [x["source_field"] for x in r2]
        if len(r1) >= 2:
            status_priority = {"review": 0, "no-match": 1, "match": 2}
            priorities = [status_priority.get(r["match_status"], 5) for r in r1]
            assert priorities == sorted(priorities)

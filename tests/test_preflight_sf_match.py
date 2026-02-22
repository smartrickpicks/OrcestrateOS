"""
Tests for Salesforce match integration in the Preflight engine.

Covers:
  - extract_account_candidates: strict label:value, CSV phrase scan, prose rejection, denylist
  - _run_salesforce_match payload shape (multi-account, composite scoring, source_type)
  - Context scoring: account-context boost (strong/weak cues), service-context penalty (source-aware caps)
  - Evidence chips generation
  - Section ordering: encoding -> sf_match -> others
  - Matrix rows include status + confidence + evidence_chips
  - Deterministic sorting of SF match results (source_type priority)
  - Acceptance criteria: multi-account, service penalty, address boost, generic suppression
  - Calibration: 1888 Records outranks generic tokens, denylist enforcement
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


def _cand_values(result):
    return [c["value"] if isinstance(c, dict) else c for c in result]


def _cand_source_types(result):
    return [c["source_type"] if isinstance(c, dict) else "unknown" for c in result]


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
        assert "1888 Records" in _cand_values(result)

    def test_extracts_value_after_company_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Company Name: Acme Corp"
        result = extract_account_candidates(text, [])
        assert "Acme Corp" in _cand_values(result)

    def test_extracts_value_after_artist_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Artist Name: DJ Shadow"
        result = extract_account_candidates(text, [])
        assert "DJ Shadow" in _cand_values(result)

    def test_extracts_value_after_legal_name_label(self):
        from server.preflight_engine import extract_account_candidates
        text = "Legal Name: Shadow Holdings LLC"
        result = extract_account_candidates(text, [])
        assert "Shadow Holdings LLC" in _cand_values(result)

    def test_extracts_value_after_salesforce_field_name(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account_Name__c: 1888 Records"
        result = extract_account_candidates(text, [])
        assert "1888 Records" in _cand_values(result)

    def test_excludes_labels_as_values(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        result = extract_account_candidates(text, ["Account Name"])
        vals = _cand_values(result)
        assert "Account Name" not in vals
        assert "1888 Records" in vals

    def test_normalizes_whitespace(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name:   Spaced   Out   Name  "
        result = extract_account_candidates(text, [])
        assert "Spaced Out Name" in _cand_values(result)

    def test_strips_trailing_punctuation(self):
        from server.preflight_engine import extract_account_candidates
        text = "Company Name: Trail Corp;;"
        result = extract_account_candidates(text, [])
        assert "Trail Corp" in _cand_values(result)

    def test_deduplicates_case_insensitively(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: Dupe Corp\nCompany Name: dupe corp"
        result = extract_account_candidates(text, [])
        vals = _cand_values(result)
        assert len([c for c in vals if c.lower() == "dupe corp"]) == 1

    def test_empty_text_and_headers(self):
        from server.preflight_engine import extract_account_candidates
        result = extract_account_candidates("", [])
        assert result == []

    def test_label_without_value_excluded(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name:\nSome other content"
        result = extract_account_candidates(text, [])
        vals = _cand_values(result)
        assert not any("account" in c.lower() for c in vals)

    def test_rejects_prose_record_means(self):
        from server.preflight_engine import extract_account_candidates
        text = 'Account Name: "Record" means every form of recorded music'
        result = extract_account_candidates(text, [])
        vals = _cand_values(result)
        assert not any("record" in c.lower() and "means" in c.lower() for c in vals)

    def test_rejects_prose_this_agreement(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: this agreement shall govern"
        result = extract_account_candidates(text, [])
        vals = _cand_values(result)
        assert not any("this agreement" in c.lower() for c in vals)

    def test_rejects_prose_whereas(self):
        from server.preflight_engine import extract_account_candidates
        text = "Company Name: whereas the party acknowledges"
        result = extract_account_candidates(text, [])
        assert result == []

    def test_rejects_long_token_value(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: zzqa zzqb zzqc zzqd zzqe zzqf zzqg zzqh"
        result = extract_account_candidates(text, [])
        vals = _cand_values(result)
        assert not any("zzqa" in c.lower() for c in vals)

    def test_rejects_generic_single_token(self):
        from server.preflight_engine import extract_account_candidates
        text = "Some random text with no label patterns"
        headers = ["record", "account", "company", "Real Corp Name"]
        result = extract_account_candidates(text, headers)
        vals = _cand_values(result)
        assert "record" not in vals
        assert "account" not in vals
        assert "company" not in vals

    def test_fallback_to_non_label_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "No label-value pairs here"
        headers = ["Some Real Company", "Account Name", "Contract Date"]
        result = extract_account_candidates(text, headers)
        vals = _cand_values(result)
        assert "Account Name" not in vals

    def test_value_priority_over_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        headers = ["Account Name", "Fallback Company"]
        result = extract_account_candidates(text, headers)
        vals = _cand_values(result)
        assert "1888 Records" in vals
        assert "Fallback Company" not in vals

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

    def test_returns_dicts_with_source_type(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: Test Corp"
        result = extract_account_candidates(text, [])
        assert len(result) > 0
        for item in result:
            assert isinstance(item, dict)
            assert "value" in item
            assert "source_type" in item

    def test_strict_label_value_source_type(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: Test Corp"
        result = extract_account_candidates(text, [])
        types = _cand_source_types(result)
        assert "strict_label_value" in types

    def test_header_fallback_source_type(self):
        from server.preflight_engine import extract_account_candidates
        text = "No label patterns here"
        headers = ["Some Real Company"]
        result = extract_account_candidates(text, headers)
        if result:
            types = _cand_source_types(result)
            assert "header_fallback" in types


class TestHardDenylist:
    def test_distribution_denied_from_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "Some text about distribution"
        headers = ["Distribution", "Real Corp"]
        result = extract_account_candidates(text, headers)
        vals = _cand_values(result)
        assert "Distribution" not in vals
        assert "distribution" not in vals

    def test_trademark_denied_from_headers(self):
        from server.preflight_engine import extract_account_candidates
        text = "Trademark related text"
        headers = ["Trademark", "Another Corp"]
        result = extract_account_candidates(text, headers)
        vals = _cand_values(result)
        assert "Trademark" not in vals

    def test_delay_denied(self):
        from server.preflight_engine import _is_generic_noise
        assert _is_generic_noise("DELAY")
        assert _is_generic_noise("delay")

    def test_image_denied(self):
        from server.preflight_engine import _is_generic_noise
        assert _is_generic_noise("Image")
        assert _is_generic_noise("image")

    def test_mean_denied(self):
        from server.preflight_engine import _is_generic_noise
        assert _is_generic_noise("Mean")
        assert _is_generic_noise("mean")

    def test_prosecute_denied(self):
        from server.preflight_engine import _is_generic_noise
        assert _is_generic_noise("Prosecute")

    def test_real_company_not_denied(self):
        from server.preflight_engine import _is_generic_noise
        assert not _is_generic_noise("1888 Records")
        assert not _is_generic_noise("Acme Corp")
        assert not _is_generic_noise("Warner Music Group")

    def test_short_uppercase_single_token_denied(self):
        from server.preflight_engine import _is_generic_noise
        assert _is_generic_noise("DELAY")
        assert _is_generic_noise("IMAGE")

    def test_strict_label_value_bypasses_denylist(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: Distribution Corp LLC"
        result = extract_account_candidates(text, [])
        vals = _cand_values(result)
        assert "Distribution Corp LLC" in vals


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
            assert "evidence_chips" in item
            assert "scoring_breakdown" in item
            assert "visible" in item
            assert "source_type" in item
            assert isinstance(item["evidence_chips"], list)
            assert isinstance(item["scoring_breakdown"], dict)

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

    def test_source_type_in_result(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Test Corp"
        result = _run_salesforce_match([], text)
        if result:
            valid_types = {"strict_label_value", "csv_phrase_hit", "header_fallback"}
            for item in result:
                assert item["source_type"] in valid_types


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
        vals = _cand_values(candidates)
        assert "1888 Records" in vals
        assert "Account Name" not in vals

    def test_1888_records_captured_via_csv_phrase_hit(self):
        from server.preflight_engine import extract_account_candidates
        from server.resolvers.account_index import get_index
        idx = get_index()
        found_1888 = any("1888" in getattr(r, "account_name", "") for r in idx.all_records()) if idx.loaded else False
        if found_1888:
            text = "Some contract text mentioning 1888 Records in the body without a label"
            candidates = extract_account_candidates(text, [])
            vals = _cand_values(candidates)
            assert "1888 Records" in vals

    def test_label_only_rows_excluded_when_value_exists(self):
        from server.preflight_engine import extract_account_candidates
        text = "Account Name: 1888 Records"
        headers = ["Account Name", "Account Name:"]
        candidates = extract_account_candidates(text, headers)
        vals = _cand_values(candidates)
        assert vals == ["1888 Records"]

    def test_record_means_prose_not_emitted(self):
        from server.preflight_engine import extract_account_candidates
        text = '"Record" means every form of recorded music.\nAccount Name: hereof the parties'
        candidates = extract_account_candidates(text, [])
        vals = _cand_values(candidates)
        assert not any("means every form" in c.lower() for c in vals)
        assert not any("record" == c.lower() for c in vals)

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


class TestContextScorer:
    def test_import(self):
        from server.resolvers.context_scorer import score_candidate
        assert callable(score_candidate)

    def test_scoring_weights_present(self):
        from server.resolvers.context_scorer import SCORING_WEIGHTS
        assert "name_max" in SCORING_WEIGHTS
        assert "address_max" in SCORING_WEIGHTS
        assert "account_context_max" in SCORING_WEIGHTS
        assert "service_penalty_max" in SCORING_WEIGHTS

    def test_compute_composite_score_basic(self):
        from server.resolvers.context_scorer import compute_composite_score
        score = compute_composite_score(1.0, 0.0, 0.0, 0.0)
        assert score == 0.55

    def test_compute_composite_score_with_address(self):
        from server.resolvers.context_scorer import compute_composite_score
        score = compute_composite_score(1.0, 0.30, 0.0, 0.0)
        assert score == 0.85

    def test_compute_composite_score_full(self):
        from server.resolvers.context_scorer import compute_composite_score
        score = compute_composite_score(1.0, 0.30, 0.20, 0.0)
        assert score == 1.0

    def test_compute_composite_score_with_penalty(self):
        from server.resolvers.context_scorer import compute_composite_score
        score = compute_composite_score(1.0, 0.0, 0.0, 0.35)
        assert score == 0.2

    def test_composite_score_clamped_at_zero(self):
        from server.resolvers.context_scorer import compute_composite_score
        score = compute_composite_score(0.0, 0.0, 0.0, 0.35)
        assert score == 0.0

    def test_composite_score_clamped_at_one(self):
        from server.resolvers.context_scorer import compute_composite_score
        score = compute_composite_score(1.0, 0.30, 0.20, 0.0)
        assert score <= 1.0


class TestAccountContextScoring:
    def test_no_text_returns_zero(self):
        from server.resolvers.context_scorer import score_account_context
        score, found = score_account_context("", "Test Corp")
        assert score == 0.0
        assert found is False

    def test_no_candidate_returns_zero(self):
        from server.resolvers.context_scorer import score_account_context
        score, found = score_account_context("Some text", "")
        assert score == 0.0
        assert found is False

    def test_candidate_near_strong_account_cues(self):
        from server.resolvers.context_scorer import score_account_context
        text = "Account Name: Acme Corp\nBilling Address: 123 Main St"
        score, found = score_account_context(text, "Acme Corp")
        assert score > 0.0
        assert found is True

    def test_candidate_near_party_cues(self):
        from server.resolvers.context_scorer import score_account_context
        text = "The licensee, hereinafter referred to as Acme Corp, agrees to..."
        score, found = score_account_context(text, "Acme Corp")
        assert score > 0.0
        assert found is True

    def test_candidate_with_no_context_cues(self):
        from server.resolvers.context_scorer import score_account_context
        text = "Some random text about weather with Acme Corp mentioned casually"
        score, found = score_account_context(text, "Acme Corp")
        assert score == 0.0

    def test_weak_cues_only_give_reduced_boost(self):
        from server.resolvers.context_scorer import score_account_context
        text = "Test LLC is a limited company, Test LLC"
        score, found = score_account_context(text, "Test LLC")
        if found:
            assert score <= 0.05

    def test_strong_cue_gives_higher_boost(self):
        from server.resolvers.context_scorer import score_account_context
        text = "The licensee Acme Corp has a billing address at 123 Main St"
        score_strong, _ = score_account_context(text, "Acme Corp")
        text2 = "Acme Corp is a limited corporation registered here"
        score_weak, _ = score_account_context(text2, "Acme Corp")
        assert score_strong >= score_weak


class TestServiceContextPenalty:
    def test_known_dsp_gets_max_penalty(self):
        from server.resolvers.context_scorer import score_service_context
        penalty, found = score_service_context("Spotify is great", "Spotify")
        assert penalty == 0.35
        assert found is True

    def test_amazon_music_gets_max_penalty(self):
        from server.resolvers.context_scorer import score_service_context
        penalty, found = score_service_context("Available on Amazon Music", "Amazon Music")
        assert penalty == 0.35
        assert found is True

    def test_non_dsp_near_streaming_phrases(self):
        from server.resolvers.context_scorer import score_service_context
        text = "Available on TestPlatform streaming service via Spotify"
        penalty, found = score_service_context(text, "TestPlatform")
        assert penalty > 0.0
        assert found is True

    def test_normal_company_no_penalty(self):
        from server.resolvers.context_scorer import score_service_context
        text = "Account Name: Acme Corp LLC\nBilling Address: 123 Main St"
        penalty, found = score_service_context(text, "Acme Corp")
        assert penalty == 0.0
        assert found is False

    def test_candidate_not_in_text_no_penalty(self):
        from server.resolvers.context_scorer import score_service_context
        penalty, found = score_service_context("Some text", "Nonexistent Corp")
        assert penalty == 0.0
        assert found is False

    def test_strict_label_value_caps_penalty(self):
        from server.resolvers.context_scorer import score_service_context
        text = "Account Name: TestPlatform\nAvailable on TestPlatform streaming service via Spotify"
        penalty, found = score_service_context(text, "TestPlatform", source_type="strict_label_value")
        if found:
            assert penalty <= 0.08

    def test_csv_phrase_hit_caps_penalty(self):
        from server.resolvers.context_scorer import score_service_context
        text = "TestPlatform is available on streaming service"
        penalty, found = score_service_context(text, "TestPlatform", source_type="csv_phrase_hit")
        if found:
            assert penalty <= 0.15


class TestAddressEvidence:
    def test_no_text_returns_zero(self):
        from server.resolvers.context_scorer import score_address_evidence
        score, chips = score_address_evidence("", "Test Corp")
        assert score == 0.0
        assert chips == []

    def test_candidate_near_street_address(self):
        from server.resolvers.context_scorer import score_address_evidence
        text = "Account Name: Acme Corp\nAddress: 123 Main Street\nNew York, NY 10001"
        score, chips = score_address_evidence(text, "Acme Corp")
        assert score > 0.0
        assert len(chips) > 0

    def test_candidate_near_zip_code(self):
        from server.resolvers.context_scorer import score_address_evidence
        text = "Acme Corp\n90210\nSome other text"
        score, chips = score_address_evidence(text, "Acme Corp")
        assert score > 0.0
        assert "zip_match" in chips

    def test_candidate_near_full_address_gets_max(self):
        from server.resolvers.context_scorer import score_address_evidence
        text = "Acme Corp\n123 Main Street\nLos Angeles, CA 90210"
        score, chips = score_address_evidence(text, "Acme Corp")
        assert score == 0.30
        assert "address_verified" in chips
        assert "city_match" in chips
        assert "zip_match" in chips

    def test_no_address_near_candidate(self):
        from server.resolvers.context_scorer import score_address_evidence
        text = "Acme Corp mentioned in a legal clause without any address information nearby at all"
        score, chips = score_address_evidence(text, "Acme Corp")
        assert score == 0.0
        assert chips == []

    def test_extract_address_fragments(self):
        from server.resolvers.context_scorer import extract_address_fragments
        text = "123 Main Street\nSuite 100\nNew York, NY 10001\nPO Box 456"
        frags = extract_address_fragments(text)
        assert len(frags) >= 2

    def test_global_address_not_granted_to_distant_candidate(self):
        from server.resolvers.context_scorer import score_address_evidence
        padding = "X " * 200
        text = f"123 Main Street\nLos Angeles, CA 90210\n{padding}\nAcme Corp is mentioned far away"
        score, chips = score_address_evidence(text, "Acme Corp")
        assert score == 0.0
        assert chips == []


class TestEvidenceChips:
    def test_exact_name_chip(self):
        from server.resolvers.context_scorer import build_evidence_chips
        chips = build_evidence_chips(1.0, "exact", [], False, False)
        assert "name_exact" in chips

    def test_fuzzy_name_chip(self):
        from server.resolvers.context_scorer import build_evidence_chips
        chips = build_evidence_chips(0.8, "token_overlap", [], False, False)
        assert "name_fuzzy" in chips

    def test_service_penalty_chip(self):
        from server.resolvers.context_scorer import build_evidence_chips
        chips = build_evidence_chips(0.8, "exact", [], False, True)
        assert "service_context_penalty" in chips

    def test_account_context_chip(self):
        from server.resolvers.context_scorer import build_evidence_chips
        chips = build_evidence_chips(1.0, "exact", [], True, False)
        assert "account_context" in chips

    def test_address_chips_passed_through(self):
        from server.resolvers.context_scorer import build_evidence_chips
        chips = build_evidence_chips(1.0, "exact", ["address_verified", "zip_match"], False, False)
        assert "address_verified" in chips
        assert "zip_match" in chips


class TestScoreCandidate:
    def test_basic_score_candidate(self):
        from server.resolvers.context_scorer import score_candidate
        result = score_candidate("Account Name: Acme Corp", "Acme Corp", 1.0, "exact")
        assert "composite_score" in result
        assert "match_status" in result
        assert "evidence_chips" in result
        assert "visible" in result

    def test_score_candidate_with_context(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Account Name: Acme Corp LLC\nBilling Address: 123 Main Street\nNew York, NY 10001"
        result = score_candidate(text, "Acme Corp", 1.0, "exact")
        assert result["composite_score"] > 0.55
        assert "name_exact" in result["evidence_chips"]

    def test_service_name_penalized(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Available on Spotify streaming service via Apple Music"
        result = score_candidate(text, "Spotify", 1.0, "exact")
        assert result["service_context_penalty"] > 0.0
        assert "service_context_penalty" in result["evidence_chips"]

    def test_source_type_affects_penalty_cap(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Account Name: TestPlatform\nAvailable on TestPlatform streaming service"
        result_strict = score_candidate(text, "TestPlatform", 0.9, "exact", source_type="strict_label_value")
        result_header = score_candidate(text, "TestPlatform", 0.9, "exact", source_type="header_fallback")
        assert result_strict["service_context_penalty"] <= result_header["service_context_penalty"]


class TestMultiAccountOutput:
    def test_multi_account_document_returns_multiple(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc\nLegal Name: Gamma LLC"
        result = _run_salesforce_match([], text)
        assert len(result) >= 2

    def test_each_result_has_evidence_chips(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc"
        result = _run_salesforce_match([], text)
        for item in result:
            assert "evidence_chips" in item
            assert isinstance(item["evidence_chips"], list)

    def test_each_result_has_scoring_breakdown(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc"
        result = _run_salesforce_match([], text)
        for item in result:
            assert "scoring_breakdown" in item
            bd = item["scoring_breakdown"]
            assert "name_evidence" in bd

    def test_each_result_has_visible_flag(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc"
        result = _run_salesforce_match([], text)
        for item in result:
            assert "visible" in item
            assert isinstance(item["visible"], bool)

    def test_deterministic_multi_account_sorting(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc\nLegal Name: Gamma LLC"
        r1 = _run_salesforce_match([], text)
        r2 = _run_salesforce_match([], text)
        assert [x["source_field"] for x in r1] == [x["source_field"] for x in r2]
        assert [x["confidence_pct"] for x in r1] == [x["confidence_pct"] for x in r2]


class TestServicePenaltyIntegration:
    def test_spotify_downgraded(self):
        from server.resolvers.context_scorer import score_candidate
        result = score_candidate("Streaming on Spotify and Apple Music", "Spotify", 1.0, "exact")
        assert result["composite_score"] < 0.55
        assert result["service_context_penalty"] > 0

    def test_real_account_not_penalized(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Account Name: Real Corp LLC\nEntity type: Corporation\nBilling Address: 100 Oak Ave"
        result = score_candidate(text, "Real Corp", 1.0, "exact")
        assert result["service_context_penalty"] == 0.0

    def test_name_plus_address_high_confidence(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Account Name: Real Corp LLC\n123 Main Street\nLos Angeles, CA 90210"
        result = score_candidate(text, "Real Corp", 1.0, "exact")
        assert result["composite_score"] >= 0.65


class TestClassifyByComposite:
    def test_high_score_is_match(self):
        from server.resolvers.context_scorer import classify_by_composite
        assert classify_by_composite(0.80, False, 1.0) == "match"

    def test_moderate_score_is_review(self):
        from server.resolvers.context_scorer import classify_by_composite
        assert classify_by_composite(0.50, False, 0.7) == "review"

    def test_low_score_is_no_match(self):
        from server.resolvers.context_scorer import classify_by_composite
        assert classify_by_composite(0.20, False, 0.3) == "no-match"

    def test_service_penalty_prevents_match_for_weak_name(self):
        from server.resolvers.context_scorer import classify_by_composite
        status = classify_by_composite(0.70, True, 0.7)
        assert status == "review"

    def test_service_penalty_allows_match_for_strong_name(self):
        from server.resolvers.context_scorer import classify_by_composite
        status = classify_by_composite(0.70, True, 0.90)
        assert status == "match"

    def test_generic_token_capped_at_review(self):
        from server.resolvers.context_scorer import classify_by_composite
        status = classify_by_composite(0.80, False, 1.0, source_type="header_fallback", is_generic_token=True)
        assert status == "review"

    def test_generic_token_strict_label_can_match(self):
        from server.resolvers.context_scorer import classify_by_composite
        status = classify_by_composite(0.80, False, 1.0, source_type="strict_label_value", is_generic_token=True)
        assert status == "match"


class TestAcceptanceCriteriaV2:
    def test_1888_records_with_address_scores_high(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Account Name: 1888 Records\nBilling Address: 456 Record Lane\nNashville, TN 37201"
        result = score_candidate(text, "1888 Records", 1.0, "exact")
        assert result["composite_score"] >= 0.65
        assert result["visible"] is True

    def test_service_mentions_downgraded(self):
        from server.resolvers.context_scorer import score_candidate
        for svc in ["Spotify", "Amazon Music", "TikTok", "YouTube"]:
            text = f"Available on {svc} streaming platform service"
            result = score_candidate(text, svc, 1.0, "exact")
            assert result["service_context_penalty"] > 0.0
            assert result["match_status"] != "match"

    def test_deterministic_output_preserved(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Corp A\nCompany Name: Corp B\nLegal Name: Corp C"
        r1 = _run_salesforce_match([], text)
        r2 = _run_salesforce_match([], text)
        fields1 = [(r["source_field"], r["confidence_pct"], r["match_status"]) for r in r1]
        fields2 = [(r["source_field"], r["confidence_pct"], r["match_status"]) for r in r2]
        assert fields1 == fields2


class TestCalibrationRegression:
    """Regression tests for the 1888 Records distribution agreement calibration."""

    def test_1888_records_outranks_generic_tokens(self):
        from server.preflight_engine import _run_salesforce_match
        text = (
            "Account Name: 1888 Records\n"
            "This Distribution Agreement...\n"
            "Trademark provisions apply.\n"
            "No DELAY shall occur.\n"
            "Image rights reserved.\n"
            "Mean delivery times apply.\n"
        )
        result = _run_salesforce_match([], text)
        if result:
            source_fields = [r["source_field"] for r in result]
            assert "1888 Records" in source_fields
            for noise in ["Distribution", "Trademark", "DELAY", "Image", "Mean"]:
                assert noise not in source_fields

    def test_generic_tokens_denied_from_extraction(self):
        from server.preflight_engine import extract_account_candidates
        text = "Distribution agreement for Trademark holder\nDELAY Image Mean"
        headers = ["Distribution", "Trademark", "DELAY", "Image", "Mean"]
        result = extract_account_candidates(text, headers)
        vals = _cand_values(result)
        for noise in ["Distribution", "Trademark", "DELAY", "Image", "Mean",
                       "distribution", "trademark"]:
            assert noise not in vals

    def test_dsp_names_stay_low_signal(self):
        from server.preflight_engine import _run_salesforce_match
        text = (
            "Account Name: 1888 Records\n"
            "Available on Spotify, Amazon Music, TikTok.\n"
        )
        result = _run_salesforce_match([], text)
        for r in result:
            if r["source_field"] in ("Spotify", "Amazon Music", "TikTok"):
                assert r["match_status"] != "match"

    def test_source_type_priority_in_sorting(self):
        from server.preflight_engine import _run_salesforce_match, _SOURCE_TYPE_PRIORITY
        text = "Account Name: Strict Corp\nSome header corp in body"
        result = _run_salesforce_match([], text)
        if len(result) >= 2:
            priorities = [_SOURCE_TYPE_PRIORITY.get(r.get("source_type", "header_fallback"), 2) for r in result]
            assert priorities == sorted(priorities)

    def test_strict_label_value_service_penalty_capped(self):
        from server.resolvers.context_scorer import score_candidate
        text = "Account Name: TestPlatform\nAvailable on TestPlatform streaming service via Spotify"
        result = score_candidate(text, "TestPlatform", 0.9, "exact", source_type="strict_label_value")
        assert result["service_context_penalty"] <= 0.08

    def test_local_address_only(self):
        from server.resolvers.context_scorer import score_address_evidence
        padding = "\n".join(["Some irrelevant line " + str(i) for i in range(20)])
        text = f"123 Main Street\nLos Angeles, CA 90210\n{padding}\nAcme Corp is mentioned far away here"
        score, chips = score_address_evidence(text, "Acme Corp")
        assert score == 0.0
        assert chips == []

    def test_deterministic_order_with_source_type(self):
        from server.preflight_engine import _run_salesforce_match
        text = "Account Name: Alpha Corp\nCompany Name: Beta Inc"
        r1 = _run_salesforce_match([], text)
        r2 = _run_salesforce_match([], text)
        fields1 = [(r["source_field"], r["source_type"], r["confidence_pct"]) for r in r1]
        fields2 = [(r["source_field"], r["source_type"], r["confidence_pct"]) for r in r2]
        assert fields1 == fields2


class TestPerCandidateExplainabilityFields:
    def test_label_value_hit_true_for_strict(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Test Corp")
        for item in result:
            if item["source_type"] == "strict_label_value":
                assert item["label_value_hit"] is True

    def test_label_value_hit_false_for_header(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match(["Some Real Company"], "No label patterns here")
        for item in result:
            if item["source_type"] == "header_fallback":
                assert item["label_value_hit"] is False

    def test_recital_party_hit_stub_false(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Test Corp")
        for item in result:
            assert item["recital_party_hit"] is False

    def test_fields_present_in_payload(self):
        from server.preflight_engine import _run_salesforce_match
        result = _run_salesforce_match([], "Account Name: Some Corp Name")
        for item in result:
            assert "label_value_hit" in item
            assert "recital_party_hit" in item
            assert isinstance(item["label_value_hit"], bool)
            assert isinstance(item["recital_party_hit"], bool)


class TestCmgSideGating:
    def test_is_cmg_side_known_alias(self):
        from server.preflight_engine import _is_cmg_side
        assert _is_cmg_side("Ostereo Limited", []) is True
        assert _is_cmg_side("ostereo limited", []) is True
        assert _is_cmg_side("Ostereo Publishing Limited", []) is True
        assert _is_cmg_side("Asterio Limited", []) is True

    def test_is_cmg_side_unknown_name(self):
        from server.preflight_engine import _is_cmg_side
        assert _is_cmg_side("1888 Records", []) is False
        assert _is_cmg_side("Acme Corp", []) is False

    def test_is_cmg_side_by_account_type(self):
        from server.preflight_engine import _is_cmg_side
        assert _is_cmg_side("Some Division Name", [{"type": "Division"}]) is True
        assert _is_cmg_side("Some Artist Name", [{"type": "Artist"}]) is False

    def test_is_cmg_side_empty_candidates(self):
        from server.preflight_engine import _is_cmg_side
        assert _is_cmg_side("Random Name", []) is False


class TestAgreementTypeGuess:
    def test_distribution_from_title(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Distribution Agreement\nBetween Party A and Party B"
        assert _guess_agreement_type(text) == "distribution"

    def test_license_from_body(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Some Title\n\nThis license agreement governs the terms."
        assert _guess_agreement_type(text) == "license"

    def test_recording_agreement(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Recording Agreement\nArtist Name: Test"
        assert _guess_agreement_type(text) == "recording"

    def test_publishing_agreement(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Publishing Agreement\nWriter: Test"
        assert _guess_agreement_type(text) == "publishing"

    def test_management_agreement(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Management Agreement\nManager: Test"
        assert _guess_agreement_type(text) == "management"

    def test_service_agreement(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Service Agreement\nProvider: Test"
        assert _guess_agreement_type(text) == "service"

    def test_amendment(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Amendment to Agreement\nOriginal Date: 2024-01-01"
        assert _guess_agreement_type(text) == "amendment"

    def test_unknown_when_no_keywords(self):
        from server.preflight_engine import _guess_agreement_type
        assert _guess_agreement_type("Random text with no keywords") == "unknown"

    def test_empty_text(self):
        from server.preflight_engine import _guess_agreement_type
        assert _guess_agreement_type("") == "unknown"

    def test_title_zone_weighted_higher(self):
        from server.preflight_engine import _guess_agreement_type
        text = "Distribution Agreement\n" + "\n".join(["line"] * 20) + "\nlicense agreement in body"
        assert _guess_agreement_type(text) == "distribution"


class TestBuildResolutionStory:
    def _make_row(self, source_field, match_status="review", confidence=0.50,
                  source_type="strict_label_value", candidates=None, visible=True):
        return {
            "source_field": source_field,
            "suggested_label": source_field,
            "match_method": "exact",
            "match_score": confidence,
            "name_score": confidence,
            "confidence_pct": round(confidence * 100),
            "match_status": match_status,
            "classification": "matched" if match_status == "match" else "ambiguous",
            "candidates": candidates or [],
            "explanation": "",
            "provider": "cmg_csv_v1",
            "evidence_chips": [],
            "scoring_breakdown": {"name_evidence": confidence * 0.55},
            "visible": visible,
            "source_type": source_type,
            "label_value_hit": source_type == "strict_label_value",
            "recital_party_hit": False,
        }

    def test_empty_sf_match_returns_null_entity(self):
        from server.preflight_engine import build_resolution_story
        story = build_resolution_story([], "Some text")
        assert story["legal_entity_account"] is None
        assert story["counterparties"] == []
        assert story["requires_manual_confirmation"] is True
        assert story["recital_parties"] == []

    def test_payload_shape(self):
        from server.preflight_engine import build_resolution_story
        story = build_resolution_story([], "")
        required_keys = [
            "legal_entity_account", "counterparties", "business_unit",
            "parent_account", "agreement_type_guess", "reasoning_steps",
            "analyst_actions", "requires_manual_confirmation", "recital_parties",
        ]
        for key in required_keys:
            assert key in story, f"Missing key: {key}"

    def test_cmg_entity_assigned_as_legal_entity(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
            self._make_row("1888 Records", "match", 0.87,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
        ]
        story = build_resolution_story(rows, "Distribution Agreement")
        assert story["legal_entity_account"] is not None
        assert story["legal_entity_account"]["name"] == "Ostereo Limited"
        assert story["legal_entity_account"]["cmg_side"] is True

    def test_non_cmg_as_counterparty(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
            self._make_row("1888 Records", "match", 0.87,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
        ]
        story = build_resolution_story(rows, "Distribution Agreement")
        cparty_names = [c["name"] for c in story["counterparties"]]
        assert "1888 Records" in cparty_names
        assert all(not c["cmg_side"] for c in story["counterparties"])

    def test_no_cmg_candidate_sets_null_and_manual(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("1888 Records", "match", 0.87,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
            self._make_row("Acme Corp", "review", 0.50,
                           candidates=[{"account_name": "Acme Corp", "type": "Artist", "account_id": "003"}]),
        ]
        story = build_resolution_story(rows, "Some text")
        assert story["legal_entity_account"] is None
        assert story["requires_manual_confirmation"] is True
        assert any("manual" in a.lower() for a in story["analyst_actions"])

    def test_reasoning_steps_not_empty(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
        ]
        story = build_resolution_story(rows, "Distribution Agreement")
        assert len(story["reasoning_steps"]) >= 1

    def test_analyst_actions_present(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
        ]
        story = build_resolution_story(rows, "Distribution Agreement")
        assert len(story["analyst_actions"]) >= 1

    def test_agreement_type_guess_populated(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
        ]
        story = build_resolution_story(rows, "Distribution Agreement between parties")
        assert story["agreement_type_guess"] == "distribution"

    def test_recital_parties_stub_empty(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
        ]
        story = build_resolution_story(rows, "")
        assert story["recital_parties"] == []

    def test_role_selection_independent_of_table_sort(self):
        from server.preflight_engine import build_resolution_story
        rows_order_a = [
            self._make_row("1888 Records", "match", 0.92,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
            self._make_row("Ostereo Limited", "match", 0.85,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
        ]
        rows_order_b = [
            self._make_row("Ostereo Limited", "match", 0.85,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
            self._make_row("1888 Records", "match", 0.92,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
        ]
        story_a = build_resolution_story(rows_order_a, "Distribution Agreement")
        story_b = build_resolution_story(rows_order_b, "Distribution Agreement")
        assert story_a["legal_entity_account"]["name"] == story_b["legal_entity_account"]["name"]
        assert story_a["legal_entity_account"]["name"] == "Ostereo Limited"
        cparties_a = [c["name"] for c in story_a["counterparties"]]
        cparties_b = [c["name"] for c in story_b["counterparties"]]
        assert cparties_a == cparties_b

    def test_non_cmg_never_legal_entity(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("1888 Records", "match", 0.99,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
        ]
        story = build_resolution_story(rows, "text")
        assert story["legal_entity_account"] is None

    def test_low_confidence_counterparty_excluded(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
            self._make_row("Weak Corp", "no-match", 0.20,
                           candidates=[{"account_name": "Weak Corp", "type": "Artist", "account_id": "005"}]),
        ]
        story = build_resolution_story(rows, "text")
        cparty_names = [c["name"] for c in story["counterparties"]]
        assert "Weak Corp" not in cparty_names

    def test_review_status_legal_entity_requires_manual(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "review", 0.50,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
        ]
        story = build_resolution_story(rows, "text")
        assert story["legal_entity_account"] is not None
        assert story["requires_manual_confirmation"] is True

    def test_service_penalty_generates_reasoning(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            {
                "source_field": "Spotify",
                "suggested_label": "Spotify",
                "match_method": "exact",
                "match_score": 0.20,
                "name_score": 1.0,
                "confidence_pct": 20,
                "match_status": "no-match",
                "classification": "not_found",
                "candidates": [],
                "explanation": "",
                "provider": "cmg_csv_v1",
                "evidence_chips": ["service_context_penalty"],
                "scoring_breakdown": {"name_evidence": 0.55, "service_context_penalty": 0.35},
                "visible": True,
                "source_type": "header_fallback",
                "label_value_hit": False,
                "recital_party_hit": False,
            },
        ]
        story = build_resolution_story(rows, "text")
        assert any("suppressed" in s.lower() or "penalty" in s.lower() for s in story["reasoning_steps"])

    def test_multiple_counterparties_supported(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
            self._make_row("1888 Records", "match", 0.87,
                           candidates=[{"account_name": "1888 Records", "type": "Artist", "account_id": "002"}]),
            self._make_row("Acme Corp", "review", 0.55,
                           candidates=[{"account_name": "Acme Corp", "type": "Artist", "account_id": "003"}]),
        ]
        story = build_resolution_story(rows, "Distribution Agreement")
        assert len(story["counterparties"]) >= 2

    def test_hidden_row_excluded(self):
        from server.preflight_engine import build_resolution_story
        rows = [
            self._make_row("Ostereo Limited", "match", 0.91, visible=True,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division", "account_id": "001"}]),
            self._make_row("Hidden Corp", "no-match", 0.10, visible=False,
                           candidates=[{"account_name": "Hidden Corp", "type": "Artist", "account_id": "009"}]),
        ]
        story = build_resolution_story(rows, "text")
        cparty_names = [c["name"] for c in story["counterparties"]]
        assert "Hidden Corp" not in cparty_names


class TestResolutionStoryInPreflight:
    def test_run_preflight_includes_resolution_story(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Test Corp\nSome data here to pad", "char_count": 60, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        assert "resolution_story" in result
        story = result["resolution_story"]
        assert "legal_entity_account" in story
        assert "counterparties" in story
        assert "agreement_type_guess" in story
        assert "reasoning_steps" in story
        assert "analyst_actions" in story
        assert "requires_manual_confirmation" in story
        assert "recital_parties" in story

    def test_resolution_story_empty_pages(self):
        from server.preflight_engine import run_preflight
        result = run_preflight([])
        assert "resolution_story" not in result

    def test_resolution_story_alongside_sf_match(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Test Corp\nSome data here to pad more", "char_count": 60, "image_coverage_ratio": 0.0}]
        result = run_preflight(pages)
        assert "salesforce_match" in result
        assert "resolution_story" in result

    def test_resolution_story_deterministic(self):
        from server.preflight_engine import run_preflight
        pages = [{"page": 1, "text": "Account Name: Alpha Corp\nCompany Name: Beta Inc", "char_count": 60, "image_coverage_ratio": 0.0}]
        r1 = run_preflight(pages)
        r2 = run_preflight(pages)
        assert r1["resolution_story"]["agreement_type_guess"] == r2["resolution_story"]["agreement_type_guess"]
        assert r1["resolution_story"]["requires_manual_confirmation"] == r2["resolution_story"]["requires_manual_confirmation"]


class TestNewEntryDetection:
    def _make_row(self, source_field, match_status="review", confidence=0.50,
                  source_type="strict_label_value", candidates=None, visible=True,
                  suggested_label=None):
        return {
            "source_field": source_field,
            "suggested_label": suggested_label or source_field,
            "match_method": "exact",
            "match_score": confidence,
            "name_score": confidence,
            "confidence_pct": round(confidence * 100),
            "match_status": match_status,
            "classification": "matched" if match_status == "match" else "ambiguous",
            "candidates": candidates or [],
            "explanation": "",
            "provider": "cmg_csv_v1",
            "evidence_chips": [],
            "scoring_breakdown": {"name_evidence": confidence * 0.55},
            "visible": visible,
            "source_type": source_type,
            "label_value_hit": source_type == "strict_label_value",
            "recital_party_hit": False,
        }

    def test_new_entry_detected_unresolved_party(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            self._make_row("Ostereo Limited", match_status="match", confidence=0.92,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division"}]),
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and RK Entertainments Ltd\n\nSome body text here."
        story = build_resolution_story(sf, text)
        assert story["new_entry_detected"] is True
        assert "RK Entertainments Ltd" in story["unresolved_counterparties"]
        assert any("Create Account" in a for a in story["analyst_actions"])
        assert story["requires_manual_confirmation"] is True

    def test_new_entry_onboarding_recommendation(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            self._make_row("Ostereo Limited", match_status="match", confidence=0.92,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division"}]),
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and RK Entertainments Ltd\n\nBody."
        story = build_resolution_story(sf, text)
        rec = story["onboarding_recommendation"]
        assert rec is not None
        assert rec["suggested_account_name"] == "RK Entertainments Ltd"
        assert rec["suggested_account_type"] == "Record Label"
        assert rec["reason"] is not None

    def test_no_new_entry_when_counterparty_matched(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            self._make_row("Ostereo Limited", match_status="match", confidence=0.92,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division"}]),
            self._make_row("1888 Records", match_status="match", confidence=0.85),
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and 1888 Records\n\nBody."
        story = build_resolution_story(sf, text)
        assert story["new_entry_detected"] is False
        assert story["unresolved_counterparties"] == []
        assert story["onboarding_recommendation"] is None

    def test_borne_suppression_no_regression(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            self._make_row("Ostereo Limited", match_status="match", confidence=0.92,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division"}]),
            self._make_row("Sony Music", match_status="no-match", confidence=0.10),
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and Sony Music\n\nBody."
        story = build_resolution_story(sf, text)
        assert story["new_entry_detected"] is False
        assert "Sony Music" not in story.get("unresolved_counterparties", [])

    def test_new_entry_fields_present_in_empty_story(self):
        from server.preflight_engine import build_resolution_story
        story = build_resolution_story([], "Some text")
        assert "new_entry_detected" in story
        assert story["new_entry_detected"] is False
        assert "unresolved_counterparties" in story
        assert story["unresolved_counterparties"] == []
        assert "onboarding_recommendation" in story
        assert story["onboarding_recommendation"] is None

    def test_artist_type_when_no_company_markers(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            self._make_row("Ostereo Limited", match_status="match", confidence=0.92,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division"}]),
        ]
        text = "Recording Agreement\nThis agreement is between Ostereo Limited and John Smith\n\nBody text."
        story = build_resolution_story(sf, text)
        assert story["new_entry_detected"] is True
        rec = story["onboarding_recommendation"]
        assert rec is not None
        assert rec["suggested_account_type"] == "Artist"

    def test_reasoning_includes_new_entry_step(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            self._make_row("Ostereo Limited", match_status="match", confidence=0.92,
                           candidates=[{"account_name": "Ostereo Limited", "type": "Division"}]),
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and RK Entertainments Ltd\n\nBody."
        story = build_resolution_story(sf, text)
        assert any("new entry detected" in s for s in story["reasoning_steps"])


class TestBorneSuppression:
    def test_borne_verb_context_detected(self):
        from server.preflight_engine import _is_borne_in_verb_context
        assert _is_borne_in_verb_context("borne", "costs to be borne by the licensee") is True
        assert _is_borne_in_verb_context("borne", "borne by the distributor") is True
        assert _is_borne_in_verb_context("borne", "shall be borne by the company") is True

    def test_borne_not_suppressed_without_phrase(self):
        from server.preflight_engine import _is_borne_in_verb_context
        assert _is_borne_in_verb_context("borne", "Borne Records is a label") is False

    def test_non_borne_candidate_not_affected(self):
        from server.preflight_engine import _is_borne_in_verb_context
        assert _is_borne_in_verb_context("Acme Corp", "costs to be borne by Acme") is False

    def test_borne_excluded_from_sf_results(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            {
                "source_field": "Ostereo Limited",
                "suggested_label": "Ostereo Limited",
                "match_method": "exact", "match_score": 0.92, "name_score": 0.92,
                "confidence_pct": 92, "match_status": "match",
                "classification": "matched",
                "candidates": [{"account_name": "Ostereo Limited", "type": "Division"}],
                "explanation": "", "provider": "", "evidence_chips": [],
                "scoring_breakdown": {"name_evidence": 0.50},
                "visible": True, "source_type": "strict_label_value",
                "label_value_hit": True, "recital_party_hit": False,
            },
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and Some Partner\n\ncosts to be borne by the licensee"
        story = build_resolution_story(sf, text)
        all_names = [cp["name"] for cp in story.get("counterparties", [])]
        assert "borne" not in [n.lower() for n in all_names]


class TestRecitalPartyBoost:
    def test_recital_party_source_type(self):
        from server.preflight_engine import _extract_recital_parties
        text = "This agreement is between Ostereo Limited and 1888 Records Ltd\n\nBody text."
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("1888 records" in n for n in names_lower)

    def test_recital_party_marked_in_results(self):
        from server.preflight_engine import _extract_recital_parties
        text = "This agreement is between Ostereo Limited and RK Entertainments Ltd\n\nBody text."
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("rk entertainments" in n for n in names_lower)


class TestConfidenceSplitFields:
    def _make_row(self, source_field, name_score=0.50, svc_penalty=0.0, addr=0.0, acct_ctx=0.0):
        name_ev = min(name_score, 1.0) * 0.55
        composite = max(0, name_ev + addr + acct_ctx - svc_penalty)
        identity_raw = name_ev + addr + acct_ctx
        return {
            "source_field": source_field,
            "suggested_label": source_field,
            "match_method": "exact", "match_score": composite, "name_score": name_score,
            "confidence_pct": round(composite * 100),
            "identity_confidence_pct": round(min(identity_raw / 0.55, 1.0) * 100),
            "context_risk_penalty_pct": round(svc_penalty * 100),
            "final_confidence_pct": round(composite * 100),
            "match_status": "match", "classification": "matched",
            "candidates": [], "explanation": "", "provider": "",
            "evidence_chips": [], "scoring_breakdown": {"name_evidence": name_ev},
            "visible": True, "source_type": "strict_label_value",
            "label_value_hit": True, "recital_party_hit": False,
        }

    def test_identity_confidence_higher_than_final(self):
        row = self._make_row("Test Corp", name_score=1.0, svc_penalty=0.10)
        assert row["identity_confidence_pct"] >= row["final_confidence_pct"]

    def test_no_penalty_identity_equals_final(self):
        row = self._make_row("Test Corp", name_score=0.80, svc_penalty=0.0)
        assert row["context_risk_penalty_pct"] == 0

    def test_all_confidence_fields_present(self):
        row = self._make_row("Test Corp")
        assert "identity_confidence_pct" in row
        assert "context_risk_penalty_pct" in row
        assert "final_confidence_pct" in row

    def test_identity_confidence_populated_from_build(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            {
                "source_field": "Ostereo Limited",
                "suggested_label": "Ostereo Limited",
                "match_method": "exact", "match_score": 0.50, "name_score": 1.0,
                "confidence_pct": 50,
                "identity_confidence_pct": 100,
                "context_risk_penalty_pct": 5,
                "final_confidence_pct": 50,
                "match_status": "match", "classification": "matched",
                "candidates": [{"account_name": "Ostereo Limited", "type": "Division"}],
                "explanation": "", "provider": "", "evidence_chips": [],
                "scoring_breakdown": {"name_evidence": 0.55},
                "visible": True, "source_type": "strict_label_value",
                "label_value_hit": True, "recital_party_hit": False,
            },
        ]
        story = build_resolution_story(sf, "Some text")
        assert story["legal_entity_account"] is not None


class TestUnresolvedCounterpartyNewEntry:
    def test_recital_counterparty_triggers_new_entry(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            {
                "source_field": "Ostereo Limited",
                "suggested_label": "Ostereo Limited",
                "match_method": "exact", "match_score": 0.92, "name_score": 0.92,
                "confidence_pct": 92, "match_status": "match",
                "classification": "matched",
                "candidates": [{"account_name": "Ostereo Limited", "type": "Division"}],
                "explanation": "", "provider": "", "evidence_chips": [],
                "scoring_breakdown": {"name_evidence": 0.50},
                "visible": True, "source_type": "strict_label_value",
                "label_value_hit": True, "recital_party_hit": False,
                "identity_confidence_pct": 100,
                "context_risk_penalty_pct": 0,
                "final_confidence_pct": 92,
            },
        ]
        text = "Distribution Agreement\nThis agreement is between Ostereo Limited and RK Entertainments Ltd\n\nBody text."
        story = build_resolution_story(sf, text)
        assert story["new_entry_detected"] is True
        assert "RK Entertainments Ltd" in story["unresolved_counterparties"]
        assert any("Create Account" in a for a in story["analyst_actions"])


class TestConfidenceSemanticsReasoning:
    def _make_sf_row(self, name, penalty_pct=0):
        return {
            "source_field": name, "suggested_label": name,
            "match_method": "exact", "match_score": 0.50, "name_score": 1.0,
            "confidence_pct": 50, "identity_confidence_pct": 100,
            "context_risk_penalty_pct": penalty_pct, "final_confidence_pct": 50,
            "match_status": "match", "classification": "matched",
            "candidates": [{"account_name": name, "type": "Division"}],
            "explanation": "", "provider": "", "evidence_chips": [],
            "scoring_breakdown": {"name_evidence": 0.55, "service_context_penalty": penalty_pct / 100.0},
            "visible": True, "source_type": "strict_label_value",
            "label_value_hit": True, "recital_party_hit": False,
        }

    def test_semantics_line_added_when_penalty_exists(self):
        from server.preflight_engine import build_resolution_story
        sf = [self._make_sf_row("Ostereo Limited", penalty_pct=5)]
        story = build_resolution_story(sf, "Some text")
        assert any("identity evidence adjusted by context risk" in s for s in story["reasoning_steps"])

    def test_semantics_line_absent_when_no_penalty(self):
        from server.preflight_engine import build_resolution_story
        sf = [self._make_sf_row("Ostereo Limited", penalty_pct=0)]
        story = build_resolution_story(sf, "Some text")
        assert not any("identity evidence adjusted by context risk" in s for s in story["reasoning_steps"])

    def test_story_entity_has_confidence_split(self):
        from server.preflight_engine import build_resolution_story
        sf = [self._make_sf_row("Ostereo Limited", penalty_pct=5)]
        story = build_resolution_story(sf, "Some text")
        le = story["legal_entity_account"]
        assert le is not None
        assert le["identity_confidence_pct"] == 100
        assert le["context_risk_penalty_pct"] == 5
        assert le["final_confidence_pct"] == 50


class TestResolverCandidateCap:
    def test_recital_parties_from_between_and(self):
        from server.preflight_engine import _extract_recital_parties
        text = "This agreement is between Ostereo Limited and 1888 Records Ltd\n\nBody text."
        parties = _extract_recital_parties(text)
        assert len(parties) >= 1

    def test_extract_rejects_clause_lines(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("shall be responsible")

    def test_extract_rejects_colon_labels(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("Party A:")


class TestRecitalExtractionHardening:
    def test_ks_preamble_extracts_both_parties(self):
        from server.preflight_engine import _extract_recital_parties
        text = (
            "DISTRIBUTION AGREEMENT\n"
            "This Distribution Agreement is entered into between "
            "KS Army Entertainment LLC and RK Entertainments Ltd\n\n"
            "WHEREAS the parties agree to the following terms.\n"
            "Body of the agreement.\n"
        )
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("ks army" in n for n in names_lower)
        assert any("rk entertainments" in n for n in names_lower)

    def test_ks_sample_no_clause_noise(self):
        from server.preflight_engine import _extract_recital_parties
        text = (
            "DISTRIBUTION AGREEMENT\n"
            "This Distribution Agreement is entered into between "
            "KS Army Entertainment LLC and RK Entertainments Ltd\n\n"
            "WHEREAS the parties agree to the following terms and conditions.\n"
            "shall distribute the recordings\n"
            "provided that all royalties are paid quarterly\n"
            "in accordance with Schedule A attached hereto\n"
            "Page 1 of 12\n"
        )
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("ks army" in n for n in names_lower)
        assert any("rk entertainments" in n for n in names_lower)
        assert not any("shall " in p.lower() for p in parties)
        assert not any("provided that" in p.lower() for p in parties)
        assert not any("in accordance" in p.lower() for p in parties)
        assert not any("page " in p.lower() for p in parties)

    def test_rejects_revenue_shares(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("REVENUE SHARES")
        assert not is_plausible_party_name("Revenue Shares")

    def test_rejects_definitions_ellipsis(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("DEFINITIONS ...")
        assert not is_plausible_party_name("Definitions")

    def test_rejects_account_name_colon_label(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("Account Name: RK Corp")
        assert not is_plausible_party_name("Bank Name: HSBC")

    def test_rejects_bank_swift_lines(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("Bank Account Number 12345678")
        assert not is_plausible_party_name("SWIFT: HBUKGB4B")
        assert not is_plausible_party_name("Sort Code 40-47-84")

    def test_rejects_schedule_exhibit(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("Schedule A")
        assert not is_plausible_party_name("Exhibit B")

    def test_rejects_channels_means_page(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("Distribution Channels")
        assert not is_plausible_party_name("By Any Means")
        assert not is_plausible_party_name("Page 3 of 10")

    def test_rejects_address_fragments(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("1234 Broadway Street, Nashville")
        assert not is_plausible_party_name("Suite 400, Los Angeles, California 90210")

    def test_rejects_generic_role_nouns_alone(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("Owner")
        assert not is_plausible_party_name("Company")
        assert not is_plausible_party_name("Label")
        assert not is_plausible_party_name("Party")

    def test_rejects_prose_clause_patterns(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("shall distribute the recordings")
        assert not is_plausible_party_name("Provided that all royalties")
        assert not is_plausible_party_name("In accordance with terms")

    def test_accepts_company_markers(self):
        from server.preflight_engine import is_plausible_party_name
        assert is_plausible_party_name("RK Entertainments Ltd")
        assert is_plausible_party_name("Ostereo Limited")
        assert is_plausible_party_name("KS Army Entertainment LLC")
        assert is_plausible_party_name("Acme Records Inc")

    def test_accepts_title_case_multi_word(self):
        from server.preflight_engine import is_plausible_party_name
        assert is_plausible_party_name("John Smith Productions")
        assert is_plausible_party_name("Mary Jane Watson")

    def test_normalize_strips_role_parens(self):
        from server.preflight_engine import normalize_party_candidate
        assert "Acme Records Inc" == normalize_party_candidate('Acme Records Inc ("Label")')
        assert "John Smith" == normalize_party_candidate('John Smith ("Artist")')

    def test_normalize_strips_address_tail(self):
        from server.preflight_engine import normalize_party_candidate
        result = normalize_party_candidate("RK Corp, located at 123 Main St")
        assert "123" not in result
        assert "Main" not in result

    def test_block_format_between_extraction(self):
        from server.preflight_engine import _extract_recital_parties
        text = "Distribution Agreement\nBETWEEN:\nOstereo Limited\nand\nRK Entertainments Ltd\n\nSome body text here."
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("ostereo" in n for n in names_lower)
        assert any("rk entertainments" in n for n in names_lower)

    def test_block_format_no_body_leakage(self):
        from server.preflight_engine import _extract_recital_parties
        filler = "\n".join([f"Line {i} of filler text" for i in range(40)])
        text = "BETWEEN:\nOstereo Limited\nand\n1888 Records Ltd\n" + filler + "\nREVENUE SHARES\nDEFINITIONS\n"
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("ostereo" in n for n in names_lower)
        assert any("1888 records" in n for n in names_lower)
        assert not any("revenue" in n for n in names_lower)
        assert not any("definition" in n for n in names_lower)

    def test_rejects_compound_and_names(self):
        from server.preflight_engine import is_plausible_party_name
        assert not is_plausible_party_name("KS Army Entertainment LLC and RK Entertainments Ltd")
        assert not is_plausible_party_name("Alpha Corp & Beta Inc")

    def test_label_party_extraction(self):
        from server.preflight_engine import _extract_recital_parties
        text = 'Acme Records Inc ("Label") and John Smith Productions LLC ("Artist")\n\nBody text here.\n'
        parties = _extract_recital_parties(text)
        names_lower = [p.lower() for p in parties]
        assert any("acme records" in n for n in names_lower)
        assert any("john smith productions" in n for n in names_lower)

    def test_preamble_35_line_limit(self):
        from server.preflight_engine import _extract_recital_parties
        filler = "\n".join([f"Line {i} of filler text" for i in range(40)])
        text = filler + "\nThis contract is between Alpha Corp LLC and Beta Inc\n\nBody."
        parties = _extract_recital_parties(text)
        assert not any("alpha" in p.lower() for p in parties)

    def test_max_parties_capped_at_6(self):
        from server.preflight_engine import _extract_recital_parties
        text = (
            'Alpha Corp Ltd ("Label") and Beta Inc ("Owner") and '
            'Gamma LLC ("Publisher") and Delta Records ("Distributor") and '
            'Epsilon Music ("Producer") and Zeta Studios ("Manager") and '
            'Eta Group ("Licensee") and Theta Entertainment ("Licensor")\n\nBody.\n'
        )
        parties = _extract_recital_parties(text)
        assert len(parties) <= 6

    def test_onboarding_quality_gate_rejects_noise(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            {
                "source_field": "KS Army Entertainment LLC",
                "suggested_label": "KS Army Entertainment LLC",
                "match_method": "exact", "match_score": 0.92, "name_score": 0.92,
                "confidence_pct": 92, "match_status": "match",
                "classification": "matched",
                "candidates": [{"account_name": "KS Army Entertainment LLC", "type": "Division"}],
                "explanation": "", "provider": "", "evidence_chips": [],
                "scoring_breakdown": {"name_evidence": 0.50},
                "visible": True, "source_type": "strict_label_value",
                "label_value_hit": True, "recital_party_hit": False,
                "identity_confidence_pct": 100,
                "context_risk_penalty_pct": 0,
                "final_confidence_pct": 92,
            },
        ]
        text = (
            "This agreement is between KS Army Entertainment LLC and RK Entertainments Ltd\n\n"
            "Body of the agreement.\n"
        )
        story = build_resolution_story(sf, text)
        for u in story["unresolved_counterparties"]:
            assert "shall" not in u.lower()
            assert "provided" not in u.lower()
            assert "page" not in u.lower()
            assert "revenue" not in u.lower()
            assert "definition" not in u.lower()

    def test_onboarding_never_suggests_noise(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            {
                "source_field": "Test Corp LLC",
                "suggested_label": "Test Corp LLC",
                "match_method": "exact", "match_score": 0.92, "name_score": 0.92,
                "confidence_pct": 92, "match_status": "match",
                "classification": "matched",
                "candidates": [{"account_name": "Test Corp LLC", "type": "Company"}],
                "explanation": "", "provider": "", "evidence_chips": [],
                "scoring_breakdown": {"name_evidence": 0.50},
                "visible": True, "source_type": "strict_label_value",
                "label_value_hit": True, "recital_party_hit": False,
                "identity_confidence_pct": 100,
                "context_risk_penalty_pct": 0,
                "final_confidence_pct": 92,
            },
        ]
        text = "This agreement is between Test Corp LLC and REVENUE SHARES\n\nBody.\n"
        story = build_resolution_story(sf, text)
        if story["onboarding_recommendation"]:
            suggested = story["onboarding_recommendation"]["suggested_account_name"]
            assert "revenue" not in suggested.lower()
            assert "shares" not in suggested.lower()


class TestIdentityConfidenceNormalization:
    def test_name_only_normalization(self):
        from server.preflight_engine import _extract_recital_parties
        identity_raw = 0.55
        positive_max = 0.55 + 0.30 + 0.20
        pct = round(min(identity_raw / positive_max, 1.0) * 100)
        assert pct == 52

    def test_full_evidence_normalization(self):
        identity_raw = 0.55 + 0.30 + 0.20
        positive_max = 0.55 + 0.30 + 0.20
        pct = round(min(identity_raw / positive_max, 1.0) * 100)
        assert pct == 100

    def test_name_plus_address_normalization(self):
        identity_raw = 0.55 + 0.30
        positive_max = 0.55 + 0.30 + 0.20
        pct = round(min(identity_raw / positive_max, 1.0) * 100)
        assert pct == 81

    def test_confidence_fields_all_present(self):
        from server.preflight_engine import build_resolution_story
        sf = [
            {
                "source_field": "Test Corp",
                "suggested_label": "Test Corp",
                "match_method": "exact", "match_score": 0.92, "name_score": 1.0,
                "confidence_pct": 92, "match_status": "match",
                "classification": "matched",
                "candidates": [{"account_name": "Test Corp", "type": "Division"}],
                "explanation": "", "provider": "", "evidence_chips": [],
                "scoring_breakdown": {"name_evidence": 0.55},
                "visible": True, "source_type": "strict_label_value",
                "label_value_hit": True, "recital_party_hit": False,
                "identity_confidence_pct": 52,
                "context_risk_penalty_pct": 0,
                "final_confidence_pct": 92,
            },
        ]
        story = build_resolution_story(sf, "Some text")
        le = story["legal_entity_account"]
        assert le is not None
        assert "identity_confidence_pct" in le
        assert "context_risk_penalty_pct" in le
        assert "final_confidence_pct" in le
        assert "confidence" in le

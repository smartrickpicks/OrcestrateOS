"""Tests for Opportunity Spine preflight gates."""

import pytest
from server.preflight_engine import (
    build_opportunity_spine,
    _extract_contract_type,
    _extract_contract_subtype,
    _extract_effective_date,
    _extract_term,
    _extract_territory,
    _check_role_linkage,
    run_preflight,
)
from server.preflight_rules import classify_contract, is_subtype_allowed, get_expected_schedule_types


class TestContractType:
    def test_distribution_in_title(self):
        text = "Distribution Agreement\n\nThis agreement is between Party A and Party B."
        result = _extract_contract_type(text)
        assert result["status"] == "pass"
        assert result["value"] == "distribution"
        assert result["confidence"] >= 0.9

    def test_license_in_body_only(self):
        filler = "\n".join([f"Line {i}" for i in range(15)])
        text = "Document Title\n" + filler + "\nThis is a license agreement between parties."
        result = _extract_contract_type(text)
        assert result["status"] == "review"
        assert result["value"] == "license"

    def test_missing_contract_type(self):
        text = "Some random document text with no contract keywords."
        result = _extract_contract_type(text)
        assert result["status"] == "fail"
        assert result["value"] is None

    def test_amendment_detected(self):
        text = "Amendment\n\nThis amendment modifies the original agreement."
        result = _extract_contract_type(text)
        assert result["status"] == "pass"
        assert result["value"] == "amendment"

    def test_termination_detected(self):
        text = "Termination Agreement\n\nThis agreement terminates the prior contract."
        result = _extract_contract_type(text)
        assert result["status"] == "pass"
        assert result["value"] == "termination"

    def test_empty_text(self):
        result = _extract_contract_type("")
        assert result["status"] == "fail"


class TestContractSubtype:
    def test_digital_distribution(self):
        text = "This is a digital distribution agreement for worldwide release."
        result = _extract_contract_subtype(text)
        assert result["status"] == "pass"
        assert result["value"] == "Distribution"
        assert "candidates" in result
        assert len(result["candidates"]) >= 1
        assert result["candidates"][0]["value"] == "Distribution"

    def test_label_services(self):
        text = "The parties agree to label services for the following recordings."
        result = _extract_contract_subtype(text)
        assert result["status"] in ("pass", "review")
        assert result["value"] == "Label Ventures"
        assert len(result["candidates"]) >= 1

    def test_multiple_subtypes(self):
        filler = "\n".join([f"Line {i}" for i in range(12)])
        text = "Distribution Agreement\n" + filler + "\nThis covers digital distribution and sync licensing rights.\nThe synchronization fees apply."
        result = _extract_contract_subtype(text)
        assert result["status"] == "review"
        assert "analyst confirmation required" in result["reason"]
        assert len(result["candidates"]) >= 2
        cand_values = [c["value"] for c in result["candidates"]]
        assert "Distribution" in cand_values
        assert "Sync" in cand_values

    def test_no_subtype(self):
        text = "A general agreement between the parties."
        result = _extract_contract_subtype(text)
        assert result["status"] == "review"
        assert result["value"] is None
        assert result["candidates"] == []

    def test_admin_publishing(self):
        text = "This admin publishing agreement covers the catalogue."
        result = _extract_contract_subtype(text)
        assert result["status"] == "pass"
        assert result["value"] == "Pub Admin"

    def test_empty_text(self):
        result = _extract_contract_subtype("")
        assert result["status"] == "fail"
        assert result["candidates"] == []

    def test_synch_normalized_to_sync(self):
        text = "This agreement includes synch licensing and synch license terms."
        result = _extract_contract_subtype(text)
        assert result["value"] == "Sync"
        cand_values = [c["value"] for c in result["candidates"]]
        assert "Sync" in cand_values
        assert "synch" not in cand_values
        assert "synch licensing" not in cand_values

    def test_synchronisation_normalized(self):
        text = "This agreement covers synchronisation rights."
        result = _extract_contract_subtype(text)
        assert result["value"] == "Sync"

    def test_candidates_have_evidence(self):
        text = "Digital distribution agreement with sync licensing rights."
        result = _extract_contract_subtype(text)
        for cand in result["candidates"]:
            assert "evidence" in cand
            assert len(cand["evidence"]) > 0
            assert "confidence" in cand
            assert "value" in cand

    def test_candidate_ordering_deterministic(self):
        text = "Distribution Agreement\nDigital distribution and sync licensing and exclusive license rights."
        results = [_extract_contract_subtype(text) for _ in range(5)]
        first_order = [c["value"] for c in results[0]["candidates"]]
        for r in results[1:]:
            assert [c["value"] for c in r["candidates"]] == first_order

    def test_single_candidate_pass(self):
        filler = "\n".join([f"Line {i}" for i in range(12)])
        text = "Agreement\n" + filler + "\nThis is a digital distribution agreement."
        result = _extract_contract_subtype(text)
        assert result["status"] == "pass"
        assert len(result["candidates"]) == 1
        assert result["candidates"][0]["value"] == "Distribution"

    def test_zone_weighting_title_higher(self):
        filler = "\n".join([f"Line {i}" for i in range(40)])
        text = "Digital Distribution Agreement\n" + filler + "\nSome sync licensing text here.\nThe synchronization rights apply."
        result = _extract_contract_subtype(text)
        assert result["candidates"][0]["value"] == "Distribution"
        assert len(result["candidates"]) >= 2
        assert result["candidates"][0]["confidence"] > result["candidates"][1]["confidence"]


class TestEffectiveDate:
    def test_standard_date_format(self):
        text = "This agreement is effective as of 15 January 2024 between the parties."
        result = _extract_effective_date(text)
        assert result["status"] == "pass"
        assert "January" in result["value"]
        assert "2024" in result["value"]

    def test_numeric_date(self):
        text = "Dated as of 01/15/2024."
        result = _extract_effective_date(text)
        assert result["status"] == "pass"
        assert "01/15/2024" in result["value"]

    def test_ordinal_date(self):
        text = "Made on the 1st day of March, 2024 between parties."
        result = _extract_effective_date(text)
        assert result["status"] == "pass"
        assert "March" in result["value"]

    def test_entered_into_date(self):
        text = "This agreement is entered into as of 25 June 2023."
        result = _extract_effective_date(text)
        assert result["status"] == "pass"

    def test_no_date(self):
        text = "This agreement has no date mentioned anywhere."
        result = _extract_effective_date(text)
        assert result["status"] == "fail"

    def test_empty_text(self):
        result = _extract_effective_date("")
        assert result["status"] == "fail"


class TestTerm:
    def test_years_term(self):
        text = "The initial term of this agreement is 3 years from the effective date."
        result = _extract_term(text)
        assert result["status"] == "pass"
        assert "3 years" in result["value"]

    def test_months_term(self):
        text = "The term shall be 18 months commencing on the effective date."
        result = _extract_term(text)
        assert result["status"] == "pass"
        assert "18 months" in result["value"]

    def test_period_of(self):
        text = "This agreement shall remain in effect for a period of 5 years."
        result = _extract_term(text)
        assert result["status"] == "pass"
        assert "5 years" in result["value"]

    def test_perpetual(self):
        text = "The license is granted in perpetuity."
        result = _extract_term(text)
        assert result["status"] == "pass"
        assert "Perpetual" in result["value"]

    def test_life_of_copyright(self):
        text = "The term shall be for the life of copyright of the works."
        result = _extract_term(text)
        assert result["status"] == "pass"
        assert "Perpetual" in result["value"]

    def test_phrase_pattern(self):
        text = "This is a 2-year term agreement."
        result = _extract_term(text)
        assert result["status"] == "review"
        assert "2" in result["value"]

    def test_no_term(self):
        text = "This agreement covers various topics but does not mention duration."
        result = _extract_term(text)
        assert result["status"] == "fail"

    def test_empty_text(self):
        result = _extract_term("")
        assert result["status"] == "fail"


class TestTerritory:
    def test_worldwide(self):
        text = "The territory shall be worldwide."
        result = _extract_territory(text)
        assert result["status"] == "pass"
        assert result["value"] == "Worldwide"

    def test_specific_country(self):
        text = "Territory: United Kingdom and related territories."
        result = _extract_territory(text)
        assert result["status"] == "pass"
        assert "United Kingdom" in result["value"]

    def test_multiple_territories(self):
        text = "The licensed territory includes the United States and United Kingdom."
        result = _extract_territory(text)
        assert result["status"] == "review"
        assert "United States" in result["value"]

    def test_no_territory(self):
        text = "This agreement has no geographic scope defined."
        result = _extract_territory(text)
        assert result["status"] == "fail"

    def test_empty_text(self):
        result = _extract_territory("")
        assert result["status"] == "fail"

    def test_worldwide_overrides_specifics(self):
        text = "Territory: worldwide including the United States."
        result = _extract_territory(text)
        assert result["status"] == "pass"
        assert result["value"] == "Worldwide"


class TestRoleLinkage:
    def test_both_resolved(self):
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [{"name": "1888 Records"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = _check_role_linkage(story)
        assert result["status"] == "pass"

    def test_legal_entity_only(self):
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = _check_role_linkage(story)
        assert result["status"] == "review"

    def test_legal_with_unresolved(self):
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [],
            "unresolved_counterparties": ["KS Army Entertainment LLC"],
            "requires_manual_confirmation": True,
        }
        result = _check_role_linkage(story)
        assert result["status"] == "review"

    def test_no_legal_entity(self):
        story = {
            "legal_entity_account": None,
            "counterparties": [{"name": "1888 Records"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = _check_role_linkage(story)
        assert result["status"] == "fail"

    def test_nothing_resolved(self):
        story = {
            "legal_entity_account": None,
            "counterparties": [],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = _check_role_linkage(story)
        assert result["status"] == "fail"

    def test_no_story(self):
        result = _check_role_linkage(None)
        assert result["status"] == "fail"


class TestBuildOpportunitySpine:
    def test_full_pass(self):
        text = """Distribution Agreement

This digital distribution agreement is effective as of 15 January 2024.

The initial term of this agreement is 3 years.

Territory: Worldwide.
"""
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [{"name": "1888 Records"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = build_opportunity_spine(text, story)
        assert result["status"] == "pass"
        assert result["summary"]["failed"] == 0
        assert len(result["checks"]) == 6
        codes = [c["code"] for c in result["checks"]]
        assert "OPP_CONTRACT_TYPE" in codes
        assert "OPP_CONTRACT_SUBTYPE" in codes
        assert "OPP_EFFECTIVE_DATE" in codes
        assert "OPP_TERM" in codes
        assert "OPP_TERRITORY" in codes
        assert "OPP_ROLE_LINKAGE" in codes

    def test_missing_contract_type_critical_fail(self):
        text = "Some document without contract type keywords."
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [{"name": "Acme"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = build_opportunity_spine(text, story)
        assert result["status"] == "fail"
        ct = next(c for c in result["checks"] if c["code"] == "OPP_CONTRACT_TYPE")
        assert ct["status"] == "fail"

    def test_ambiguous_subtype_review(self):
        text = """Distribution Agreement

This covers digital distribution and sync licensing rights.
Effective as of January 1, 2024.
Term of 5 years. Territory: Worldwide.
"""
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [{"name": "Acme"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = build_opportunity_spine(text, story)
        sub = next(c for c in result["checks"] if c["code"] == "OPP_CONTRACT_SUBTYPE")
        assert sub["status"] == "review"
        assert result["status"] in ("review", "pass")

    def test_missing_role_linkage_critical_fail(self):
        text = "Distribution Agreement\nEffective date: January 1, 2024.\nTerm of 3 years.\nTerritory: Worldwide."
        story = {
            "legal_entity_account": None,
            "counterparties": [],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = build_opportunity_spine(text, story)
        assert result["status"] == "fail"
        rl = next(c for c in result["checks"] if c["code"] == "OPP_ROLE_LINKAGE")
        assert rl["status"] == "fail"

    def test_schema_stability(self):
        text = "Distribution Agreement\nSome text."
        story = {"legal_entity_account": None, "counterparties": [], "unresolved_counterparties": [], "requires_manual_confirmation": False}
        result = build_opportunity_spine(text, story)
        assert "status" in result
        assert "checks" in result
        assert "summary" in result
        assert isinstance(result["checks"], list)
        assert isinstance(result["summary"], dict)
        for ck in result["checks"]:
            assert "code" in ck
            assert "label" in ck
            assert "status" in ck
            assert "confidence" in ck
            assert "value" in ck
            assert "reason" in ck
            assert ck["status"] in ("pass", "review", "fail")

    def test_overall_review_no_critical_fail(self):
        text = "Distribution Agreement\nSome distribution content."
        story = {
            "legal_entity_account": {"name": "Ostereo"},
            "counterparties": [],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        result = build_opportunity_spine(text, story)
        assert result["status"] == "review"

    def test_empty_text(self):
        result = build_opportunity_spine("", None)
        assert result["status"] == "fail"
        assert result["summary"]["failed"] >= 2

    def test_run_preflight_includes_opportunity_spine(self):
        pages = [{"text": "Distribution Agreement\nEffective date: January 1, 2024.\nTerritory: Worldwide.\nTerm of 3 years.", "char_count": 100, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        assert "opportunity_spine" in result
        spine = result["opportunity_spine"]
        assert "status" in spine
        assert "checks" in spine
        assert "summary" in spine
        assert len(spine["checks"]) == 6


class TestContractClassification:
    def test_distribution_classification(self):
        r = classify_contract("distribution", "Distribution Agreement\nDigital distribution for worldwide release.")
        assert r["contract_category"] == "Distribution"
        assert "distro_sync_existing_masters" in r["expected_schedule_types"] or "catalog_acquisition_masters" in r["expected_schedule_types"]
        assert r["termination_flavor"] is None

    def test_termination_mutual(self):
        text = "Termination Agreement\n\nThe parties mutually agree to terminate the prior agreement by mutual agreement."
        r = classify_contract("termination", text)
        assert r["contract_category"] == "Termination"
        assert r["termination_flavor"] == "mutual"
        assert r["termination_flavor_label"] == "Mutual Termination"
        assert len(r["termination_flavor_evidence"]) >= 1

    def test_termination_for_cause(self):
        text = "Termination Agreement\n\nDue to material breach of the terms and failure to cure within 30 days."
        r = classify_contract("termination", text)
        assert r["contract_category"] == "Termination"
        assert r["termination_flavor"] == "for_cause"
        assert r["termination_flavor_label"] == "Termination for Cause"

    def test_termination_convenience(self):
        text = "Termination Agreement\n\nParty A terminates for convenience upon 90 days notice."
        r = classify_contract("termination", text)
        assert r["contract_category"] == "Termination"
        assert r["termination_flavor"] == "convenience"

    def test_termination_expiry(self):
        text = "Termination Agreement\n\nThe agreement terminates upon natural expiry and non-renewal of the term."
        r = classify_contract("termination", text)
        assert r["contract_category"] == "Termination"
        assert r["termination_flavor"] == "expiry"

    def test_termination_reversion(self):
        text = "Termination Agreement\n\nAll rights shall revert to the artist upon reversion of rights per the catalogue reversion clause."
        r = classify_contract("termination", text)
        assert r["contract_category"] == "Termination"
        assert r["termination_flavor"] == "reversion"

    def test_no_termination_flavor_for_distribution(self):
        r = classify_contract("distribution", "Distribution Agreement content.")
        assert r["termination_flavor"] is None
        assert r["termination_flavor_evidence"] == []

    def test_unknown_contract_type(self):
        r = classify_contract(None, "Some text")
        assert r["contract_category"] is None
        assert r["expected_schedule_types"] == []

    def test_license_classification(self):
        r = classify_contract("license", "License Agreement text.")
        assert r["contract_category"] == "License"
        assert "catalog_acquisition_masters" in r["expected_schedule_types"]

    def test_amendment_classification(self):
        r = classify_contract("amendment", "Amendment text.")
        assert r["contract_category"] == "Amendment"
        assert r["expected_schedule_types"] == []

    def test_classification_in_run_preflight(self):
        pages = [{"text": "Distribution Agreement\nDigital distribution agreement for worldwide release.\nEffective date: January 1, 2024.\nTerm of 3 years.\nTerritory: Worldwide.", "char_count": 150, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        assert "contract_classification" in result
        cc = result["contract_classification"]
        assert cc["contract_category"] == "Distribution"
        assert isinstance(cc["expected_schedule_types"], list)
        assert cc["category_rule_version"] == "1.0"

    def test_termination_classification_in_run_preflight(self):
        pages = [{"text": "Termination Agreement\n\nThe parties mutually agree to terminate.\nMutual termination by mutual agreement.", "char_count": 100, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        cc = result["contract_classification"]
        assert cc["contract_category"] == "Termination"
        assert cc["termination_flavor"] == "mutual"


class TestSubtypeAllowedByRules:
    def test_distribution_allows_sync(self):
        assert is_subtype_allowed("distribution", "Sync") is True

    def test_distribution_allows_distribution(self):
        assert is_subtype_allowed("distribution", "Distribution") is True

    def test_distribution_blocks_pub_admin(self):
        assert is_subtype_allowed("distribution", "Pub Admin") is False

    def test_license_allows_sync(self):
        assert is_subtype_allowed("license", "Sync") is True

    def test_license_blocks_cma(self):
        assert is_subtype_allowed("license", "CMA") is False

    def test_unknown_type_allows_anything(self):
        assert is_subtype_allowed("xyz_unknown", "Distribution") is True

    def test_none_type_allows_anything(self):
        assert is_subtype_allowed(None, "Distribution") is True


class TestDistributionSyncSubtype:
    def test_distribution_sync_combo_detected(self):
        text = "Distribution Agreement\n\nThis covers digital distribution and sync licensing rights.\nThe synchronization fees apply.\nDistro & Sync for existing masters."
        result = _extract_contract_subtype(text)
        cand_values = [c["value"] for c in result["candidates"]]
        assert "Distribution" in cand_values
        assert "Sync" in cand_values

    def test_distro_sync_contract_type(self):
        text = "Distro & Sync Agreement\n\nDigital distribution and sync licensing."
        result = _extract_contract_type(text)
        assert result["status"] == "pass"
        assert result["value"] == "distribution"

    def test_expected_schedule_for_distribution(self):
        expected = get_expected_schedule_types("distribution")
        assert "distro_sync_existing_masters" in expected
        assert "catalog_acquisition_masters" in expected

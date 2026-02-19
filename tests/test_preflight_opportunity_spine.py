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
)


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
        assert result["value"] == "digital distribution"

    def test_label_services(self):
        text = "The parties agree to label services for the following recordings."
        result = _extract_contract_subtype(text)
        assert result["status"] == "pass"
        assert result["value"] == "label services"

    def test_multiple_subtypes(self):
        text = "This covers both digital distribution and sync licensing rights."
        result = _extract_contract_subtype(text)
        assert result["status"] == "review"
        assert "Multiple" in result["reason"]

    def test_no_subtype(self):
        text = "A general agreement between the parties."
        result = _extract_contract_subtype(text)
        assert result["status"] == "review"
        assert result["value"] is None

    def test_admin_publishing(self):
        text = "This admin publishing agreement covers the catalogue."
        result = _extract_contract_subtype(text)
        assert result["status"] == "pass"
        assert result["value"] == "admin publishing"

    def test_empty_text(self):
        result = _extract_contract_subtype("")
        assert result["status"] == "fail"


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
        from server.preflight_engine import run_preflight
        pages = [{"text": "Distribution Agreement\nEffective date: January 1, 2024.\nTerritory: Worldwide.\nTerm of 3 years.", "char_count": 100, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        assert "opportunity_spine" in result
        spine = result["opportunity_spine"]
        assert "status" in spine
        assert "checks" in spine
        assert "summary" in spine
        assert len(spine["checks"]) == 6

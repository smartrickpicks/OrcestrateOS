import pytest
from server.preflight_engine import (
    build_addons_readiness,
    _extract_addon_type_signals,
    _extract_addon_rights,
    _extract_addon_pricing,
    _extract_addon_dates,
    _check_addon_completeness,
)


class TestAddonTypeSignals:
    def test_no_text(self):
        r = _extract_addon_type_signals("")
        assert r["status"] == "fail"

    def test_pass_multiple(self):
        text = "This add-on amendment covers additional services for synchronization and rider provisions."
        r = _extract_addon_type_signals(text)
        assert r["status"] == "pass"

    def test_review_single(self):
        text = "The supplemental terms apply to this agreement."
        r = _extract_addon_type_signals(text)
        assert r["status"] == "review"

    def test_fail_none(self):
        text = "Standard distribution agreement between the parties."
        r = _extract_addon_type_signals(text)
        assert r["status"] == "fail"


class TestAddonRights:
    def test_pass_multiple_rights(self):
        text = "Rights granted include synchronization, mechanical, and digital distribution for all streaming platforms."
        r = _extract_addon_rights(text)
        assert r["status"] == "pass"
        assert r["confidence"] >= 0.8

    def test_review_limited(self):
        text = "Streaming rights are granted."
        r = _extract_addon_rights(text)
        assert r["status"] == "review"

    def test_fail_no_rights(self):
        text = "The parties agree to cooperate in good faith."
        r = _extract_addon_rights(text)
        assert r["status"] == "fail"


class TestAddonPricing:
    def test_pass_pricing_with_amounts(self):
        text = "Additional fee of $5,000 per synchronization use. Supplemental royalty of 3% for each add-on."
        r = _extract_addon_pricing(text)
        assert r["status"] == "pass"

    def test_review_partial(self):
        text = "A flat fee applies to this service."
        r = _extract_addon_pricing(text)
        assert r["status"] == "review"

    def test_review_no_pricing(self):
        text = "Standard terms and conditions apply."
        r = _extract_addon_pricing(text)
        assert r["status"] == "review"


class TestAddonDates:
    def test_pass_multiple(self):
        text = "Effective date: January 1, 2025. Renewal option for a term extension of 2 years."
        r = _extract_addon_dates(text)
        assert r["status"] == "pass"

    def test_review_single(self):
        text = "The commencement date is upon execution."
        r = _extract_addon_dates(text)
        assert r["status"] == "review"

    def test_review_none(self):
        text = "This agreement covers standard operations."
        r = _extract_addon_dates(text)
        assert r["status"] == "review"


class TestAddonCompleteness:
    def test_comprehensive(self):
        text = (
            "This add-on amendment grants synchronization and mechanical rights.\n"
            "Additional fee of $10,000 per use.\n"
            "Effective date: March 1, 2025. Term extension of 3 years.\n"
        )
        r = _check_addon_completeness(text, None)
        assert r["status"] == "pass"

    def test_termination_na(self):
        spine = {"checks": [{"code": "OPP_CONTRACT_TYPE", "status": "pass", "value": "termination", "confidence": 0.9}]}
        r = _check_addon_completeness("Termination effective immediately.", spine)
        assert r["status"] == "pass"

    def test_minimal(self):
        text = "Standard agreement."
        r = _check_addon_completeness(text, None)
        assert r["status"] == "fail"


class TestBuildAddonsReadiness:
    def test_rich_addon_contract(self):
        text = (
            "ADD-ON AGREEMENT\n"
            "This rider amendment covers synchronization, mechanical, and performance rights.\n"
            "Additional fee of $25,000 per synchronization placement.\n"
            "Supplemental royalty: 5% of net receipts for each add-on use.\n"
            "Effective date: July 1, 2025. Option period: 2 years with automatic renewal.\n"
        )
        result = build_addons_readiness(text, None)
        assert result["status"] in ("pass", "review")
        assert len(result["checks"]) == 5
        assert result["summary"]["passed"] >= 3

    def test_empty_text(self):
        result = build_addons_readiness("", None)
        assert result["status"] == "fail"
        assert result["summary"]["failed"] >= 1

    def test_return_structure(self):
        result = build_addons_readiness("Some basic text.", None)
        assert "status" in result
        assert "checks" in result
        assert "summary" in result
        for ck in result["checks"]:
            assert "code" in ck
            assert "label" in ck
            assert "status" in ck
            assert "confidence" in ck
            assert ck["code"].startswith("ADDON_")

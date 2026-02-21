"""Tests for V2 Add-ons readiness preflight checks."""

from server.preflight_engine import (
    _extract_addon_options,
    _extract_addon_merch_pitching,
    _extract_addon_negotiation_rights,
    _extract_addon_windows,
    _extract_addon_economics,
    _check_addon_expectedness,
    build_v2_addons_readiness,
    build_opportunity_spine,
    run_preflight,
)


class TestAddonsSignals:
    def test_options_detected(self):
        text = "The parties grant an option period and option rights to renew."
        r = _extract_addon_options(text)
        assert r["status"] == "pass"

    def test_merch_and_pitching_detected(self):
        text = "This includes merchandising rights and placement services with sync representation."
        r = _extract_addon_merch_pitching(text)
        assert r["status"] == "pass"

    def test_negotiation_rights_detected(self):
        text = "The agreement includes first negotiation and matching rights."
        r = _extract_addon_negotiation_rights(text)
        assert r["status"] == "pass"

    def test_windows_detect_days(self):
        text = "Exercise notice must be provided within 30 business days."
        r = _extract_addon_windows(text)
        assert r["status"] == "pass"
        assert "30 days" in r["value"]

    def test_economics_detected(self):
        text = "An additional commission of 15% shall apply to this option."
        r = _extract_addon_economics(text)
        assert r["status"] == "pass"
        assert "15%" in r["value"]


class TestBuildAddonsReadiness:
    def test_build_shape(self):
        text = (
            "Distribution Agreement\n"
            "Option rights are granted for an option period.\n"
            "First negotiation and matching rights apply.\n"
            "Exercise notice within 30 days.\n"
            "Additional fee of 10% for merchandising rights.\n"
        )
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "RK Entertainments"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        opp = build_opportunity_spine(text, story)
        r = build_v2_addons_readiness(text, opp)
        assert "status" in r
        assert "checks" in r
        assert "summary" in r
        assert len(r["checks"]) == 6
        codes = [c["code"] for c in r["checks"]]
        assert "ADDON_OPTIONS" in codes
        assert "ADDON_MERCH_PITCH" in codes
        assert "ADDON_NEGOTIATION" in codes
        assert "ADDON_WINDOWS" in codes
        assert "ADDON_ECONOMICS" in codes
        assert "ADDON_EXPECTEDNESS" in codes

    def test_expectedness_review_for_termination(self):
        text = "Termination agreement for prior rights."
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "RK Entertainments"}],
            "unresolved_counterparties": [],
        }
        opp = build_opportunity_spine(text, story)
        r = _check_addon_expectedness(opp)
        assert r["status"] == "review"

    def test_run_preflight_includes_addons_readiness(self):
        pages = [{
            "text": (
                "Distribution Agreement\n"
                "Option rights are granted.\n"
                "First negotiation and matching rights apply.\n"
                "Exercise notice within 45 days.\n"
                "Additional fee of 12% applies.\n"
            ),
            "char_count": 260,
            "image_coverage_ratio": 0.0,
            "page": 1,
        }]
        result = run_preflight(pages)
        assert "addons_readiness" in result
        addon = result["addons_readiness"]
        assert "status" in addon
        assert "checks" in addon
        assert "summary" in addon

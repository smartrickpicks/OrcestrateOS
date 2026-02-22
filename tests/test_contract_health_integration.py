import pytest
from server.preflight_engine import compute_preflight_health_score
from server.contract_health_runtime import reset_contract_health_runtime_cache


def _make_module(status, checks_data):
    checks = []
    for code, st, conf in checks_data:
        checks.append({"code": code, "label": code, "status": st, "confidence": conf, "value": "test", "reason": "test"})
    passed = sum(1 for c in checks if c["status"] == "pass")
    review = sum(1 for c in checks if c["status"] == "review")
    failed = sum(1 for c in checks if c["status"] == "fail")
    return {"status": status, "checks": checks, "summary": {"passed": passed, "review": review, "failed": failed}}


@pytest.fixture(autouse=True)
def clear_band_cache():
    reset_contract_health_runtime_cache()
    yield
    reset_contract_health_runtime_cache()


class TestComputePreflightHealthScore:
    def test_all_pass_green_gate(self):
        opp = _make_module("pass", [("OPP_1", "pass", 0.9), ("OPP_2", "pass", 0.95)])
        sch = _make_module("pass", [("SCH_1", "pass", 0.85), ("SCH_2", "pass", 0.9)])
        fin = _make_module("pass", [("FIN_1", "pass", 0.9), ("FIN_2", "pass", 0.85)])
        addon = _make_module("pass", [("ADDON_1", "pass", 0.8)])
        story = {"legal_entity_account": {"name": "Test Corp"}, "counterparties": [{"name": "Artist X"}]}
        result = compute_preflight_health_score("GREEN", opp, sch, fin, addon, story)
        assert result["raw_score"] >= 0.7
        assert result["calibrated_score"] >= 0.7
        assert result["band"] in ("VERY_HIGH_CONFIDENCE_HEALTHY", "HEALTHY_REVIEW_SPOTCHECK")
        assert result["gate_penalty"] == 0.0
        assert "opportunity_spine" in result["section_scores"]
        assert "financials_readiness" in result["section_scores"]
        assert "addons_readiness" in result["section_scores"]
        assert "entity_resolution" in result["section_scores"]

    def test_all_fail_red_gate(self):
        opp = _make_module("fail", [("OPP_1", "fail", 0.1)])
        sch = _make_module("fail", [("SCH_1", "fail", 0.0)])
        fin = _make_module("fail", [("FIN_1", "fail", 0.0)])
        addon = _make_module("fail", [("ADDON_1", "fail", 0.0)])
        story = {}
        result = compute_preflight_health_score("RED", opp, sch, fin, addon, story)
        assert result["raw_score"] == 0.0
        assert result["gate_penalty"] == 0.35
        assert result["band"] == "NEEDS_DETAILED_REVIEW"

    def test_mixed_yellow_gate(self):
        opp = _make_module("pass", [("OPP_1", "pass", 0.9)])
        sch = _make_module("review", [("SCH_1", "review", 0.5)])
        fin = _make_module("pass", [("FIN_1", "pass", 0.85)])
        addon = _make_module("fail", [("ADDON_1", "fail", 0.0)])
        story = {"legal_entity_account": {"name": "Legal"}, "counterparties": []}
        result = compute_preflight_health_score("YELLOW", opp, sch, fin, addon, story)
        assert 0.0 <= result["raw_score"] <= 1.0
        assert result["gate_penalty"] == 0.15
        assert result["calibration_version"]

    def test_none_modules(self):
        result = compute_preflight_health_score("GREEN", None, None, None, None, None)
        assert result["raw_score"] == 0.0
        assert result["band"] == "NEEDS_DETAILED_REVIEW"

    def test_entity_only_legal(self):
        story = {"legal_entity_account": {"name": "Corp"}, "counterparties": []}
        result = compute_preflight_health_score("GREEN", None, None, None, None, story)
        assert result["section_scores"]["entity_resolution"] == 0.6

    def test_entity_both(self):
        story = {"legal_entity_account": {"name": "Corp"}, "counterparties": [{"name": "A"}]}
        result = compute_preflight_health_score("GREEN", None, None, None, None, story)
        assert result["section_scores"]["entity_resolution"] == 1.0

    def test_moderate_confidence_band(self):
        opp = _make_module("pass", [("OPP_1", "pass", 0.7)])
        sch = _make_module("review", [("SCH_1", "review", 0.5)])
        fin = _make_module("review", [("FIN_1", "review", 0.5)])
        addon = _make_module("review", [("ADDON_1", "review", 0.4)])
        story = {"legal_entity_account": {"name": "Corp"}, "counterparties": []}
        result = compute_preflight_health_score("GREEN", opp, sch, fin, addon, story)
        assert result["band"] in ("MODERATE_CONFIDENCE", "HEALTHY_REVIEW_SPOTCHECK", "NEEDS_DETAILED_REVIEW")

    def test_band_names_valid(self):
        valid_bands = {"VERY_HIGH_CONFIDENCE_HEALTHY", "HEALTHY_REVIEW_SPOTCHECK", "MODERATE_CONFIDENCE", "NEEDS_DETAILED_REVIEW"}
        result = compute_preflight_health_score("GREEN", None, None, None, None, None)
        assert result["band"] in valid_bands

    def test_output_structure(self):
        result = compute_preflight_health_score("GREEN", None, None, None, None, None)
        assert "raw_score" in result
        assert "calibrated_score" in result
        assert "band" in result
        assert "calibration_version" in result
        assert "section_scores" in result
        assert "gate_penalty" in result
        for key in ("opportunity_spine", "schedule_structure", "financials_readiness", "addons_readiness", "entity_resolution"):
            assert key in result["section_scores"]

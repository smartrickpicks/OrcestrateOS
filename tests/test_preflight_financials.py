"""Tests for Financials Readiness preflight checks."""

from server.preflight_engine import (
    _extract_fin_revenue_model,
    _extract_fin_split_signals,
    _extract_fin_payment_timing,
    _extract_fin_thresholds,
    _check_financials_alignment,
    build_financials_readiness,
    build_opportunity_spine,
    build_schedule_structure,
    run_preflight,
)


class TestFinancialSignals:
    def test_revenue_model_pass(self):
        text = "For digital distribution revenue share and for synch licenses sync revenue applies."
        r = _extract_fin_revenue_model(text)
        assert r["status"] == "pass"

    def test_split_signals_detect_percentages(self):
        text = "Eighty percent (80%) of Revenue and Seventy Percent (70%) of Synch Revenue."
        r = _extract_fin_split_signals(text)
        assert r["status"] == "pass"
        assert 80 in r["splits"]
        assert 70 in r["splits"]

    def test_payment_timing_pass(self):
        text = "Payment shall be made within 30 days of invoice receipt."
        r = _extract_fin_payment_timing(text)
        assert r["status"] == "pass"
        assert "within 30 days" in r["value"]

    def test_thresholds_review_when_absent(self):
        text = "Revenue share applies. No threshold language."
        r = _extract_fin_thresholds(text)
        assert r["status"] in ("review", "pass")


class TestBuildFinancialsReadiness:
    def test_financials_readiness_shape(self):
        text = (
            "Distribution Agreement\n"
            "For Digital Distribution ... 80% of Revenue.\n"
            "For Synch licenses ... 70% of Synch Revenue.\n"
            "Payment within 30 days.\n"
        )
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "RK Entertainments"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        opp = build_opportunity_spine(text, story)
        sch = build_schedule_structure(text, story, opp)
        r = build_financials_readiness(text, opp, sch)
        assert "status" in r
        assert "checks" in r
        assert "summary" in r
        assert len(r["checks"]) == 5
        codes = [c["code"] for c in r["checks"]]
        assert "FIN_REVENUE_MODEL" in codes
        assert "FIN_SPLIT_SIGNALS" in codes
        assert "FIN_PAYMENT_TIMING" in codes
        assert "FIN_THRESHOLDS" in codes
        assert "FIN_ALIGNMENT" in codes

    def test_alignment_review_for_termination(self):
        text = "Termination Agreement with final settlement and payment language."
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "RK Entertainments"}],
            "unresolved_counterparties": [],
        }
        opp = build_opportunity_spine(text, story)
        sch = build_schedule_structure(text, story, opp)
        r = _check_financials_alignment(opp, sch)
        assert r["status"] in ("review", "pass")

    def test_run_preflight_includes_financials_readiness(self):
        pages = [{
            "text": (
                "Distribution Agreement\n"
                "For Digital Distribution, including download and streaming of Records.\n"
                "For Synch licenses: Seventy Percent (70%) of Synch Revenue.\n"
                "Eighty percent (80%) of Revenue.\n"
                "Payment within 30 days."
            ),
            "char_count": 300,
            "image_coverage_ratio": 0.0,
            "page": 1,
        }]
        result = run_preflight(pages)
        assert "financials_readiness" in result
        fin = result["financials_readiness"]
        assert "status" in fin
        assert "checks" in fin
        assert "summary" in fin

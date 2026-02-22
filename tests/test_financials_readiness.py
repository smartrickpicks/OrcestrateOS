import pytest
from server.preflight_engine import (
    build_financials_readiness,
    _extract_financial_amounts,
    _extract_financial_rates,
    _extract_payment_terms,
    _extract_currency_signals,
    _check_financial_completeness,
)


class TestFinancialAmounts:
    def test_no_text(self):
        r = _extract_financial_amounts("")
        assert r["status"] == "fail"

    def test_pass_with_amounts_and_keywords(self):
        text = "The royalty rate shall be 15% of net receipts. Advance of $50,000 payable upon execution."
        r = _extract_financial_amounts(text)
        assert r["status"] == "pass"
        assert r["confidence"] >= 0.8

    def test_review_with_partial(self):
        text = "The fee structure is outlined in Schedule B."
        r = _extract_financial_amounts(text)
        assert r["status"] == "review"

    def test_fail_no_markers(self):
        text = "This agreement is between Party A and Party B regarding distribution rights."
        r = _extract_financial_amounts(text)
        assert r["status"] == "fail"


class TestFinancialRates:
    def test_no_text(self):
        r = _extract_financial_rates("")
        assert r["status"] == "fail"

    def test_pass_with_rates_and_keywords(self):
        text = "Artist shall receive a royalty rate of 18% of net revenue. Revenue share is 70/30 split."
        r = _extract_financial_rates(text)
        assert r["status"] == "pass"
        assert r["confidence"] >= 0.8

    def test_review_with_partial(self):
        text = "The percentage of revenue shall be determined per the schedule."
        r = _extract_financial_rates(text)
        assert r["status"] == "review"

    def test_fail_no_rates(self):
        text = "The parties agree to the terms stated herein."
        r = _extract_financial_rates(text)
        assert r["status"] == "fail"


class TestPaymentTerms:
    def test_pass_multiple_terms(self):
        text = "Payment terms are net 30. Royalties payable quarterly within 60 days of accounting period close."
        r = _extract_payment_terms(text)
        assert r["status"] == "pass"

    def test_review_single(self):
        text = "All amounts are payable upon receipt."
        r = _extract_payment_terms(text)
        assert r["status"] == "review"

    def test_fail_none(self):
        text = "This is a standard agreement between the parties."
        r = _extract_payment_terms(text)
        assert r["status"] == "fail"


class TestCurrencySignals:
    def test_pass_with_currency(self):
        text = "All amounts stated in USD."
        r = _extract_currency_signals(text)
        assert r["status"] == "pass"

    def test_pass_with_symbol(self):
        text = "Advance of $100,000."
        r = _extract_currency_signals(text)
        assert r["status"] == "pass"

    def test_review_no_currency(self):
        text = "The parties agree to the payment schedule."
        r = _extract_currency_signals(text)
        assert r["status"] == "review"


class TestFinancialCompleteness:
    def test_full_completeness(self):
        text = "Advance of $50,000. Royalty rate of 15%. Payment terms are net 30, payable quarterly."
        r = _check_financial_completeness(text, None)
        assert r["status"] == "pass"
        assert "3/3" in r["value"]

    def test_partial_completeness(self):
        text = "Advance of $50,000 upon execution. Royalty rate is 18%."
        r = _check_financial_completeness(text, None)
        assert r["status"] in ("pass", "review")

    def test_termination_contract_lenient(self):
        spine = {"checks": [{"code": "OPP_CONTRACT_TYPE", "status": "pass", "value": "termination", "confidence": 0.9}]}
        text = "Termination effective as of the actual termination date. Payment of $10,000."
        r = _check_financial_completeness(text, spine)
        assert r["status"] in ("pass", "review")


class TestBuildFinancialsReadiness:
    def test_full_financial_contract(self):
        text = (
            "DISTRIBUTION AGREEMENT\n"
            "Advance of $250,000 USD payable upon execution.\n"
            "Royalty rate: 18% of net receipts.\n"
            "Revenue share: 70/30 split.\n"
            "Payment terms: Net 30, payable quarterly.\n"
            "Accounting periods end March 31, June 30, September 30, December 31.\n"
        )
        result = build_financials_readiness(text, None)
        assert result["status"] in ("pass", "review")
        assert len(result["checks"]) == 5
        assert result["summary"]["passed"] >= 3

    def test_empty_text(self):
        result = build_financials_readiness("", None)
        assert result["status"] == "fail"
        assert result["summary"]["failed"] >= 2

    def test_return_structure(self):
        result = build_financials_readiness("Some basic text.", None)
        assert "status" in result
        assert "checks" in result
        assert "summary" in result
        for ck in result["checks"]:
            assert "code" in ck
            assert "label" in ck
            assert "status" in ck
            assert "confidence" in ck
            assert ck["code"].startswith("FIN_")

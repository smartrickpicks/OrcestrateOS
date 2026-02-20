"""Tests for deterministic contract rules classification."""

from server.preflight_rules import classify_contract, get_expected_schedule_types, get_schedule_type_priority


def test_classify_contract_distribution():
    text = "Distribution Agreement for digital distribution and sync licensing."
    r = classify_contract("distribution", text)
    assert r["contract_category"] == "Distribution"
    assert "distro_sync_existing_masters" in r["expected_schedule_types"]
    assert isinstance(r["subtypes_allowed"], list)


def test_classify_contract_termination_flavor():
    text = "Termination Agreement. The parties mutually agree to terminate."
    r = classify_contract("termination", text)
    assert r["contract_category"] == "Termination"
    assert r["termination_flavor"] in ("mutual", "for_cause", "convenience", "expiry", "reversion", None)
    if r["termination_flavor"] == "mutual":
        assert "Mutual" in (r["termination_flavor_label"] or "")


def test_helpers_return_lists():
    assert isinstance(get_expected_schedule_types("distribution"), list)
    assert isinstance(get_schedule_type_priority(), list)

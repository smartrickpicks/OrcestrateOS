"""Tests for Schedule Structure preflight checks."""

from server.preflight_engine import (
    _extract_schedule_presence,
    _extract_schedule_type,
    _extract_ownership_signals,
    _extract_lifecycle_signals,
    _check_schedule_role_alignment,
    build_schedule_structure,
    build_opportunity_spine,
    run_preflight,
)
from server.preflight_rules import classify_contract


class TestSchedulePresence:
    def test_schedule_presence_pass(self):
        text = "Distribution Agreement\nSchedule 1 - Catalog Acquisition"
        opp = {"checks": [{"code": "OPP_CONTRACT_TYPE", "value": "distribution"}]}
        r = _extract_schedule_presence(text, opp)
        assert r["status"] == "pass"

    def test_schedule_presence_review_for_termination_without_schedule(self):
        text = "Termination Agreement\nThis notice terminates prior terms."
        opp = {"checks": [{"code": "OPP_CONTRACT_TYPE", "value": "termination"}]}
        r = _extract_schedule_presence(text, opp)
        assert r["status"] == "review"

    def test_schedule_presence_fail(self):
        text = "Random agreement text with no bundle references"
        opp = {"checks": [{"code": "OPP_CONTRACT_TYPE", "value": "distribution"}]}
        r = _extract_schedule_presence(text, opp)
        assert r["status"] == "fail"


class TestScheduleType:
    def test_schedule_type_detects_distro_sync(self):
        text = "Distro & Sync - Existing Masters\nSchedule 1"
        r = _extract_schedule_type(text)
        assert r["status"] in ("pass", "review")
        assert r["value"] == "distro_sync_existing_masters"
        assert len(r["candidates"]) >= 1

    def test_schedule_type_ambiguous_review(self):
        text = "Schedule 1 catalog acquisition and distro & sync for existing masters"
        r = _extract_schedule_type(text)
        assert r["status"] in ("review", "pass")
        assert len(r["candidates"]) >= 1


class TestScheduleSignals:
    def test_ownership_signals_pass(self):
        text = "Master ownership and composition ownership with asset owner details."
        r = _extract_ownership_signals(text)
        assert r["status"] == "pass"

    def test_lifecycle_signals_review_or_pass(self):
        text = "Termination notice and offboard date to be confirmed."
        r = _extract_lifecycle_signals(text)
        assert r["status"] in ("review", "pass")


class TestScheduleRoleAlignment:
    def test_role_alignment_pass(self):
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "1888 Records"}],
            "unresolved_counterparties": [],
        }
        r = _check_schedule_role_alignment(story)
        assert r["status"] == "pass"

    def test_role_alignment_review_when_unresolved(self):
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [],
            "unresolved_counterparties": ["RK Entertainments"],
        }
        r = _check_schedule_role_alignment(story)
        assert r["status"] == "review"


class TestBuildScheduleStructure:
    def test_build_schedule_structure_shape(self):
        text = "Distribution Agreement\nSchedule 1\nMaster ownership\nEffective date: 01/01/2024"
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "1888 Records"}],
            "unresolved_counterparties": [],
            "requires_manual_confirmation": False,
        }
        opp = build_opportunity_spine(text, story)
        r = build_schedule_structure(text, story, opp)
        assert "status" in r
        assert "checks" in r
        assert "summary" in r
        assert len(r["checks"]) == 5
        codes = [c["code"] for c in r["checks"]]
        assert "SCH_PRESENCE" in codes
        assert "SCH_TYPE" in codes
        assert "SCH_OWNERSHIP" in codes
        assert "SCH_LIFECYCLE" in codes
        assert "SCH_ROLE_ALIGNMENT" in codes

    def test_run_preflight_includes_schedule_structure(self):
        pages = [{"text": "Distribution Agreement\nSchedule 1\nMaster ownership\nTerritory: Worldwide", "char_count": 120, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        assert "schedule_structure" in result
        sch = result["schedule_structure"]
        assert "status" in sch
        assert "checks" in sch
        assert "summary" in sch


class TestDistroSyncScheduleType:
    def test_distro_sync_suppresses_general_schedule(self):
        text = "Distribution Agreement\nDistro & Sync - Existing Masters\nSchedule 1\nfor digital distribution and synch licenses"
        r = _extract_schedule_type(text, contract_type_value="distribution")
        assert r["value"] == "distro_sync_existing_masters"
        cand_values = [c["value"] for c in r["candidates"]]
        assert "general_schedule" not in cand_values

    def test_distro_sync_with_catalog_acquisition(self):
        text = "Distribution Agreement\nSchedule 1 catalog acquisition\nDistro & Sync for existing masters"
        r = _extract_schedule_type(text, contract_type_value="distribution")
        assert r["value"] in ("distro_sync_existing_masters", "catalog_acquisition_masters")
        assert len(r["candidates"]) >= 2
        cand_values = [c["value"] for c in r["candidates"]]
        assert "general_schedule" not in cand_values

    def test_general_schedule_kept_when_no_specific(self):
        text = "Service Agreement\nSchedule A - Service Terms\nExhibit 1"
        r = _extract_schedule_type(text, contract_type_value="service")
        assert r["value"] == "general_schedule"

    def test_no_contract_type_general_still_suppressed_when_specific_wins(self):
        text = "Distro & Sync for existing masters\nSchedule 1\nDigital distribution and synch revenue"
        r = _extract_schedule_type(text)
        assert r["value"] == "distro_sync_existing_masters"

    def test_schedule_type_priority_ordering(self):
        text = "Distribution Agreement\nDistro & Sync for existing masters\nSchedule 1 catalog acquisition\nAppendix"
        r = _extract_schedule_type(text, contract_type_value="distribution")
        assert r["candidates"][0]["value"] in ("distro_sync_existing_masters", "catalog_acquisition_masters")
        cand_values = [c["value"] for c in r["candidates"]]
        assert "general_schedule" not in cand_values


class TestTerminationScheduleType:
    def test_termination_schedule_type(self):
        text = "Termination Agreement\nTermination schedule attached.\nActual termination date: March 1, 2025.\nOffboard procedures."
        r = _extract_schedule_type(text, contract_type_value="termination")
        assert r["value"] == "termination_schedule"

    def test_termination_flavor_mutual_in_preflight(self):
        pages = [{"text": "Termination Agreement\n\nThe parties mutually agree to terminate.\nMutual termination by mutual agreement.\nTermination schedule attached.\nActual termination date: March 1, 2025.", "char_count": 150, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        cc = result["contract_classification"]
        assert cc["termination_flavor"] == "mutual"
        assert cc["termination_flavor_label"] == "Mutual Termination"
        sch = result["schedule_structure"]
        sch_type = next(c for c in sch["checks"] if c["code"] == "SCH_TYPE")
        assert sch_type["value"] == "termination_schedule"

    def test_termination_flavor_for_cause_in_preflight(self):
        pages = [{"text": "Termination Agreement\n\nDue to material breach and failure to cure.\nTermination notice effective immediately.\nTermination schedule.", "char_count": 130, "image_coverage_ratio": 0.0, "page": 1}]
        result = run_preflight(pages)
        cc = result["contract_classification"]
        assert cc["termination_flavor"] == "for_cause"

    def test_build_schedule_structure_passes_contract_type(self):
        text = "Distribution Agreement\nDistro & Sync for existing masters\nSchedule 1 catalog acquisition\nMaster ownership\nEffective date"
        story = {
            "legal_entity_account": {"name": "Ostereo Limited"},
            "counterparties": [{"name": "1888 Records"}],
            "unresolved_counterparties": [],
        }
        opp = build_opportunity_spine(text, story)
        r = build_schedule_structure(text, story, opp)
        sch_type = next(c for c in r["checks"] if c["code"] == "SCH_TYPE")
        assert sch_type["value"] != "general_schedule"
        assert sch_type["value"] in ("distro_sync_existing_masters", "catalog_acquisition_masters")

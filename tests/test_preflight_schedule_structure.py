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

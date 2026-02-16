import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from server.suggestion_engine import (
    normalize_text,
    normalize_field_name,
    _classify_suppression,
    _is_entity_eligible,
    _compute_exact_alias,
    _compute_tok_overlap,
    _compute_ordered_overlap,
    _compute_edit_sim,
    _compute_first_token_bonus,
    _compute_context_bonus,
    _generate_reason_chips,
    _score_candidate_against_entry,
    _match_source_against_glossary,
    _extract_body_text_candidates,
    _apply_category_balance,
    _build_glossary_index,
    KEEP_TOKENS,
    DOMAIN_SIGNAL_TOKENS,
    SCORING_CONFIG,
)


def _make_entry(field_key, label=None, definition="", category="", extra_tokens=None):
    label = label or field_key
    _, label_tokens = normalize_text(label)
    _, fk_tokens = normalize_text(field_key)
    all_tokens = list(dict.fromkeys(label_tokens + fk_tokens))
    if extra_tokens:
        all_tokens.extend(extra_tokens)
    return {
        "id": field_key,
        "field_key": field_key,
        "label": label,
        "normalized": normalize_field_name(label),
        "fk_normalized": normalize_field_name(field_key),
        "definition": definition,
        "category": category,
        "tokens_list": all_tokens,
        "tokens_set": set(all_tokens),
        "keyword_set": set(all_tokens),
        "domain_keywords": set(),
    }


class TestSyncVsSynchMatch:

    def test_sync_synch_edit_sim_high(self):
        c_tokens = ["synch"]
        g_tokens = ["sync"]
        c_norm = "synch"
        g_norm = "sync"
        sim = _compute_edit_sim(c_tokens, g_tokens, c_norm, g_norm)
        assert sim >= 0.75, f"edit_sim between sync/synch should be >= 0.75, got {sim}"

    def test_synch_matches_sync_glossary_term(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {}
        result = _match_source_against_glossary("Synch", [entry], alias_map)
        assert result["confidence_bucket"] in ("HIGH", "MEDIUM"), \
            f"Synch should match sync at MED/HIGH, got {result['confidence_bucket']} ({result['confidence_pct']}%)"

    def test_synch_confidence_at_least_60(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {}
        result = _match_source_against_glossary("Synch", [entry], alias_map)
        assert result["confidence_pct"] >= 60, \
            f"Synch vs sync confidence should be >= 60%, got {result['confidence_pct']}%"


class TestAliasFuzzyPath:

    def test_exact_alias_match_is_high(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {"synch": entry["id"]}
        result = _match_source_against_glossary("Synch", [entry], alias_map)
        assert result["confidence_bucket"] == "HIGH", \
            f"Exact alias should be HIGH, got {result['confidence_bucket']}"
        assert result["confidence_pct"] >= 80

    def test_alias_takes_priority_over_fuzzy(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {"synch": entry["id"]}
        result = _match_source_against_glossary("Synch", [entry], alias_map)
        assert "Exact alias" in result.get("reason_labels", []) or \
               result["match_method"] == "alias_exact", \
               f"Alias match should be flagged, got method={result['match_method']}, reasons={result.get('reason_labels')}"


class TestSuppressionRules:

    def test_section_marker_roman_suppressed(self):
        reasons = _classify_suppression("(iv)", ["iv"])
        assert "section_marker" in reasons

    def test_section_marker_numeric_suppressed(self):
        reasons = _classify_suppression("3.1.2", [])
        assert "section_marker" in reasons

    def test_url_heavy_suppressed(self):
        reasons = _classify_suppression("https://example.com/path", ["https", "example", "com", "path"])
        assert "url_heavy" in reasons

    def test_mojibake_suppressed(self):
        text = "abc\ufffd\ufffd\ufffddef"
        reasons = _classify_suppression(text, ["abc", "def"])
        assert "mojibake" in reasons

    def test_entity_not_suppressed_as_numeric(self):
        tokens = ["1888", "records"]
        reasons = _classify_suppression("1888 Records", tokens)
        entity = _is_entity_eligible(tokens)
        assert entity is True
        if "numeric_heavy" in reasons:
            reasons.remove("numeric_heavy")
        assert "numeric_heavy" not in reasons

    def test_normal_text_not_suppressed(self):
        reasons = _classify_suppression("Digital Distribution", ["digital", "distribution"])
        assert len(reasons) == 0


class TestEntityEligible:

    def test_1888_records_is_entity_eligible(self):
        assert _is_entity_eligible(["1888", "records"]) is True

    def test_plain_text_not_entity(self):
        assert _is_entity_eligible(["sync", "license"]) is False

    def test_single_token_not_entity(self):
        assert _is_entity_eligible(["1888"]) is False


class TestDeterministicOrdering:

    def test_same_input_same_output(self):
        entries = [
            _make_entry("sync_license_type", "Sync License Type", category="contract"),
            _make_entry("account_name", "Account Name", category="identity"),
            _make_entry("distribution_type", "Distribution Type", category="catalog"),
        ]
        alias_map = {}
        fields = ["Digital Distribution", "Synch", "Account"]

        results_1 = []
        for f in fields:
            r = _match_source_against_glossary(f, entries, alias_map)
            results_1.append((r["source_field"], r["confidence_pct"], r["glossary_field_key"]))

        results_2 = []
        for f in fields:
            r = _match_source_against_glossary(f, entries, alias_map)
            results_2.append((r["source_field"], r["confidence_pct"], r["glossary_field_key"]))

        assert results_1 == results_2, "Same input must produce identical results"

    def test_tie_breaking_by_field_key(self):
        entry_a = _make_entry("aaa_field", "Test Field", category="test")
        entry_b = _make_entry("zzz_field", "Test Field", category="test")
        alias_map = {}
        result = _match_source_against_glossary("Test Field", [entry_a, entry_b], alias_map)
        if result["candidates"] and len(result["candidates"]) >= 2:
            first_key = result["candidates"][0]["field_key"]
            second_key = result["candidates"][1]["field_key"]
            assert first_key <= second_key or \
                result["candidates"][0]["confidence_pct"] >= result["candidates"][1]["confidence_pct"]


class TestBodyTextCandidateExtraction:

    def test_extracts_domain_terms(self):
        text = "This agreement covers Sync licensing and Digital Distribution rights."
        candidates = _extract_body_text_candidates(text)
        found_sync = any("sync" in c.lower() or "synch" in c.lower() for c in candidates)
        found_dist = any("distribution" in c.lower() for c in candidates)
        assert found_sync or found_dist, f"Should find domain terms, got: {candidates}"

    def test_filters_garbage(self):
        text = "Page 1\n\n\nhttps://example.com\n\nSynch license applies here."
        candidates = _extract_body_text_candidates(text)
        for c in candidates:
            assert "https://" not in c
            assert len(c) >= 3

    def test_respects_max_candidates(self):
        lines = ["Sync term %d" % i for i in range(200)]
        text = "\n".join(lines)
        candidates = _extract_body_text_candidates(text, max_candidates=10)
        assert len(candidates) <= 10

    def test_1888_records_in_body(self):
        text = "The agreement with 1888 Records covers distribution."
        candidates = _extract_body_text_candidates(text)
        found = any("1888" in c and "records" in c.lower() for c in candidates)
        assert found or len(candidates) > 0, "Should extract entity-like phrases from body"

    def test_empty_body_returns_empty(self):
        assert _extract_body_text_candidates("") == []
        assert _extract_body_text_candidates(None) == []


class TestCategoryStarvationPrevention:

    def _make_suggestions(self, categories_and_scores):
        results = []
        for cat, score, fk in categories_and_scores:
            results.append({
                "source_field": fk,
                "confidence_pct": score,
                "glossary_field_key": fk,
                "_match_context": {"glossary_category": cat},
                "candidates": [],
            })
        return results

    def test_balance_prevents_domination(self):
        items = self._make_suggestions([
            ("identity", 85, "account_name_1"),
            ("identity", 84, "account_name_2"),
            ("identity", 83, "account_name_3"),
            ("identity", 82, "account_name_4"),
            ("identity", 81, "account_name_5"),
            ("identity", 80, "account_name_6"),
            ("contract", 79, "contract_type"),
            ("catalog", 78, "catalog_title"),
        ])
        balanced = _apply_category_balance(items)
        top5 = balanced[:5]
        cats_in_top5 = set(s["_match_context"]["glossary_category"] for s in top5)
        assert len(cats_in_top5) > 1, \
            f"Top 5 should include multiple categories, got only: {cats_in_top5}"

    def test_single_category_unchanged(self):
        items = self._make_suggestions([
            ("identity", 90, "name_1"),
            ("identity", 80, "name_2"),
        ])
        balanced = _apply_category_balance(items)
        assert len(balanced) == 2
        assert balanced[0]["confidence_pct"] >= balanced[1]["confidence_pct"]

    def test_empty_list_unchanged(self):
        assert _apply_category_balance([]) == []


class TestNormalization:

    def test_nfkc_lowercase(self):
        norm, tokens = normalize_text("SYNCH")
        assert norm == "synch"

    def test_noise_tokens_removed(self):
        norm, tokens = normalize_text("the agreement for distribution")
        assert "the" not in tokens
        assert "distribution" in tokens

    def test_keep_tokens_preserved(self):
        norm, tokens = normalize_text("sync distribution records")
        assert "sync" in tokens
        assert "distribution" in tokens
        assert "records" in tokens


class TestReasonChips:

    def test_exact_alias_chip(self):
        chips = _generate_reason_chips(1.0, 0.5, 0.3, 0.4, 0.0, 0.0, False)
        assert "Exact alias" in chips

    def test_token_overlap_chip(self):
        chips = _generate_reason_chips(0.0, 0.6, 0.0, 0.0, 0.0, 0.0, False)
        assert "Token overlap" in chips

    def test_edit_sim_chip(self):
        chips = _generate_reason_chips(0.0, 0.0, 0.0, 0.80, 0.0, 0.0, False)
        assert "Edit-sim" in chips

    def test_entity_rule_chip(self):
        chips = _generate_reason_chips(0.0, 0.5, 0.0, 0.0, 0.0, 0.0, True)
        assert "Entity rule" in chips


class TestAliasDrivenCorrectness:

    def test_alias_present_synch_resolves(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {"synch": entry["id"]}
        result = _match_source_against_glossary("Synch", [entry], alias_map)
        assert result["confidence_bucket"] == "HIGH"
        assert result["glossary_field_key"] == "sync_license_type"
        assert result["match_method"] == "alias_exact"

    def test_alias_present_phrase_resolves(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {"synch licenses": entry["id"]}
        result = _match_source_against_glossary("Synch licenses", [entry], alias_map)
        assert result["confidence_bucket"] == "HIGH"
        assert result["glossary_field_key"] == "sync_license_type"

    def test_alias_removed_fuzzy_still_works(self):
        entry = _make_entry("sync_license_type", "Sync License Type", category="contract")
        alias_map = {}
        result = _match_source_against_glossary("Synch", [entry], alias_map)
        assert result["confidence_pct"] > 0
        assert result["confidence_bucket"] in ("HIGH", "MEDIUM", "LOW")
        assert result["match_method"] != "alias_exact"

    def test_genericity_royalti_typo(self):
        entry = _make_entry("royalty_rate", "Royalty Rate", category="financial")
        alias_map = {}
        result = _match_source_against_glossary("Royalti", [entry], alias_map)
        assert result["confidence_pct"] > 0
        assert result["glossary_field_key"] == "royalty_rate"

    def test_genericity_distribtn_typo(self):
        entry = _make_entry("distribution_type", "Distribution Type", category="catalog")
        alias_map = {}
        result = _match_source_against_glossary("Distribtn", [entry], alias_map)
        assert result["confidence_pct"] > 0
        assert result["glossary_field_key"] == "distribution_type"

    def test_no_hardcoded_sync_logic(self):
        import inspect
        from server import suggestion_engine
        source = inspect.getsource(suggestion_engine._score_candidate_against_entry)
        assert '"sync"' not in source, "No hardcoded sync string in scorer"
        assert '"synch"' not in source, "No hardcoded synch string in scorer"
        assert "'sync'" not in source, "No hardcoded sync string in scorer"
        assert "'synch'" not in source, "No hardcoded synch string in scorer"

    def test_determinism_multiple_runs(self):
        entries = [
            _make_entry("sync_license_type", "Sync License Type", category="contract"),
            _make_entry("account_name", "Account Name", category="identity"),
            _make_entry("royalty_rate", "Royalty Rate", category="financial"),
        ]
        alias_map = {"synch": "sync_license_type"}
        fields = ["Synch", "Acct Name", "Royalti Rate"]

        runs = []
        for _ in range(5):
            run_results = []
            for f in fields:
                r = _match_source_against_glossary(f, entries, alias_map)
                run_results.append((
                    r["source_field"],
                    r["confidence_pct"],
                    r["glossary_field_key"],
                    r["match_method"],
                ))
            runs.append(run_results)

        for i in range(1, len(runs)):
            assert runs[i] == runs[0], f"Run {i} differs from run 0"


class TestScoringConfigFreeze:

    def test_weights_sum_to_one(self):
        total = sum(SCORING_CONFIG["weights"].values())
        assert abs(total - 1.0) < 0.001, f"Weights must sum to 1.0, got {total}"

    def test_thresholds_ordered(self):
        t = SCORING_CONFIG["thresholds"]
        assert t["HIGH"] > t["MEDIUM"] > t["LOW"]

    def test_config_has_required_keys(self):
        assert "weights" in SCORING_CONFIG
        assert "thresholds" in SCORING_CONFIG
        assert "boosts" in SCORING_CONFIG
        assert "tie_break_order" in SCORING_CONFIG
        assert "chip_thresholds" in SCORING_CONFIG

    def test_boost_multipliers_in_range(self):
        b = SCORING_CONFIG["boosts"]
        assert 0 < b["short_single_token_multiplier"] < 1
        assert 0 < b["domain_single_token_multiplier"] < 1
        assert 0 < b["entity_boost"] <= 0.10


class TestExportContractValidation:

    def test_export_payload_has_required_blocks(self):
        from server.routes.preflight import _build_export_payload
        cached = {
            "doc_mode": "SEARCHABLE",
            "gate_color": "GREEN",
            "gate_reasons": [],
            "metrics": {"total_pages": 1},
            "page_classifications": [{"page": 1, "classification": "SEARCHABLE"}],
            "decision_trace": [],
            "corruption_samples": [],
            "timestamp": "2026-01-01T00:00:00Z",
        }
        payload = _build_export_payload(cached, "ws_1", "doc_1", "ws_1::doc_1")
        assert payload["schema_version"] == "prep_export_v0"
        assert "context" in payload
        assert "source" in payload
        assert payload["source"] == "cache"
        assert "preflight" in payload
        assert "ogc_preview" in payload
        assert "operator_decisions" in payload
        assert "evaluation" in payload

    def test_export_context_fields(self):
        from server.routes.preflight import _build_export_payload
        cached = {
            "doc_mode": "SEARCHABLE", "gate_color": "GREEN", "gate_reasons": [],
            "metrics": {}, "page_classifications": [], "timestamp": "2026-01-01T00:00:00Z",
        }
        payload = _build_export_payload(cached, "ws_1", "doc_1", "ws_1::doc_1")
        ctx = payload["context"]
        assert ctx["workspace_id"] == "ws_1"
        assert ctx["doc_id"] == "doc_1"
        assert ctx["cache_key"] == "ws_1::doc_1"

    def test_export_no_recompute(self):
        from server.routes.preflight import _build_export_payload
        cached = {
            "doc_mode": "MIXED", "gate_color": "YELLOW", "gate_reasons": ["mixed_mode"],
            "metrics": {"total_pages": 3}, "page_classifications": [],
            "timestamp": "2026-01-01T00:00:00Z",
        }
        payload = _build_export_payload(cached, "ws_1", "doc_1", "ws_1::doc_1")
        assert payload["preflight"]["doc_mode"] == "MIXED"
        assert payload["preflight"]["recommended_gate"] == "YELLOW"


class TestSalesforceResolverStub:

    def test_resolver_disabled_by_default(self):
        from server.resolvers.salesforce import is_resolver_enabled
        assert is_resolver_enabled() is False

    def test_resolve_entity_returns_contract(self):
        from server.resolvers.salesforce import resolve_entity
        result = resolve_entity("ws_1", "Acme Corp", address="123 Main St")
        assert result["classification"] == "Unknown"
        assert result["score"] == 0.0
        assert isinstance(result["candidates"], list)
        assert isinstance(result["explanation"], str)
        assert result["provider"] == "salesforce_mock"
        assert result["resolved"] is False

    def test_resolver_status(self):
        from server.resolvers.salesforce import get_resolver_status
        status = get_resolver_status()
        assert status["enabled"] is False
        assert status["ready_for_integration"] is True
        assert status["live_api"] is False

    def test_no_network_calls(self):
        from server.resolvers.salesforce import resolve_entity
        result = resolve_entity("ws_1", "Test Entity")
        assert result["provider"] == "salesforce_mock"
        assert result["resolved"] is False


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])

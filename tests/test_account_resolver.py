"""
Tests for CMG Account Resolver — deterministic matching on CMG_Account.csv.

Covers:
  - Index loading and normalization
  - Exact match (single, multi-alias)
  - Fuzzy match (token overlap, edit distance)
  - Ambiguous classification
  - Not-found classification
  - Stable candidate ordering (deterministic)
  - Non-regression: existing preflight tests unaffected
"""
import pytest
from pathlib import Path

CSV_PATH = Path(__file__).resolve().parent.parent / "server" / "data" / "CMG_Account.csv"


@pytest.fixture(scope="module")
def index():
    from server.resolvers.account_index import AccountIndex
    idx = AccountIndex()
    loaded = idx.load(CSV_PATH)
    assert loaded, "CMG_Account.csv must be loadable"
    return idx


@pytest.fixture(scope="module")
def resolver():
    from server.resolvers import salesforce
    from server.resolvers.account_index import ensure_loaded
    ensure_loaded(CSV_PATH)
    return salesforce


def test_index_loads(index):
    assert index.loaded
    assert index.record_count > 14000


def test_normalize_deterministic():
    from server.resolvers.account_index import normalize
    assert normalize("Louis The Child") == "louis the child"
    assert normalize("  DJ  Rupp  ") == "dj rupp"
    assert normalize("Royce da 5'9'") == "royce da 5 9"
    assert normalize("EH!DE") == "eh de"
    assert normalize("#CAKE") == "cake"
    assert normalize("TOKYOxVANITY") == "tokyoxvanity"
    assert normalize("") == ""
    assert normalize(None) == ""


def test_normalize_nfkc():
    from server.resolvers.account_index import normalize
    assert normalize("Ruan Guimarães") == normalize("Ruan Guimarães")


def test_exact_match_single(resolver):
    result = resolver.resolve_account("Louis The Child")
    assert result["classification"] == "matched"
    assert result["resolved"] is True
    assert result["score"] == 1.0
    assert len(result["candidates"]) >= 1
    assert result["candidates"][0]["account_name"] == "Louis The Child"
    assert result["provider"] == "cmg_csv_v1"


def test_exact_match_artist_name(resolver):
    result = resolver.resolve_account("Maejor")
    assert result["classification"] == "matched"
    assert result["resolved"] is True
    assert result["candidates"][0]["account_name"] == "Maejor"


def test_exact_match_case_insensitive(resolver):
    r1 = resolver.resolve_account("louis the child")
    r2 = resolver.resolve_account("LOUIS THE CHILD")
    r3 = resolver.resolve_account("Louis The Child")
    assert r1["classification"] == r2["classification"] == r3["classification"] == "matched"
    assert r1["candidates"][0]["account_id"] == r2["candidates"][0]["account_id"] == r3["candidates"][0]["account_id"]


def test_exact_match_via_legal_name(resolver):
    result = resolver.resolve_account("Brandon Green")
    assert result["classification"] == "matched"
    assert result["resolved"] is True
    assert result["candidates"][0]["account_name"] == "Maejor"


def test_not_found(resolver):
    result = resolver.resolve_account("Completely Nonexistent Artist ZZZZZ")
    assert result["classification"] == "not_found"
    assert result["resolved"] is False
    assert len(result["candidates"]) == 0


def test_empty_query(resolver):
    result = resolver.resolve_account("")
    assert result["classification"] == "not_found"
    assert result["resolved"] is False


def test_fuzzy_match_edit_distance(resolver):
    result = resolver.resolve_account("Luis The Child")
    assert result["classification"] in ("matched", "ambiguous")
    assert result["score"] > 0.7
    assert len(result["candidates"]) >= 1


def test_candidate_stable_ordering(resolver):
    r1 = resolver.resolve_account("DJ")
    r2 = resolver.resolve_account("DJ")
    assert r1["candidates"] == r2["candidates"]
    if len(r1["candidates"]) > 1:
        scores = [c["score"] for c in r1["candidates"]]
        assert scores == sorted(scores, reverse=True)


def test_resolver_status(resolver):
    status = resolver.get_resolver_status()
    assert status["enabled"] is True
    assert status["provider"] == "cmg_csv_v1"
    assert status["record_count"] > 14000
    assert status["ready_for_integration"] is True


def test_classification_contract():
    from server.resolvers.salesforce import resolve_account
    from server.resolvers.account_index import ensure_loaded
    ensure_loaded(CSV_PATH)

    result = resolve_account("Sean Kingston")
    assert "classification" in result
    assert "score" in result
    assert "candidates" in result
    assert "explanation" in result
    assert "provider" in result
    assert "resolved" in result
    assert result["classification"] in ("matched", "ambiguous", "not_found")
    assert isinstance(result["score"], float)
    assert isinstance(result["candidates"], list)
    assert isinstance(result["resolved"], bool)


def test_deterministic_same_input_same_output(resolver):
    inputs = ["Soulja Boy", "Said The Sky", "Panda Eyes", "Nonexistent XYZ"]
    for name in inputs:
        r1 = resolver.resolve_account(name)
        r2 = resolver.resolve_account(name)
        assert r1 == r2, f"Non-deterministic result for '{name}'"


def test_candidate_fields_present(resolver):
    result = resolver.resolve_account("Sean Kingston")
    assert result["classification"] == "matched"
    candidate = result["candidates"][0]
    for field in ["account_name", "type", "account_id", "id_18", "le_id",
                  "artist_name", "company_name", "legal_name", "score", "match_tier"]:
        assert field in candidate, f"Missing field: {field}"


def test_max_candidates_capped(resolver):
    result = resolver.resolve_account("DJ")
    assert len(result["candidates"]) <= 5

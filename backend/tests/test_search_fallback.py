"""Search must still return results when the LLM reranker or vector search is unavailable."""
from types import SimpleNamespace
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from tests.conftest import import_app

main = import_app()
from app.api import search as search_api  # noqa: E402
from app.api.search import fallback_order  # noqa: E402
from app.services.db_service import db_service  # noqa: E402
from app.security import create_access_token  # noqa: E402

client = TestClient(main.app)


def P(pid, title="t", platform="arxiv"):
    return SimpleNamespace(paper_id=pid, platform=platform, title=title, abstract="a", authors=["x"],
                           categories=["c"], pdf_url=f"http://x/{pid}.pdf", published_date="2026-01-01",
                           updated_date="2026-01-01")


# ---------- fallback_order ----------
def test_fallback_follows_retrieval_order():
    papers = [P("c"), P("a"), P("b")]
    pairs = [("a", "arxiv"), ("b", "arxiv"), ("c", "arxiv")]
    assert [p.paper_id for p in fallback_order(papers, pairs, 10)] == ["a", "b", "c"]


def test_fallback_unknown_ids_go_last_in_original_order():
    papers = [P("z"), P("a"), P("y")]
    assert [p.paper_id for p in fallback_order(papers, [("a", "arxiv")], 10)] == ["a", "z", "y"]


def test_fallback_respects_limit_and_platform():
    papers = [P("a", platform="acl"), P("a", platform="arxiv"), P("b")]
    out = fallback_order(papers, [("a", "arxiv"), ("b", "arxiv")], 2)
    assert [(p.paper_id, p.platform) for p in out] == [("a", "arxiv"), ("b", "arxiv")]


# ---------- endpoint ----------
def _wire(monkeypatch, rerank, vec=None, kw=None):
    monkeypatch.setattr(search_api.vector_search_service, "search", vec or AsyncMock(return_value=[("v1", "arxiv")]))
    monkeypatch.setattr(search_api.keyword_search_service, "search", kw or AsyncMock(return_value=[("k1", "arxiv"), ("k2", "arxiv")]))
    monkeypatch.setattr(db_service, "get_papers_by_ids", AsyncMock(return_value=[P("v1", "V"), P("k2", "K2"), P("k1", "K1")]))
    monkeypatch.setattr(search_api.llm_service, "get_rerank", rerank)
    monkeypatch.setattr(search_api.search_log_service, "append_record", AsyncMock())


def _ids(r):
    return [x["paper_id"] for x in r.json()["results"]]


def test_empty_rerank_falls_back_to_retrieval_order(monkeypatch):
    _wire(monkeypatch, AsyncMock(return_value=[]))
    r = client.post("/api/search/", json={"query": "vision transformers"})
    assert r.status_code == 200
    assert _ids(r) == ["k1", "k2", "v1"]  # keyword hits first, in keyword order, then vector


def test_rerank_exception_falls_back(monkeypatch):
    _wire(monkeypatch, AsyncMock(side_effect=RuntimeError("no aws credentials")))
    r = client.post("/api/search/", json={"query": "vision transformers"})
    assert r.status_code == 200 and _ids(r) == ["k1", "k2", "v1"]


def test_valid_rerank_still_wins(monkeypatch):
    _wire(monkeypatch, AsyncMock(return_value=[2, 0]))  # papers list order: v1, k2, k1
    r = client.post("/api/search/", json={"query": "q"})
    assert _ids(r) == ["k1", "v1"]


def test_out_of_range_rerank_indices_ignored(monkeypatch):
    _wire(monkeypatch, AsyncMock(return_value=[99, -1, 1]))
    r = client.post("/api/search/", json={"query": "q"})
    assert r.status_code == 200 and _ids(r) == ["k2"]


def test_vector_failure_does_not_break_keyword_results(monkeypatch):
    _wire(monkeypatch, AsyncMock(return_value=[]), vec=AsyncMock(side_effect=RuntimeError("index missing")))
    r = client.post("/api/search/", json={"query": "q"})
    assert r.status_code == 200 and len(_ids(r)) == 3


def test_no_candidates_returns_empty(monkeypatch):
    _wire(monkeypatch, AsyncMock(return_value=[]), vec=AsyncMock(return_value=[]), kw=AsyncMock(return_value=[]))
    r = client.post("/api/search/", json={"query": "zzzz"})
    assert r.status_code == 200 and r.json()["count"] == 0

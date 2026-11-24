"""Test bootstrap: stub heavy/optional third-party modules so the app imports without GPUs, API keys or a DB."""
import importlib.abc
import importlib.machinery
import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 24)

_STUB_ROOTS = {"torch", "transformers", "faiss", "dashscope", "selenium", "webdriver_manager", "Bio", "pgvector", "google"}


class _StubFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    def find_spec(self, name, path, target=None):
        if name.split(".")[0] in _STUB_ROOTS:
            return importlib.machinery.ModuleSpec(name, self, is_package=True)
        return None

    def create_module(self, spec):
        m = MagicMock(name=spec.name)
        m.__path__ = []
        m.__spec__ = spec
        return m

    def exec_module(self, module):
        pass


sys.meta_path.insert(0, _StubFinder())

for _k, _v in {"EMBEDDING_BATCH_SIZE": "8", "EMBEDDING_DIMENSIONS": "8", "LLM_RERANK_TOPN": "5",
               "LLM_CONVERSATION_TEMPERATURE": "0.2", "LLM_API_KEY": "test", "LLM_API_URL": "http://localhost"}.items():
    os.environ.setdefault(_k, _v)


import asyncio as _asyncio


def import_app():
    """Import app.main; services start background tasks at import time (they normally run under uvicorn's loop)."""
    real = _asyncio.create_task

    def _safe_create_task(coro, *a, **kw):
        try:
            _asyncio.get_running_loop()
        except RuntimeError:
            coro.close()
            return MagicMock()
        return real(coro, *a, **kw)

    _asyncio.create_task = _safe_create_task
    try:
        import app.main as m
        return m
    finally:
        _asyncio.create_task = real

import json
import asyncio
from datetime import datetime
from pathlib import Path
import logging

LOG_PATH = (
    Path(__file__).resolve().parents[3] / "logs" / "search_history.jsonl"
)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)

_write_lock = asyncio.Lock()

async def append_record(query: str, results: list[dict], user_id: int | None = None):
    logger.info(f"Appending search record for user {user_id} with query: {query}")

    logger.info(
        f"Appending search record for user {user_id} with query: {query} "
        f"and results count: {len(results)} "
        f"to log file: {LOG_PATH} ")
     #   f"exists: {LOG_PATH.exists()}")
    """
    {
        "timestamp": "2025-06-03T13:05:22Z",
        "user_id": 123,
        "query": "...",
        "results": [...]   
    }
    """
    record = {
        "timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "user_id": user_id,
        "query": query,
        "results": results,
    }

    async with _write_lock:
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False, default=str) + "\n")


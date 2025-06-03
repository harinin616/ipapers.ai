import json
import asyncio
from datetime import datetime
from pathlib import Path

LOG_PATH = (
    Path(__file__).resolve().parents[3] / "logs" / "search_history.jsonl"
)
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)


_write_lock = asyncio.Lock()

async def append_record(query: str, results: list[dict], user_id: int | None = None):
    
    print(LOG_PATH)          # 打印出完整路径
    print(LOG_PATH.exists()) # 检查目录是否存在

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


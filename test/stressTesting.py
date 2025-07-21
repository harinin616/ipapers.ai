import asyncio
import random
import string
import time
import aiohttp

NUM_REQUESTS = 100
QUERY_LEN = 8
CONCURRENCY = 50
API_URL = "https://ipapers.ai/api/search/"

async def fetch(session: aiohttp.ClientSession, q: str):
    payload = {"query": q}
    start = time.perf_counter()
    try:
        async with session.post(API_URL, json=payload) as resp:
            elapsed = (time.perf_counter() - start) * 1000
            text = await resp.text()
            size = len(text)
            if resp.status == 200:
                print(f"[200] q={q}  size={size}  {elapsed:.1f}ms")
                return elapsed
            else:
                print(f"[{resp.status} FAILED] q={q}  size={size}  {elapsed:.1f}ms")
                return None
    except asyncio.TimeoutError:
        print(f"[TIMEOUT] q={q}")
    except Exception as e:
        print(f"[ERROR]   q={q} -> {e}")
    return None  # 超时或其他错误

async def main():
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout = aiohttp.ClientTimeout(total=240, sock_connect=20, sock_read=220)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [
            fetch(
                session,
                "".join(random.choices(string.ascii_lowercase + string.digits, k=QUERY_LEN))
            )
            for _ in range(NUM_REQUESTS)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=False)

    # 只有返回数值的才算成功
    times = [r for r in results if isinstance(r, (int, float))]
    completed = len(times)
    avg_ms = sum(times) / completed if completed else 0

    print(f"\nFinished {completed}/{NUM_REQUESTS} requests")
    print(f"Average response time: {avg_ms:.1f} ms")

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
import random, string, time
import aiohttp

NUM_REQUESTS = 100
QUERY_LEN    = 8
CONCURRENCY  = 50
API_URL      = "https://ipapers.ai/api/search/"

async def fetch(session: aiohttp.ClientSession, q: str):
    payload = {"query": q}  # 注意：Post 接口期望字段名是 query
    start = time.perf_counter()
    try:
        async with session.post(API_URL, json=payload) as resp:
            text = await resp.text()
            elapsed = (time.perf_counter() - start) * 1000
            size = len(text)
            print(f"[{resp.status}] q={q}  size={size}  {elapsed:.1f}ms")
    except asyncio.TimeoutError:
        print(f"[TIMEOUT] q={q}")
    except Exception as e:
        print(f"[ERROR]   q={q} -> {e}")

async def main():
    connector = aiohttp.TCPConnector(limit=CONCURRENCY)
    timeout   = aiohttp.ClientTimeout(total=60, sock_connect=5, sock_read=55)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        for _ in range(NUM_REQUESTS):
            q = ''.join(random.choices(string.ascii_lowercase + string.digits, k=QUERY_LEN))
            tasks.append(fetch(session, q))
        # return_exceptions=True 意味着即使有异常也不会抛出，只会收集到结果列表
        await asyncio.gather(*tasks, return_exceptions=True)

if __name__ == "__main__":
    asyncio.run(main())

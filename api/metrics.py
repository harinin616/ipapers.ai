from datetime import date, timedelta
from fastapi import APIRouter, Request
from sqlalchemy import select, func
from app.models.db_models import PageViewDaily
from app.db.database import get_async_db   # ← 跟 DBService 一样用生成器

router = APIRouter()


# ========= ① 埋点入口 /api/metrics/track =========
@router.post("/track")
async def track(req: Request):
    payload = await req.json()
    if payload.get("event") != "page_view":
        return {"status": "ignored"}

    today = date.today()

    async for db in get_async_db():              # 与 DBService 风格一致
        obj = await db.get(PageViewDaily, today)
        if obj:
            obj.cnt += 1
        else:
            db.add(PageViewDaily(day=today, cnt=1))
        await db.commit()
    return {"status": "ok"}


# ========= ② 统计接口 /api/metrics/site-metric =========
@router.get("/site-metric")
async def site_metric():
    today = date.today()
    async for db in get_async_db():
        # 最近 5 天
        rows = await db.execute(
            select(PageViewDaily.day, PageViewDaily.cnt)
            .where(PageViewDaily.day >= today - timedelta(days=4))
            .order_by(PageViewDaily.day)
        )
        mapping = {d: c for d, c in rows.all()}
        last5 = [mapping.get(today - timedelta(days=i), 0) for i in range(4, -1, -1)]

        # 总量
        total = await db.scalar(select(func.sum(PageViewDaily.cnt))) or 0

    return {"total": total, "last5": last5}

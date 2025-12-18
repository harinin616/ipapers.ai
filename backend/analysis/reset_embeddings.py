#!/usr/bin/env python3
import os
import asyncio
import logging
import json
from typing import List, Optional, Dict, Any, Tuple

import numpy as np
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.db_models import DBPaper
from app.services.llm_service import llm_service
from app.services.vector_search_service import vector_search_service

# ================= 配置区 =================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:yourpass@localhost:5432/dlmonitor",
)

# 每批从 DB 取多少篇论文
BATCH_SIZE = int(os.getenv("EMB_BATCH_SIZE", "2560"))

# 是否重置 FAISS 索引 & 进度文件（不动数据库）
#   第一次全量建索引：RESET_FAISS=1
#   之后断点续跑：    RESET_FAISS=0
RESET_FAISS = os.getenv("RESET_FAISS", "1") == "1"

# 本地进度文件：记录已经处理到哪个 (paper_id, platform)
PROGRESS_FILE = os.getenv(
    "EMB_PROGRESS_FILE",
    "embedding_rebuild_progress.json",
)

# 每处理多少篇汇报一次
PROGRESS_STEP = int(os.getenv("EMB_PROGRESS_STEP", "10000"))

# FAISS 训练最多采样多少个向量做 k-means
FAISS_TRAIN_MAX = int(os.getenv("FAISS_TRAIN_MAX", "655904"))

# 每累计多少个向量才把 FAISS 索引落盘一次
FAISS_SAVE_EVERY = int(os.getenv("FAISS_SAVE_EVERY", "50000"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("rebuild_from_db_embeddings")


# =============== 进度文件相关 =================

def load_progress() -> Optional[Dict[str, Any]]:
    """从本地 JSON 文件读取进度"""
    if not os.path.exists(PROGRESS_FILE):
        return None
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if "last_paper_id" in data and "last_platform" in data and "processed" in data:
            return data
        return None
    except Exception as e:
        logger.warning(f"Failed to load progress file {PROGRESS_FILE}: {e}")
        return None


def save_progress(last_paper_id: str, last_platform: str, processed: int) -> None:
    """把当前进度写到本地 JSON 文件"""
    data = {
        "last_paper_id": last_paper_id,
        "last_platform": last_platform,
        "processed": processed,
    }
    tmp_path = PROGRESS_FILE + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp_path, PROGRESS_FILE)
    logger.info(
        f"Saved progress: last=({last_paper_id}, {last_platform}), "
        f"processed={processed}"
    )


# =============== 嵌入计算 =================

async def embed_batch(texts: List[str]) -> Optional[np.ndarray]:
    """
    调 llm_service 生成一批文本的 embedding，并做 L2 归一化。
    返回 shape=(batch_size, dim) 的 float32 numpy 数组。
    """
    if not texts:
        return None

    logger.info(
        f"Starting embedding generation for {len(texts)} texts "
        f"in 1 batches (batch_size={len(texts)})"
    )
    embeddings = await llm_service.get_embeddings(texts=texts)
    if embeddings is None:
        return None

    arr = np.asarray(embeddings, dtype="float32")
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = arr / norms
    return arr.astype("float32")


# =============== 重置 FAISS（可选） =================

def reset_faiss_index_and_progress():
    """
    可选：删除现有 FAISS 索引文件，并让 vector_search_service 创建一个全新的 IVF+PQ 索引。
    同时删除本地进度文件，从头开始重建。
    （注意：完全不动数据库里的 embedding 列）
    """
    vs = vector_search_service

    # 删除旧索引文件（如果存在）
    for path in [vs.index_path, vs.paper_ids_path, vs.paper_platforms_path]:
        try:
            os.remove(path)
            logger.info(f"Removed old index file: {path}")
        except FileNotFoundError:
            pass

    # 删除进度文件
    try:
        os.remove(PROGRESS_FILE)
        logger.info(f"Removed old progress file: {PROGRESS_FILE}")
    except FileNotFoundError:
        pass

    # 在当前进程里重建空索引
    vs.create_new_index()
    logger.info(
        f"Created new empty FAISS index in memory "
        f"(key={vs.index_key}, dim={vs.embedding_dim})"
    )


# =============== 主流程 =================

async def rebuild_from_db_embeddings():
    """
    主流程：
      - 不清空 DB 的 embedding 列
      - 对每个 paper：
        * 如果 embedding 不为空：直接用（归一化）→ 加入 FAISS （去重）
        * 如果 embedding 为空：算 embedding → 写回 DB → 加入 FAISS
      - 用本地 progress 文件按 (paper_id, platform) 断点续传
      - FAISS 端用 (paper_id, platform) 去重，避免重复 add
    """
    # 1) 重置 FAISS & 进度文件（不动 DB）
    if RESET_FAISS:
        logger.info("RESET_FAISS=1: will reset FAISS index and local progress file")
        reset_faiss_index_and_progress()
    else:
        logger.info("RESET_FAISS=0: keep existing FAISS index and progress file")

    vs = vector_search_service  # 简写

    # 读取已有进度
    progress = load_progress()
    if progress:
        last_paper_id = progress["last_paper_id"]
        last_platform = progress["last_platform"]
        processed = int(progress["processed"])
        logger.info(
            f"Loaded progress from file: last=({last_paper_id}, {last_platform}), "
            f"processed={processed}"
        )
    else:
        last_paper_id = None
        last_platform = None
        processed = 0
        logger.info("No existing progress file, start from the beginning")

    # 预先拿到 nlist（IVF 聚类中心数）
    nlist = getattr(vs, "ivf_nlist", getattr(vs.index, "nlist", 0))
    if nlist:
        logger.info(f"FAISS IVF nlist={nlist}")
    else:
        logger.info("FAISS index appears non-IVF or nlist=0")

    # 现有索引里的 (paper_id, platform) 集合，用于去重
    existing_keys: set[Tuple[str, str]] = set()
    if vs.paper_ids and vs.paper_platforms:
        existing_keys = set(zip(vs.paper_ids, vs.paper_platforms))
    logger.info(f"Existing FAISS entries: {len(existing_keys)}")

    # 累积用于训练的向量（只有在 index 还没 train 时使用）
    pending_train_vecs: List[np.ndarray] = []
    pending_train_ids: List[str] = []
    pending_train_platforms: List[str] = []

    faiss_total_added = len(existing_keys)
    faiss_last_saved = faiss_total_added

    # 3) 创建异步引擎和 Session 工厂
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with AsyncSessionLocal() as session:  # type: AsyncSession
        # 4) 统计总论文数（用于进度展示）
        result_total = await session.execute(
            select(func.count()).select_from(DBPaper)
        )
        total_count = result_total.scalar_one()
        logger.info(f"Total papers in DB: {total_count}")

        last_reported = processed

        # 5) 主循环：按 (paper_id, platform) 顺序扫表
        while True:
            stmt = select(DBPaper)

            # 有进度，从上次 (paper_id, platform) 之后继续
            if last_paper_id is not None and last_platform is not None:
                stmt = stmt.where(
                    or_(
                        DBPaper.paper_id > last_paper_id,
                        and_(
                            DBPaper.paper_id == last_paper_id,
                            DBPaper.platform > last_platform,
                        ),
                    )
                )

            stmt = (
                stmt.order_by(DBPaper.paper_id, DBPaper.platform)
                .limit(BATCH_SIZE)
            )

            result = await session.execute(stmt)
            papers_batch: List[DBPaper] = result.scalars().all()

            if not papers_batch:
                logger.info("No more papers to process, break.")
                break

            # 提前记下这一批最后一条（防止异常时没有进度）
            batch_last_paper_id = papers_batch[-1].paper_id
            batch_last_platform = papers_batch[-1].platform

            logger.info(
                f"Fetched batch: size={len(papers_batch)} "
                f"(processed={processed}/{total_count})"
            )

            # 本批需要算 embedding 的
            texts_to_embed: List[str] = []
            papers_to_embed: List[DBPaper] = []

            # 本批要加到 FAISS 的向量和 id
            faiss_vecs: List[np.ndarray] = []
            faiss_ids: List[str] = []
            faiss_platforms: List[str] = []

            # 1) 先看 DB 是否已有 embedding
            for p in papers_batch:
                key = (p.paper_id, p.platform)

                # 已经在 FAISS 里了，跳过
                if key in existing_keys:
                    processed += 1
                    continue

                # 文本是否为空
                text = f"{p.title} {p.abstract or ''}".strip()
                if not text:
                    logger.warning(
                        f"Paper {p.paper_id} ({p.platform}) has empty text, skip."
                    )
                    processed += 1
                    continue

                if p.embedding is not None:
                    # DB 已有 embedding：直接用
                    emb_arr = np.asarray(p.embedding, dtype="float32")
                    if emb_arr.shape[0] != vs.embedding_dim:
                        logger.warning(
                            f"Paper {p.paper_id} ({p.platform}) embedding dim mismatch: "
                            f"got {emb_arr.shape[0]}, expect {vs.embedding_dim}, skip."
                        )
                        processed += 1
                        continue

                    # 重新归一化一下，保证和新索引一致
                    norm = np.linalg.norm(emb_arr)
                    if norm == 0:
                        logger.warning(
                            f"Paper {p.paper_id} ({p.platform}) embedding norm=0, skip."
                        )
                        processed += 1
                        continue
                    emb_arr = (emb_arr / norm).astype("float32")

                    faiss_vecs.append(emb_arr)
                    faiss_ids.append(p.paper_id)
                    faiss_platforms.append(p.platform)
                    existing_keys.add(key)
                    processed += 1
                else:
                    # embedding 为空：延后统一算
                    texts_to_embed.append(text)
                    papers_to_embed.append(p)

            # 2) 对 embedding 为空的做 batch 计算
            if texts_to_embed:
                try:
                    emb_array_new = await embed_batch(texts_to_embed)
                except Exception as e:
                    logger.error(
                        f"Embedding batch (for NULL) failed: {e}", exc_info=True
                    )
                    # 这一批没算成功的，下次还能再来
                    emb_array_new = None

                if (
                    emb_array_new is not None
                    and emb_array_new.shape[0] == len(papers_to_embed)
                ):
                    # 写回 DB + 收集到 FAISS 列表
                    for p, vec in zip(papers_to_embed, emb_array_new):
                        key = (p.paper_id, p.platform)
                        # 写回 DB（pgvector 支持 list）
                        p.embedding = vec.tolist()

                        faiss_vecs.append(vec)
                        faiss_ids.append(p.paper_id)
                        faiss_platforms.append(p.platform)
                        existing_keys.add(key)
                        processed += 0  # 上面已经在第一轮处理时加过 processed
                else:
                    if emb_array_new is None:
                        logger.error("Embedding batch returned None, skip this group.")
                    else:
                        logger.error(
                            f"Embedding batch shape mismatch for new embeddings: "
                            f"got {emb_array_new.shape}, expected {len(papers_to_embed)}"
                        )
                    # 这些 paper 的 embedding 仍然是 None，下次跑脚本还会再尝试

            # 3) 写回 DB（只针对刚刚补上的 embedding）
            #    注意：即便 DB commit 失败，也不会影响已经在 FAISS 的那部分
            try:
                await session.commit()
            except Exception as e:
                logger.error(f"DB commit failed: {e}", exc_info=True)
                await session.rollback()
                # 这批新算的 embedding 会丢掉（DB 里仍然是 NULL），
                # 但我们已经加进 FAISS 了。以后如果你很在意一致性，可以再写个“纯从 DB 重建 FAISS”的脚本。
                pass

            # 更新 last_xxx 用于进度文件
            last_paper_id = batch_last_paper_id
            last_platform = batch_last_platform

            # 4) 更新 FAISS 索引
            try:
                if faiss_vecs:
                    X = np.vstack(faiss_vecs).astype("float32")

                    # 还没训练的 IVF 索引：先累积足够多向量，再统一训练 + add
                    if hasattr(vs.index, "is_trained") and not vs.index.is_trained and nlist:
                        # 把这一批先放到 pending 里
                        pending_train_vecs.append(X)
                        pending_train_ids.extend(faiss_ids)
                        pending_train_platforms.extend(faiss_platforms)

                        total_pending = sum(arr.shape[0] for arr in pending_train_vecs)
                        if total_pending < nlist*40:
                            logger.info(
                                f"FAISS index not trained yet: have {total_pending} "
                                f"training vectors, need at least nlist={nlist*40}. "
                                f"Postpone training to later batches."
                            )
                        else:
                            # 够 nlist 了，开始训练
                            train_x = np.vstack(pending_train_vecs)
                            if train_x.shape[0] > FAISS_TRAIN_MAX:
                                idx = np.random.choice(
                                    train_x.shape[0], FAISS_TRAIN_MAX, replace=False
                                )
                                train_x = train_x[idx]

                            logger.info(
                                f"Training FAISS index on {train_x.shape[0]} vectors "
                                f"(key={vs.index_key}, nlist={nlist})"
                            )
                            vs.index.train(train_x)
                            logger.info("FAISS index training finished")

                            # 把所有累积的向量一次性加进去
                            add_x = np.vstack(pending_train_vecs).astype("float32")
                            vs.index.add(add_x)
                            vs.paper_ids.extend(pending_train_ids)
                            vs.paper_platforms.extend(pending_train_platforms)

                            added_now = add_x.shape[0]
                            faiss_total_added += added_now

                            # 清空 pending
                            pending_train_vecs.clear()
                            pending_train_ids.clear()
                            pending_train_platforms.clear()

                            if faiss_total_added - faiss_last_saved >= FAISS_SAVE_EVERY:
                                vs.save_index()
                                faiss_last_saved = faiss_total_added
                                logger.info(
                                    f"Saved FAISS index after initial training; "
                                    f"total_added={faiss_total_added}"
                                )

                    else:
                        # 索引已经训练好（或者不是 IVF 索引），直接 add
                        vs.index.add(X)
                        vs.paper_ids.extend(faiss_ids)
                        vs.paper_platforms.extend(faiss_platforms)

                        added_now = X.shape[0]
                        faiss_total_added += added_now

                        if faiss_total_added - faiss_last_saved >= FAISS_SAVE_EVERY:
                            vs.save_index()
                            faiss_last_saved = faiss_total_added
                            logger.info(
                                f"Saved FAISS index incrementally; "
                                f"total_added={faiss_total_added}"
                            )

            except Exception as e:
                logger.error(f"Updating FAISS index failed: {e}", exc_info=True)
                # 不影响 DB，最坏就是索引里暂时少一部分向量

            # 5) 进度输出 & 进度文件
            if processed - last_reported >= PROGRESS_STEP or processed >= total_count:
                last_reported = processed
                frac = processed / total_count if total_count > 0 else 0.0
                logger.info(
                    f"Progress: {processed}/{total_count} ({frac:.2%})"
                )
                print(f"{processed}/{total_count}", flush=True)

            save_progress(last_paper_id, last_platform, processed)

    await engine.dispose()

    # 结束前做一次最终 save，避免少量未刷盘的增量
    try:
        vs.save_index()
        logger.info("Final FAISS index save completed.")
    except Exception as e:
        logger.error(f"Final FAISS save_index failed: {e}", exc_info=True)

    logger.info("Rebuild FAISS index from DB embeddings finished.")


async def main():
    await rebuild_from_db_embeddings()


if __name__ == "__main__":
    asyncio.run(main())

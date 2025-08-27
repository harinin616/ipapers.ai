# app/services/idea_service.py
from __future__ import annotations
import json, time, re, asyncio
from typing import Any, Dict, List, Optional

# ====== Resolve your LLM Service ======
def _resolve_llm_service():
    try:
        from app.services.llm_service import llm_service  # preferred singleton
        return llm_service
    except Exception:
        try:
            from app.services.llm_service import LLMService
            return LLMService()
        except Exception as e:
            raise RuntimeError(
                "LLM service not available. Ensure app.services.llm_service exposes "
                "`llm_service` or `LLMService` with method "
                "`get_conversation_completion_non_streaming(messages, model)`."
            ) from e


# ====== Helpers ======
def _extract_json(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    text2 = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    try:
        return json.loads(text2)
    except Exception:
        pass
    s, e = text.find("{"), text.rfind("}")
    if s != -1 and e != -1 and e > s:
        snippet = text[s:e+1]
        try:
            return json.loads(snippet)
        except Exception:
            return {}
    return {}

def _clamp_int(x: Any, lo: int = 0, hi: int = 100) -> int:
    try:
        v = int(round(float(x)))
    except Exception:
        v = lo
    return max(lo, min(hi, v))


# ====== Service ======
class IdeaService:
    """
    Multi-stage ideation with real-time streaming:
    - seed: quick list (id,title,one-liner)
    - refine: per-idea expansion + metrics
    - score/kpis: finalize KPIs
    All LLM calls使用你的 get_conversation_completion_non_streaming。
    """
    def __init__(self, llm, model: Optional[str] = None):
        self.llm = llm
        self.model = model
        self._idea_store: Dict[str, Dict[str, Any]] = {}  # id -> idea

    # ---------- LLM calls ----------
    async def _llm_seed(self, topic: str, rounds: int, reviewers: int, active_personas: List[str]) -> List[Dict[str, Any]]:
        system = (
            "You generate a fast list of research idea seeds. "
            "Return STRICT JSON only: {\"ideas\":[{\"title\":\"\",\"summary\":\"\"}, ... exactly 8 items]}"
        )
        user = (
            f"topic: {topic}\n"
            f"L (critique rounds): {rounds}\n"
            f"N (reviewers): {reviewers}\n"
            f"personas: {', '.join(active_personas) if active_personas else '—'}\n"
            "Return exactly 8 seeds. Keep summary one sentence."
        )
        raw = await self.llm.get_conversation_completion_non_streaming(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=self.model
        )
        data = _extract_json(raw or "")
        ideas = data.get("ideas") or []
        return ideas if isinstance(ideas, list) else []

    async def _llm_refine(self, seed: Dict[str, Any], topic: str, rounds: int, reviewers: int, active_personas: List[str]) -> Dict[str, Any]:
        system = (
            "You refine ONE research idea. Return STRICT JSON only with fields:\n"
            "{\"title\":\"\",\"summary\":\"\",\"novelty\":0-100,\"feasibility\":0-100,\"clarity\":0-100,"
            "\"score\":0-100,\"tags\":[\"Novel\",\"Feasible\",\"Low-Compute\",\"Data-Free\",\"Eval-Ready\"]}"
        )
        user = (
            f"seed_title: {seed.get('title','')}\n"
            f"seed_summary: {seed.get('summary','')}\n"
            f"context_topic: {topic}\n"
            f"L: {rounds} | N: {reviewers}\n"
            f"personas: {', '.join(active_personas) if active_personas else '—'}\n"
            "Refine the idea, produce concise summary and metrics."
        )
        raw = await self.llm.get_conversation_completion_non_streaming(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=self.model
        )
        data = _extract_json(raw or "")
        return data if isinstance(data, dict) else {}

    async def _llm_kpis(self, ideas: List[Dict[str, Any]]) -> Dict[str, int]:
        # 可选：让 LLM 评一个 kpi；同时我们也有可解释兜底
        system = (
            "Compute KPIs for list of ideas. Return STRICT JSON: {\"nonDup\":0-100,\"pAt10\":0-100}."
        )
        user = "ideas:\n" + json.dumps([{"title":i["title"],"score":i["score"]} for i in ideas], ensure_ascii=False)
        raw = await self.llm.get_conversation_completion_non_streaming(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            model=self.model
        )
        data = _extract_json(raw or "")
        if not isinstance(data, dict):
            data = {}
        return data

    # ---------- Non-streaming (still used by fallback) ----------
    async def generate_ideas(self, payload) -> Dict[str, Any]:
        p = payload.dict() if hasattr(payload, "dict") else dict(payload)
        topic = p.get("topic","")
        rounds = int(p.get("rounds",3))
        reviewers = int(p.get("reviewers",3))
        active = [x.get("name") for x in (p.get("personas") or []) if x.get("on")]

        seeds = await self._llm_seed(topic, rounds, reviewers, active)
        now_ms = int(time.time()*1000)
        ideas: List[Dict[str,Any]] = []
        # refine sequentially
        for i, seed in enumerate(seeds[:8]):
            rid = f"{now_ms}-{i}"
            ref = await self._llm_refine(seed, topic, rounds, reviewers, active)
            idea = {
                "id": rid,
                "title": (ref.get("title") or seed.get("title") or f"Idea {i+1}").strip(),
                "summary": (ref.get("summary") or seed.get("summary") or "").strip() or f"{topic} · {rounds} rounds × {reviewers} reviewers",
                "novelty": _clamp_int(ref.get("novelty")),
                "feasibility": _clamp_int(ref.get("feasibility")),
                "clarity": _clamp_int(ref.get("clarity")),
                "score": _clamp_int(ref.get("score") if ref.get("score") is not None else 0),
                "tags": list(map(str, (ref.get("tags") or [])[:3])),
            }
            # derive score if 0
            if idea["score"] == 0:
                idea["score"] = _clamp_int(idea["novelty"]*0.4 + idea["feasibility"]*0.4 + idea["clarity"]*0.2)
            ideas.append(idea)
            self._idea_store[rid] = idea

        # KPIs
        k = await self._llm_kpis(ideas)
        if not isinstance(k, dict): k = {}
        if "nonDup" not in k:
            titles = [x["title"].strip().lower() for x in ideas]
            k["nonDup"] = _clamp_int(int(round(len(set(titles))/max(1,len(titles))*100)))
        if "pAt10" not in k:
            top10 = sorted(ideas, key=lambda x:x["score"], reverse=True)[:10]
            hits = sum(1 for x in top10 if x["score"] >= 70)
            k["pAt10"] = _clamp_int(int(round(hits/max(1,len(top10))*100)))
        return {"ideas": ideas, "kpis": k}

    # ---------- Streaming (SSE) ----------
    async def generate_ideas_stream(self, payload):
        """
        Yields:
         - {"event":"phase","stage":"start/config/llm/...", "message":"...", "progress":int}
         - {"event":"seed","ideas":[{id,title,summary,metrics=0...}]}
         - {"event":"idea_update","idea":{... refined ...}}
         - {"event":"kpis","kpis":{...}}
         - {"event":"complete","ideas":[...], "kpis":{...}}
        """
        p = payload.dict() if hasattr(payload, "dict") else dict(payload)
        topic = p.get("topic","")
        rounds = int(p.get("rounds",3))
        reviewers = int(p.get("reviewers",3))
        active = [x.get("name") for x in (p.get("personas") or []) if x.get("on")]

        # 0) start
        yield {"event":"phase","stage":"start","message":"Starting pipeline","progress":5}
        await asyncio.sleep(0)

        # 1) seed
        yield {"event":"phase","stage":"seed","message":"Generating seed ideas…","progress":15}
        seeds = await self._llm_seed(topic, rounds, reviewers, active)
        now_ms = int(time.time()*1000)
        seed_items: List[Dict[str,Any]] = []
        for i, s in enumerate(seeds[:8]):
            rid = f"{now_ms}-{i}"
            item = {
                "id": rid,
                "title": (s.get("title") or f"Idea {i+1}").strip(),
                "summary": (s.get("summary") or "").strip(),
                "novelty": 0, "feasibility": 0, "clarity": 0, "score": 0,
                "tags": []
            }
            seed_items.append(item)
            self._idea_store[rid] = item
        yield {"event":"seed","ideas": seed_items}
        yield {"event":"phase","stage":"seed","message":"Seeds ready. Refining…","progress":30}
        await asyncio.sleep(0)

        # 2) refine & stream one by one (or concurrently)
        tasks = [asyncio.create_task(self._llm_refine(s, topic, rounds, reviewers, active)) for s in seeds[:8]]
        progress = 30
        refined: List[Dict[str,Any]] = []
        for idx, task in enumerate(asyncio.as_completed(tasks), start=1):
            ref = await task
            rid = seed_items[len(refined)]["id"]  # keep simple ordering
            # 合并
            idea = self._idea_store[rid]
            idea.update({
                "title": (ref.get("title") or idea["title"]).strip(),
                "summary": (ref.get("summary") or idea["summary"] or f"{topic} · {rounds} rounds × {reviewers} reviewers").strip(),
                "novelty": _clamp_int(ref.get("novelty")),
                "feasibility": _clamp_int(ref.get("feasibility")),
                "clarity": _clamp_int(ref.get("clarity")),
                "score": _clamp_int(ref.get("score") if ref.get("score") is not None else 0),
                "tags": list(map(str, (ref.get("tags") or [])[:3])),
            })
            if idea["score"] == 0:
                idea["score"] = _clamp_int(idea["novelty"]*0.4 + idea["feasibility"]*0.4 + idea["clarity"]*0.2)

            refined.append(idea)
            yield {"event":"idea_update","idea": idea}
            progress = min(90, 30 + int(idx/8*55))
            yield {"event":"phase","stage":"refine","message":f"Refined {idx}/8","progress":progress}
            await asyncio.sleep(0)

        # 3) KPIs
        yield {"event":"phase","stage":"kpis","message":"Computing KPIs…","progress":92}
        k = await self._llm_kpis(refined)
        if not isinstance(k, dict): k = {}
        if "nonDup" not in k:
            titles = [x["title"].strip().lower() for x in refined]
            k["nonDup"] = _clamp_int(int(round(len(set(titles))/max(1,len(titles))*100)))
        if "pAt10" not in k:
            top10 = sorted(refined, key=lambda x:x["score"], reverse=True)[:10]
            hits = sum(1 for x in top10 if x["score"] >= 70)
            k["pAt10"] = _clamp_int(int(round(hits/max(1,len(top10))*100)))
        yield {"event":"kpis","kpis": k}
        await asyncio.sleep(0)

        # 4) complete
        refined_sorted = sorted(refined, key=lambda x:x["score"], reverse=True)
        yield {"event":"complete","ideas": refined_sorted, "kpis": k}

    async def expand_proposal(self, idea_id: str) -> str:
        idea = self._idea_store.get(idea_id)
        if not idea:
            return (
                f"# Proposal for {idea_id}\n\n"
                "**Summary**: TBD\n\n"
                "**Method**:\n- Retrieval + multi-agent critique (N reviewers, L rounds)\n"
                "- Persona-driven feasibility checks\n- Dedup + preference-ranking\n\n"
                "**Evaluation**:\n- Datasets, metrics, ablations\n\n"
                "**Risks & Mitigations**:\n- Data availability, compute budget\n\n"
                "**Expected Contributions**:\n- Novel method and reproducible pipeline\n"
            )
        sys = "You write clear, reproducible research proposals. Return pure Markdown (no fences)."
        user = (
            "Expand the following idea into a short proposal with Sections: "
            "Summary, Method, Evaluation, Risks & Mitigations, Expected Contributions.\n\n"
            f"Title: {idea['title']}\n"
            f"Summary seed: {idea['summary']}\n"
            f"Metrics: Novelty {idea['novelty']}, Feasibility {idea['feasibility']}, "
            f"Clarity {idea['clarity']}, Score {idea['score']}\n"
            f"Tags: {', '.join(idea.get('tags', []))}\n"
        )
        md = await self.llm.get_conversation_completion_non_streaming(
            messages=[{"role":"system","content":sys},{"role":"user","content":user}],
            model=self.model
        )
        return (md or "").strip() or f"# Proposal for {idea['title']}\n\n{idea['summary']}\n"


# ====== singleton ======
_idea_service_singleton: Optional[IdeaService] = None
def get_idea_service(model: Optional[str] = None) -> IdeaService:
    global _idea_service_singleton
    if _idea_service_singleton is None:
        _idea_service_singleton = IdeaService(_resolve_llm_service(), model=model)
    return _idea_service_singleton

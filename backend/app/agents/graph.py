"""LangGraph multi-agent pipeline: Planner -> Researcher -> Verifier -> Summarizer -> Writer"""
import asyncio, logging
from typing import TypedDict
from langgraph.graph import StateGraph, END
from tavily import TavilyClient
from ..config import settings
from .llm import generate, parse_json

log = logging.getLogger("agents")

class State(TypedDict, total=False):
    topic: str
    depth: int
    questions: list
    sources: list   # [{id,title,url,content}]
    facts: list     # [{claim,confidence,source_ids}]
    summary: str
    report: dict

def _src_block(sources, limit=700):
    return "\n\n".join(f"[{s['id']}] {s['title']} ({s['url']})\n{s['content'][:limit]}" for s in sources)

async def planner(s: State):
    p = (f"You are a research planner. Topic: '{s['topic']}'.\n"
         f"Create {s['depth']} distinct, specific web-search questions covering key aspects "
         'of this topic. Return JSON: {"questions": ["..."]}')
    qs = parse_json(await generate(p, True)).get("questions", [])[: s["depth"]]
    log.info(f"Planner produced {len(qs)} questions")
    return {"questions": qs or [s["topic"]]}

async def researcher(s: State):
    if not settings.TAVILY_API_KEY:
        raise RuntimeError("TAVILY_API_KEY missing in .env")
    tv = TavilyClient(api_key=settings.TAVILY_API_KEY)

    async def one(q):
        try:
            r = await asyncio.to_thread(tv.search, q, max_results=4, search_depth="advanced")
            return r.get("results", [])
        except Exception as e:
            log.warning(f"Search failed for '{q}': {e}")
            return []

    results = await asyncio.gather(*[one(q) for q in s["questions"]])
    seen, sources = set(), []
    for batch in results:
        for r in batch:
            if r["url"] in seen:
                continue
            seen.add(r["url"])
            sources.append({"id": len(sources) + 1, "title": r.get("title", "Untitled"),
                            "url": r["url"], "content": r.get("content", "")})
    if not sources:
        raise RuntimeError("No search results found. Check Tavily key / topic.")
    return {"sources": sources}

async def verifier(s: State):
    p = (f"You are a fact-checker. Topic: {s['topic']}.\nSources:\n{_src_block(s['sources'])}\n\n"
         "Extract up to 15 key factual claims. Keep ONLY claims supported by at least one source. "
         "confidence = 'high' if 2+ sources agree, 'medium' if 1 reliable source, 'low' if uncertain/conflicting. "
         'Return JSON: {"facts":[{"claim":"...","confidence":"high|medium|low","source_ids":[1,2]}]}')
    facts = parse_json(await generate(p, True)).get("facts", [])
    facts = [f for f in facts if f.get("confidence") != "low" and f.get("source_ids")]
    return {"facts": facts}

async def summarizer(s: State):
    fl = "\n".join(f"- {f['claim']} [{','.join(map(str, f['source_ids']))}] ({f['confidence']})" for f in s["facts"])
    p = (f"Summarize these verified facts about '{s['topic']}' into a concise, organized brief "
         f"(max 350 words). Keep [n] citation markers.\n\n{fl}")
    return {"summary": await generate(p)}

async def writer(s: State):
    p = (f"You are a professional report writer. Topic: '{s['topic']}'.\n"
         f"Verified summary:\n{s['summary']}\n\nWrite a formal research report. Use [n] citation markers "
         "matching source ids. No markdown symbols (no ** or #). Plain paragraphs separated by blank lines.\n"
         'Return JSON: {"title":"...","executive_summary":"...",'
         '"sections":[{"heading":"...","content":"..."}],"conclusion":"..."} with 4-6 sections.')
    rep = parse_json(await generate(p, True))
    rep["sources"] = [{"id": x["id"], "title": x["title"], "url": x["url"]} for x in s["sources"]]
    rep["fact_check"] = s["facts"]
    return {"report": rep}

def build_graph():
    g = StateGraph(State)
    for name, fn in [("planner", planner), ("researcher", researcher), ("verifier", verifier),
                     ("summarizer", summarizer), ("writer", writer)]:
        g.add_node(name, fn)
    g.set_entry_point("planner")
    g.add_edge("planner", "researcher")
    g.add_edge("researcher", "verifier")
    g.add_edge("verifier", "summarizer")
    g.add_edge("summarizer", "writer")
    g.add_edge("writer", END)
    return g.compile()

graph = build_graph()

from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException

from app.embedding import EmbeddingService
from app.chroma import ChromaService

services = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    services["embedder"] = EmbeddingService()
    services["chroma"] = ChromaService()
    yield
    services.clear()


app = FastAPI(
    title="ProfileDB AI",
    description="ProfileDB AI Troubleshooting POC",
    version="1.0",
    lifespan=lifespan
)


def _items(res):
    items = [
        {"id": i, "log": d, "metadata": m}
        for i, d, m in zip(res["ids"], res["documents"], res["metadatas"])
    ]
    items.sort(key=lambda x: x["metadata"]["seq"])
    return items


@app.get("/")
def home():
    return {"application": "ProfileDB AI", "status": "running"}


@app.get("/health")
def health():
    return {"status": "UP", "documents": services["chroma"].count_documents()}


@app.get("/search")
def search(
    query: str = Query(..., min_length=3),
    top_k: int = Query(3, ge=1, le=20),
    level: str | None = Query(None, description="Optional: ERROR, WARN, INFO")
):
    where = {"level": level.upper()} if level else None
    vector = services["embedder"].create_query_embedding(query)
    res = services["chroma"].search(vector, top_k=top_k, where=where)

    return {
        "query": query,
        "results": [
            {"id": i, "log": d, "distance": dist, "metadata": m}
            for i, d, dist, m in zip(
                res["ids"][0], res["documents"][0],
                res["distances"][0], res["metadatas"][0]
            )
        ],
    }


@app.get("/errors")
def errors(limit: int = Query(50, ge=1, le=500)):
    res = services["chroma"].get_where({"level": "ERROR"}, limit)
    items = _items(res)
    return {"count": len(items), "results": items}


@app.get("/context")
def context(
    doc_id: str,
    seconds: int = Query(10, ge=1, le=300),
    max_lines: int = Query(15, ge=1, le=200)
):
    chroma = services["chroma"]
    base = chroma.get_by_id(doc_id)

    if not base["ids"]:
        raise HTTPException(status_code=404, detail="Document not found")

    meta = base["metadatas"][0]
    if not meta.get("thread"):
        raise HTTPException(status_code=400, detail="This line has no thread to correlate on")

    where = {"$and": [
        {"thread": meta["thread"]},
        {"ts_ms": {"$gte": meta["ts_ms"] - seconds * 1000}},
        {"seq": {"$lte": meta["seq"]}},
    ]}
    res = chroma.get_where(where, limit=1000)
    items = _items(res)[-max_lines:]
    return {"doc_id": doc_id, "thread": meta["thread"], "count": len(items), "lines": items}


@app.get("/record/{record_id}")
def record(
    record_id: int,
    neighbors: int = Query(2, ge=0, le=20, description="Lines kept before/after each match on the same thread"),
    level: str | None = Query(None, description="Optional: only return lines of this level, e.g. ERROR"),
    max_lines: int = Query(100, ge=1, le=1000, description="Return at most this many (the most recent)")
):
    chroma = services["chroma"]

    direct = _items(chroma.get_where({"record_id": record_id}, limit=5000))
    if not direct:
        raise HTTPException(status_code=404, detail="No lines found for this record_id")

    direct_ids = {x["id"] for x in direct}

    by_thread = {}
    for x in direct:
        t = x["metadata"].get("thread", "")
        if t:
            by_thread.setdefault(t, []).append(x)

    keep = {x["id"]: x for x in direct}

    for thread, matches in by_thread.items():
        start = min(x["metadata"]["ts_ms"] for x in matches) - 2000
        end = max(x["metadata"]["ts_ms"] for x in matches) + 2000
        where = {"$and": [
            {"thread": thread},
            {"ts_ms": {"$gte": start}},
            {"ts_ms": {"$lte": end}},
        ]}
        lines = _items(chroma.get_where(where, limit=5000))
        hits = [i for i, x in enumerate(lines) if x["id"] in direct_ids]
        for h in hits:
            for j in range(max(0, h - neighbors), min(len(lines), h + neighbors + 1)):
                keep[lines[j]["id"]] = lines[j]

    result = sorted(keep.values(), key=lambda x: x["metadata"]["seq"])
    for x in result:
        x["match"] = x["id"] in direct_ids

    if level:
        result = [x for x in result if x["metadata"].get("level") == level.upper()]

    levels = {}
    for x in direct:
        lv = x["metadata"].get("level", "UNKNOWN")
        levels[lv] = levels.get(lv, 0) + 1

    return {
        "record_id": record_id,
        "matching_lines": len(direct),
        "matching_by_level": levels,
        "threads": sorted(by_thread.keys()),
        "total_lines": len(result),
        "returned": min(len(result), max_lines),
        "lines": result[-max_lines:],
    }
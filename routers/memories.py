"""Ghost-Writer Backend — Memories Router.

POST   /memories/store  — Store messages as vector memories.
POST   /memories/search — Semantic search over stored memories.
GET    /memories/count  — Get count of stored memories.
DELETE /memories/clear  — Clear all stored memories.
"""
from fastapi import APIRouter, HTTPException

from models.schemas import StoreMemoriesRequest, MemorySearchRequest, MemorySearchResponse
from services.vector_store import get_vector_store

router = APIRouter()


@router.post("/store")
async def store_memories(request: StoreMemoriesRequest):
    """Store messages as searchable vector memories."""
    store = get_vector_store()
    stored_count = store.store_memories(request.messages)
    return {"stored_count": stored_count, "mode": store.mode}


@router.post("/search", response_model=MemorySearchResponse)
async def search_memories(request: MemorySearchRequest):
    """Search stored memories by semantic similarity."""
    if not request.query.strip():
        raise HTTPException(status_code=422, detail="Search query cannot be empty.")

    store = get_vector_store()
    results = store.search(request.query, request.top_k)

    return MemorySearchResponse(results=results, query_used=request.query)


@router.get("/count")
async def memory_count():
    """Get the number of stored memories."""
    store = get_vector_store()
    return {"count": store.count, "mode": store.mode}


@router.delete("/clear")
async def clear_memories():
    """Clear all stored memories."""
    store = get_vector_store()
    store.clear()
    return {"cleared": True, "mode": store.mode}

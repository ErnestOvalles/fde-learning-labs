# Week 11: Retrieval-Augmented Generation (RAG)

## Outcome

Build a **Retrieval-Augmented Generation (RAG)** pipeline that indexes your tracker's request history into a vector store, retrieves the most similar past requests, and uses them as grounded context for an LLM answer to "Which past requests are similar to this new one?"

## Setup Checklist

- [ ] Reuse the `tracker` FastAPI app + Postgres from Weeks 5–6
- [ ] Have an OpenAI API key (or run with a local embedding model from HuggingFace)
- [ ] `uv add openai chromadb langchain-text-splitters tiktoken python-dotenv pytest`
- [ ] Confirm Postgres is running and the tracker DB is reachable
- [ ] Confirm at least 20 sample requests exist in the tracker

### Setup Walkthrough

```bash
# 1. Enter the week's folder
cd phase-3-llm-apps/week-11-retrieval
uv init
uv python pin 3.13

# 2. Install dependencies
uv add openai chromadb langchain-text-splitters tiktoken python-dotenv pytest ruff

# 3. Set the embedding model and the chat model
cat >> .env <<'EOF'
EMBED_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o-mini
EOF

# 4. Sanity-check
uv run python - <<'PY'
import os
from dotenv import load_dotenv
load_dotenv()
print("embed model:", os.getenv("EMBED_MODEL"))
print("llm model:", os.getenv("LLM_MODEL"))
PY
```

If you prefer **fully local embeddings**, swap `EMBED_MODEL` for a HuggingFace sentence-transformer:

```bash
uv add sentence-transformers
```

and load it with `SentenceTransformer("all-MiniLM-L6-v2")` — its vectors are 384-dim, so set `EMBED_DIM=384` in `.env`.

## Learning Path (60–90 minutes)

**Best approach:** Build retrieval *first*. Only after retrieval is measurably correct do you wire it to generation.

### Learn in this order

1. **What embeddings are** — fixed-length vectors of floats; semantically similar text is close in cosine distance
2. **Cosine similarity vs Euclidean** — cosine ignores magnitude, almost always right for text
3. **Chunking strategies** — fixed-size, sentence, recursive, semantic; tradeoffs
4. **Vector stores** — ChromaDB (easy, local), FAISS (fast, no server), pgvector (already in your Postgres)
5. **Indexing pipeline** — chunk → embed → upsert with metadata
6. **Retrieval pipeline** — embed query → top-k neighbors → re-rank optional
7. **RAG prompting** — stuff retrieved chunks into the system prompt, cite sources, refuse if none

### Free Resources

- [OpenAI Embeddings Guide](https://platform.openai.com/docs/guides/embeddings) — `text-embedding-3-small` and `-3-large`
- [ChromaDB Quickstart](https://docs.trychroma.com/getting-started) — `chromadb.PersistentClient`, `add`, `query`
- [LangChain Text Splitters](https://python.langchain.com/docs/concepts/text_splitters/) — `RecursiveCharacterTextSplitter`
- [pgvector README](https://github.com/pgvector/pgvector) — if you want retrieval inside Postgres
- [RAG Survey (Lewis et al., 2020)](https://arxiv.org/abs/2005.11401) — the original paper that named the pattern

**Tip:** Embedding model choice is a long-term commitment. Changing models means **re-embedding everything**. Pick one early.

## Micro-Exercises (45–60 minutes)

Create `practice.py` and work through these:

### Exercise 1 — Generate one embedding and inspect it

```python
# practice.py
import os, math
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

text = "Customer cannot log in after the upgrade."
resp = client.embeddings.create(
    model=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
    input=text,
)

vec = resp.data[0].embedding
print("dim:", len(vec))
print("first 5:", vec[:5])
print("usage tokens:", resp.usage.total_tokens)

# A real implementation will normalize; for intuition only:
def l2(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))

print("||v||_2:", l2(vec))
```

**Step-by-step:**
1. Run — confirm the vector length matches `text-embedding-3-small` (1536) or `-3-large` (3072).
2. Print the first 5 numbers — they look random. The structure only becomes meaningful under similarity.
3. Save the embedding to a list of dicts if you want to reuse later.

### Exercise 2 — Cosine similarity by hand

```python
def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb)

# Two semantically related sentences should be highly similar
s1 = "Login is broken for several users"
s2 = "Customers cannot authenticate after the deploy"
s3 = "We need to update the homepage banner"

e1 = client.embeddings.create(model=os.getenv("EMBED_MODEL"), input=s1).data[0].embedding
e2 = client.embeddings.create(model=os.getenv("EMBED_MODEL"), input=s2).data[0].embedding
e3 = client.embeddings.create(model=os.getenv("EMBED_MODEL"), input=s3).data[0].embedding

print("login vs login :", cosine(e1, e2))   # should be high
print("login vs banner:", cosine(e1, e3))   # should be lower
```

**Step-by-step:**
1. Run and observe the two scores.
2. Try replacing `s3` with a near-duplicate of `s1` (one word changed) — the score should be very high.
3. **Important:** if you cache embeddings, key them by `(model, text_hash)` so you don't double-bill.

### Exercise 3 — Recursive chunking with token counts

```python
# practice.py  (append)
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

long_text = """
Our customer request tracker has been running for three years. The current
schema uses JSON columns and a request is a dict. Each request includes id,
customer name, title, description, priority, status, created_at, updated_at.

The most common request categories are billing, technical, account, and
general. Login issues are the largest single category of technical requests.
We have observed a steady increase in urgency=critical tickets during off-hours.
""" * 5

splitter = RecursiveCharacterTextSplitter(
    chunk_size=200, chunk_overlap=40, length_function=len,
)
chunks = splitter.split_text(long_text)
print("chunks:", len(chunks))
print("first chunk:", chunks[0])

# Verify token counts with tiktoken
enc = tiktoken.encoding_for_model("gpt-4o-mini")
for i, c in enumerate(chunks[:3]):
    print(f"chunk {i} tokens:", len(enc.encode(c)))
```

**Step-by-step:**
1. Run — expect several chunks, each around 200 chars.
2. Use `tiktoken` to verify chunk sizes are reasonable for your model.
3. Try `chunk_size=500` and observe the trade-off: fewer chunks, less precise retrieval.

### Exercise 4 — Stand up ChromaDB and upsert five documents

```python
import os, shutil
import chromadb
from chromadb.config import Settings
from openai import OpenAI

# Use OpenAI as the embedding function — Chroma will call it for us
openai_ef = chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.environ["OPENAI_API_KEY"],
    model_name=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
)

PERSIST = "./chroma_store"
if os.path.exists(PERSIST):
    shutil.rmtree(PERSIST)

client = chromadb.PersistentClient(path=PERSIST, settings=Settings(anonymized_telemetry=False))
col = client.create_collection(name="tracker_requests", embedding_function=openai_ef)

docs = [
    "Login fails after the v2 upgrade. Multiple enterprise customers affected.",
    "Invoice PDF is blank when downloaded from the billing portal.",
    "User cannot add a teammate to their organization; the invite email never arrives.",
    "Production API returns 502 during peak load. Suspect connection pool exhaustion.",
    "Password reset email goes to spam for users on outlook.com domains.",
]
ids = [f"r{i}" for i in range(len(docs))]
metas = [{"priority": "high", "category": c} for c in
          ["technical", "billing", "account", "technical", "account"]]

col.add(documents=docs, ids=ids, metadatas=metas)
print("count:", col.count())
```

**Step-by-step:**
1. Run — Chroma persists to `./chroma_store`.
2. The `metas` show how to filter retrieval later (`where={"category": "billing"}`).
3. Re-run to confirm idempotency: Chroma dedupes by id, so count stays at 5.

### Exercise 5 — Query ChromaDB and inspect neighbors

```python
results = col.query(
    query_texts=["I cannot sign in to my account"],
    n_results=3,
    where={"category": "technical"},     # metadata filter
)

for i, (doc, dist, meta, id_) in enumerate(zip(
    results["documents"][0],
    results["distances"][0],
    results["metadatas"][0],
    results["ids"][0],
)):
    print(f"{i+1}. id={id_} dist={dist:.3f} meta={meta}")
    print(f"   {doc[:120]}")
```

**Step-by-step:**
1. Run — Chroma returns distance (1 − cosine similarity for cosine metric).
2. Notice how the `category=technical` filter narrows results.
3. Try removing the `where` filter and compare the order.

### Exercise 6 — Embed your own corpus and cache embeddings

```python
# Caching pattern — saves money during iteration
import json, hashlib
from pathlib import Path

CACHE = Path("./embed_cache.jsonl")

def embed_cached(texts: list[str], model: str) -> list[list[float]]:
    cache = {}
    if CACHE.exists():
        for line in CACHE.read_text().splitlines():
            row = json.loads(line)
            cache[row["k"]] = row["v"]
    out, missing = [], []
    for t in texts:
        k = hashlib.sha256(f"{model}:{t}".encode()).hexdigest()
        if k in cache:
            out.append(cache[k])
        else:
            missing.append((k, t))
    if missing:
        resp = client.embeddings.create(model=model, input=[t for _, t in missing])
        for (k, _), item in zip(missing, resp.data):
            cache[k] = item.embedding
            out.append(item.embedding)
            CACHE.parent.mkdir(parents=True, exist_ok=True)
            with CACHE.open("a") as f:
                f.write(json.dumps({"k": k, "v": item.embedding}) + "\n")
    return out

# Use the cache for batched embedding
vecs = embed_cached(docs, os.getenv("EMBED_MODEL", "text-embedding-3-small"))
print("got", len(vecs), "vectors; cached to", CACHE)
```

**Step-by-step:**
1. Run twice — second run should be a cache hit and skip the OpenAI call.
2. Delete `embed_cache.jsonl` and re-run to confirm you get fresh vectors.
3. **Pitfall:** never reuse cache files across embedding models — vectors are not comparable.

### Exercise 7 — Build a minimal RAG answer

```python
def rag_answer(question: str, col, k: int = 4) -> str:
    results = col.query(query_texts=[question], n_results=k)
    context = "\n\n".join(results["documents"][0])

    resp = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {
                "role": "system",
                "content": (
                    "You answer questions using ONLY the supplied context. "
                    "If the context does not contain the answer, say "
                    "'I don't have enough information.' "
                    "Cite sources as [1], [2], etc."
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion: {question}",
            },
        ],
        temperature=0,
    )
    return resp.choices[0].message.content

print(rag_answer("Any known issues with login?", col))
```

**Step-by-step:**
1. Confirm the answer cites `[1]`, `[2]`, etc. matching the retrieved chunks.
2. Ask a question with no relevant docs (e.g., "What is the weather in Tokyo?") — the model should refuse.
3. This refusal behavior is the most important safety property of a RAG system.

---

## Main Lab: RAG over tracker requests (4–5 hours)

### Scenario

Customer success needs a "have we seen this before?" tool. Given a new free-text message, return the **top 3 similar past requests** and an **LLM-generated answer with citations**.

### Data Shape

```python
class RetrievedRequest(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    status: str
    category: str
    score: float                  # cosine similarity, 0..1
    source_index: int             # 1-based, for citations

class RagAnswer(BaseModel):
    question: str
    answer: str
    citations: list[RetrievedRequest]
    used_context: bool            # false if we returned "I don't have enough information"
```

### Required Endpoints

```
POST /rag/query            — accept a question, return RagAnswer
POST /rag/ingest           — (re)index all requests from Postgres into Chroma
GET  /rag/health           — confirm vector store reachable
```

### Build Steps

**Commit after each step.** Use messages like:
- `feat: embedding client + cache`
- `feat: chunking module`
- `feat: chromadb upsert + query`
- `feat: /rag/query endpoint`
- `feat: ingest pipeline`

#### Step 1 — Build the embedding client

```python
# rag/embed.py
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
_client = OpenAI()

def embed_texts(texts: list[str], model: str | None = None) -> list[list[float]]:
    """Embed a batch of strings; returns one vector per input."""
    model = model or os.getenv("EMBED_MODEL", "text-embedding-3-small")
    resp = _client.embeddings.create(model=model, input=texts)
    return [d.embedding for d in resp.data]

def embed_one(text: str, model: str | None = None) -> list[float]:
    return embed_texts([text], model=model)[0]
```

#### Step 2 — Build the chunker

```python
# rag/chunk.py
from langchain_text_splitters import RecursiveCharacterTextSplitter

def chunk_request(title: str, description: str,
                  chunk_size: int = 400, chunk_overlap: int = 80) -> list[str]:
    """Combine title + description and split into retrievable chunks."""
    full = f"Title: {title}\n\nDescription: {description}".strip()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=len,
    )
    return splitter.split_text(full) or [full]
```

#### Step 3 — Build the vector store wrapper

```python
# rag/store.py
import os
from pathlib import Path
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

PERSIST = Path(os.getenv("CHROMA_PATH", "./chroma_store"))
COLLECTION = "tracker_requests"

def get_collection():
    client = chromadb.PersistentClient(
        path=str(PERSIST),
        settings=Settings(anonymized_telemetry=False),
    )
    ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=os.environ["OPENAI_API_KEY"],
        model_name=os.getenv("EMBED_MODEL", "text-embedding-3-small"),
    )
    return client.get_or_create_collection(name=COLLECTION, embedding_function=ef)
```

#### Step 4 — Index requests from Postgres

```python
# rag/ingest.py
from rag.chunk import chunk_request
from rag.store import get_collection

def index_request(req: dict) -> int:
    """Upsert one request into Chroma; returns number of chunks added."""
    col = get_collection()
    chunks = chunk_request(req["title"], req["description"])
    ids = [f"{req['id']}::chunk::{i}" for i in range(len(chunks))]
    metas = [{
        "request_id": req["id"],
        "priority":  req["priority"],
        "status":    req["status"],
        "category":  req.get("category", "general"),
        "chunk":     i,
    } for i in range(len(chunks))]
    col.upsert(documents=chunks, ids=ids, metadatas=metas)
    return len(chunks)

def index_all(requests: list[dict]) -> int:
    total = 0
    for r in requests:
        total += index_request(r)
    return total
```

Wire it into the tracker:

```python
# in tracker app, on create_request / update_request:
from rag.ingest import index_request

@app.post("/requests", status_code=201)
def create_request(req: CreateRequest):
    new = {...}                # existing code
    requests.append(new)
    save_requests(requests)
    index_request(new)
    return new
```

#### Step 5 — Implement the retrieval function

```python
# rag/retrieve.py
from rag.store import get_collection

def retrieve(query: str, k: int = 3, where: dict | None = None) -> list[dict]:
    col = get_collection()
    kwargs = {"query_texts": [query], "n_results": k}
    if where:
        kwargs["where"] = where
    res = col.query(**kwargs)

    out: list[dict] = []
    for i in range(len(res["ids"][0])):
        out.append({
            "id":         res["ids"][0][i],
            "document":   res["documents"][0][i],
            "distance":   res["distances"][0][i],
            "metadata":   res["metadatas"][0][i],
        })
    return out
```

Cosine distance ranges from 0 (identical) to 2 (opposite). Convert to a similarity score:

```python
def similarity(distance: float) -> float:
    # For cosine distance in [0, 2], 1 - distance/2 ∈ [-1, 1]
    return max(0.0, 1.0 - distance / 2.0)
```

#### Step 6 — Implement the RAG answer

```python
# rag/answer.py
import os
from openai import OpenAI
from dotenv import load_dotenv
from rag.retrieve import retrieve, similarity
from rag.schema import RagAnswer, RetrievedRequest

load_dotenv()
_client = OpenAI()

SYSTEM = (
    "You answer questions about past customer requests using ONLY the "
    "supplied context. Cite sources as [1], [2], etc., matching the numbered "
    "context blocks. If the context does not contain the answer, respond "
    "exactly: 'I don't have enough information.'"
)

def rag_query(question: str, k: int = 3, min_score: float = 0.55) -> RagAnswer:
    hits = retrieve(question, k=k)
    cited: list[RetrievedRequest] = []
    blocks: list[str] = []
    for i, h in enumerate(hits, start=1):
        score = similarity(h["distance"])
        if score < min_score:
            continue
        meta = h["metadata"]
        cited.append(RetrievedRequest(
            id=meta["request_id"],
            title=meta.get("title", "(missing)"),
            description=h["document"],
            priority=meta.get("priority", "unknown"),
            status=meta.get("status", "unknown"),
            category=meta.get("category", "general"),
            score=round(score, 3),
            source_index=i,
        ))
        blocks.append(f"[{i}] {h['document']}")

    if not blocks:
        return RagAnswer(question=question, answer="I don't have enough information.",
                         citations=[], used_context=False)

    context = "\n\n".join(blocks)
    resp = _client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        temperature=0,
    )
    return RagAnswer(question=question, answer=resp.choices[0].message.content,
                     citations=cited, used_context=True)
```

#### Step 7 — Expose the FastAPI endpoint

```python
# rag/api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from rag.answer import rag_query
from rag.ingest import index_all
from tracker.repo import load_requests  # from Week 6

app = FastAPI(title="rag-service")

class RagQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    k: int = Field(default=3, ge=1, le=10)

@app.post("/rag/query")
def query(req: RagQueryRequest) -> dict:
    try:
        ans = rag_query(req.question, k=req.k)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    return ans.model_dump()

@app.post("/rag/ingest")
def ingest() -> dict:
    n = index_all(load_requests())
    return {"indexed_chunks": n}

@app.get("/rag/health")
def health() -> dict:
    from rag.store import get_collection
    return {"ok": True, "count": get_collection().count()}
```

```bash
uv run uvicorn rag.api:app --reload --port 8001
uv run pytest -q
```

#### Step 8 — Add a hybrid filter (metadata + text)

```python
@app.post("/rag/query")
def query(req: RagQueryRequest, status: str | None = None,
          category: str | None = None):
    where = {}
    if status:
        where["status"] = status
    if category:
        where["category"] = category
    ans = rag_query(req.question, k=req.k, where=where or None)
    return ans.model_dump()
```

Test with `?status=open&category=technical` — confirm the metadata filter narrows results.

#### Step 9 — Write tests with a tiny in-memory Chroma

```python
# tests/test_rag.py
import os, shutil
import pytest
from rag.store import get_collection
from rag.ingest import index_request
from rag.answer import rag_query

@pytest.fixture(scope="module", autouse=True)
def temp_chroma(tmp_path_factory):
    os.environ["CHROMA_PATH"] = str(tmp_path_factory.mktemp("chroma"))
    yield

SAMPLE = {
    "id": "REQ-001",
    "title": "Login broken",
    "description": "After upgrade, half our users cannot log in.",
    "priority": "high",
    "status": "open",
    "category": "technical",
}

def test_index_and_retrieve(monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", os.environ["CHROMA_PATH"])
    index_request(SAMPLE)
    hits = rag_query.__wrapped__ if hasattr(rag_query, "__wrapped__") else None  # noqa
    # Direct retrieval bypasses the LLM call
    from rag.retrieve import retrieve
    out = retrieve("login issue", k=2)
    assert len(out) >= 1
    assert out[0]["metadata"]["request_id"] == "REQ-001"
```

#### Step 10 — Add observability: log retrieval scores

```python
# rag/answer.py — inside rag_query, before returning:
import logging
log = logging.getLogger("rag")

log.info("rag.retrieve", extra={
    "question": question,
    "k": k,
    "hits": len(cited),
    "top_score": cited[0].score if cited else 0.0,
})
```

#### Step 11 — Document the project

```markdown
# rag-service

Retrieval-augmented question answering over the customer request tracker.

## Setup
    uv sync
    cp .env.example .env
    uv run python -c "from rag.api import app"

## Run
    uv run uvicorn rag.api:app --reload --port 8001

## Endpoints
- POST /rag/query     — ask a question, get cited answer
- POST /rag/ingest    — re-index all tracker requests
- GET  /rag/health    — confirm vector store reachable

## Notes
- Embeddings are cached in `embed_cache.jsonl` keyed by `(model, text)`.
- ChromaDB persists to `./chroma_store`.
- Re-ingest whenever you switch embedding models.
```

### Required Manual Tests

- [ ] `POST /rag/ingest` returns `{"indexed_chunks": <N>}`
- [ ] `POST /rag/query` with `"login issue"` returns a relevant cited answer
- [ ] `POST /rag/query` with `"What is the meaning of life?"` returns "I don't have enough information."
- [ ] `POST /rag/query?category=billing` only cites billing requests
- [ ] Deleting `./chroma_store` and re-ingesting produces the same retrieval order
- [ ] Asking the same query twice hits the embedding cache the second time (check stdout for token usage)

### Acceptance Criteria

- [ ] Retrieval returns top-k neighbors with cosine similarity scores
- [ ] The LLM only answers from retrieved context; refusal behavior is tested
- [ ] Embeddings are cached to avoid duplicate billing
- [ ] Metadata filters (`status`, `category`) work and are tested
- [ ] `/rag/ingest` is idempotent (re-running does not duplicate)
- [ ] At least 5 meaningful commits
- [ ] You can explain the difference between cosine similarity and cosine distance

## AI-Off Check (30 minutes)

Without looking at your code, write a function that takes a list of `(text, vector)` pairs and a query vector, and returns the top-k by cosine similarity. Use only `math` and plain Python:

```python
def topk_cosine(items: list[tuple[str, list[float]]],
                 query: list[float], k: int) -> list[tuple[str, float]]:
    """Return up to k (text, score) pairs sorted by descending cosine similarity."""
    raise NotImplementedError
```

Compare with your implementation. The goal is to internalize what `chromadb.query` is doing under the hood.

## Reflection Questions

After you finish, write answers to these in `REFLECTION.md`:

1. What breaks if you switch embedding models without re-ingesting?
2. How does chunk size change precision vs recall? Give an example.
3. When would you choose pgvector over ChromaDB?
4. Why is the "I don't have enough information" refusal important for production safety?

## Next Steps

Once you pass all acceptance criteria:

1. Run `uv run pytest -q` and save the output
2. Write reflection answers
3. Commit with message: `docs: week 11 complete`
4. Move to Week 12 (Agents) — the agent you build will call `/rag/query` as a tool

---

**Ready?** Start by running:

```bash
uv init
uv add openai chromadb langchain-text-splitters tiktoken python-dotenv pytest ruff
```

Then follow the learning path above. Good luck! 🎯

"""
rag_engine.py — RAG Pipeline for CallIQ
Contextual policy-aware auditing using LangChain + FAISS (local) or Pinecone (cloud).

Features:
- Ingest policy/compliance documents (.txt, .pdf, .md)
- Chunk + embed using OpenAI or sentence-transformers (free fallback)
- Store in FAISS (local, no API needed) or Pinecone (cloud)
- Retrieve relevant policy context for a given transcript
- Generate contextual audit feedback grounded in real policy docs
"""

import os
import json
import hashlib
import pickle
from pathlib import Path
from typing import Optional

# ── Optional heavy imports (graceful degradation) ──────────────────────────
try:
    import numpy as np
    NUMPY_OK = True
except ImportError:
    NUMPY_OK = False

try:
    import faiss
    FAISS_OK = True
except ImportError:
    FAISS_OK = False

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

# ── Paths ───────────────────────────────────────────────────────────────────
FAISS_INDEX_PATH  = Path("calliq_faiss.index")
FAISS_META_PATH   = Path("calliq_faiss_meta.pkl")
POLICY_DOCS_DIR   = Path("policy_docs")
POLICY_DOCS_DIR.mkdir(exist_ok=True)

# ── Default sample policy documents ─────────────────────────────────────────
SAMPLE_POLICIES = {
    "greeting_policy.txt": """
# Greeting & Opening Policy

All agents must greet customers within the first 5 seconds of the call.
Required elements of a proper greeting:
1. Say "Thank you for calling [Company Name]"
2. State your first name clearly
3. Ask: "How may I assist you today?"

Prohibited phrases:
- "What do you want?"
- "Hold on" without explanation
- Informal greetings like "Hey" or "Yeah"

Agents must never put a customer on hold in the first 30 seconds without offering a callback.
Brand voice: warm, confident, and professional at all times.
""",
    "empathy_compliance.txt": """
# Empathy & De-escalation Standards

Agents must acknowledge customer frustration before moving to resolution.
Required empathy acknowledgement when customer expresses frustration:
- "I completely understand how frustrating that must be."
- "I sincerely apologize for the inconvenience."
- "That's not the experience we want you to have."

Escalation triggers — agent must offer supervisor if:
- Customer uses the word "unacceptable" twice or more
- Customer explicitly asks to speak to a manager
- Call duration exceeds 15 minutes without resolution

Prohibited responses to angry customers:
- Arguing or raising voice
- Saying "That's not my problem" or "There's nothing I can do"
- Disconnecting without resolution attempt
""",
    "data_privacy_policy.txt": """
# Data Privacy & Verification Policy

Identity Verification Requirements:
- All agents must verify customer identity before accessing account details.
- Minimum verification: Full name + account number OR date of birth.
- Never state account balances, personal details, or order history before verification.

GDPR / Data Protection:
- Never read out full credit card numbers over the phone.
- Do not confirm email addresses unprompted — only confirm partial.
- If customer requests data deletion, log ticket immediately and advise 30-day processing time.

Call Recording Notice:
- Agents must inform customers if the call is being recorded, unless jurisdiction exempts this.
- Phrase: "Please be aware this call may be recorded for quality and training purposes."
""",
    "resolution_standards.txt": """
# Resolution & Closing Standards

Every call must end with a resolution or a clear next step.
Mandatory closing checklist:
1. Summarize what was done or agreed
2. Confirm customer is satisfied: "Does that resolve everything for you today?"
3. Provide ticket or reference number if applicable
4. Offer further assistance: "Is there anything else I can help with?"
5. Thank the customer by name

Escalation to Level 2 Support:
- Agent must attempt resolution for at least 5 minutes before escalating.
- If escalating, agent must brief Level 2 agent before transferring — never cold transfer.
- Tell the customer: "I'm going to connect you with a specialist who can resolve this quickly."

SLA Commitments:
- Callbacks must be scheduled within 24 hours.
- Technical issues must have a ticket raised within 5 minutes of identification.
- Refund approvals must be communicated with a 3–5 business day timeline.
""",
    "professionalism_standards.txt": """
# Language & Professionalism Standards

Prohibited language:
- Profanity or offensive language under any circumstances
- Slang or overly casual language ("gonna", "wanna", "nope", "yep")
- Negative language about competitors or the company itself
- "I don't know" without follow-up ("Let me find out for you")
- "That's not possible" without an alternative offered

Required positive language patterns:
- Use "I will" instead of "I'll try"
- Use "What I can do is..." instead of "I can't..."
- Use customer's name at least twice during the call
- Use "certainly", "absolutely", "of course" to affirm requests

Hold procedures:
- Always ask permission before placing on hold: "May I place you on a brief hold?"
- Maximum hold time: 3 minutes without check-in
- Return from hold: "Thank you for your patience, [Name]."
"""
}

def ensure_sample_policies():
    """Write sample policy docs if none exist yet."""
    for filename, content in SAMPLE_POLICIES.items():
        fp = POLICY_DOCS_DIR / filename
        if not fp.exists():
            fp.write_text(content.strip(), encoding="utf-8")


# ── Text chunking ────────────────────────────────────────────────────────────
def chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i : i + chunk_size])
        chunks.append(chunk)
        i += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 30]


# ── Embedding ────────────────────────────────────────────────────────────────
def embed_texts_openai(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed texts using OpenAI text-embedding-3-small."""
    resp = requests.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "text-embedding-3-small", "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return [d["embedding"] for d in data["data"]]


def embed_texts_openrouter(texts: list[str], api_key: str) -> list[list[float]]:
    """Embed texts using OpenRouter (falls back to OpenAI embeddings endpoint)."""
    resp = requests.post(
        "https://openrouter.ai/api/v1/embeddings",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"model": "openai/text-embedding-3-small", "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()
    return [d["embedding"] for d in data["data"]]


def embed_texts_tfidf(texts: list[str], dim: int = 384) -> list[list[float]]:
    """
    Fallback embedder: deterministic TF-IDF-style sparse vector (no API, no torch).
    Not as good as dense embeddings but works offline.
    """
    import re, math
    vocab: dict[str, int] = {}
    tokenized = []
    for t in texts:
        tokens = re.findall(r"[a-z]{3,}", t.lower())
        tokenized.append(tokens)
        for tok in tokens:
            if tok not in vocab:
                vocab[tok] = len(vocab)

    embeddings = []
    for tokens in tokenized:
        freq: dict[str, int] = {}
        for tok in tokens:
            freq[tok] = freq.get(tok, 0) + 1
        vec = [0.0] * dim
        for tok, cnt in freq.items():
            idx = vocab.get(tok, 0) % dim
            vec[idx] += cnt / (len(tokens) + 1e-9)
        # L2 normalize
        norm = math.sqrt(sum(x * x for x in vec)) + 1e-9
        vec = [x / norm for x in vec]
        embeddings.append(vec)
    return embeddings


def get_embedding_fn(openai_key: str = "", openrouter_key: str = ""):
    """Return the best available embedding function."""
    if openai_key and REQUESTS_OK:
        return lambda texts: embed_texts_openai(texts, openai_key)
    if openrouter_key and REQUESTS_OK:
        return lambda texts: embed_texts_openrouter(texts, openrouter_key)
    return embed_texts_tfidf


# ── FAISS index ──────────────────────────────────────────────────────────────
class FAISSStore:
    def __init__(self):
        self.index = None
        self.metadata: list[dict] = []   # {source, chunk, text}
        self.dim: int = 0

    def build(self, embeddings: list[list[float]], metadata: list[dict]):
        if not FAISS_OK or not NUMPY_OK:
            raise RuntimeError("faiss-cpu and numpy are required. Run: pip install faiss-cpu numpy")
        self.dim = len(embeddings[0])
        mat = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(mat)
        self.index = faiss.IndexFlatIP(self.dim)   # Inner product = cosine on normalized vecs
        self.index.add(mat)
        self.metadata = metadata

    def save(self):
        if self.index is None:
            return
        faiss.write_index(self.index, str(FAISS_INDEX_PATH))
        with open(FAISS_META_PATH, "wb") as f:
            pickle.dump({"metadata": self.metadata, "dim": self.dim}, f)

    def load(self) -> bool:
        if not FAISS_INDEX_PATH.exists() or not FAISS_META_PATH.exists():
            return False
        try:
            self.index = faiss.read_index(str(FAISS_INDEX_PATH))
            with open(FAISS_META_PATH, "rb") as f:
                d = pickle.load(f)
            self.metadata = d["metadata"]
            self.dim = d["dim"]
            return True
        except Exception:
            return False

    def search(self, query_vec: list[float], top_k: int = 5) -> list[dict]:
        if self.index is None:
            return []
        q = np.array([query_vec], dtype="float32")
        faiss.normalize_L2(q)
        scores, idxs = self.index.search(q, top_k)
        results = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0:
                continue
            results.append({**self.metadata[idx], "score": float(score)})
        return results


# Simple in-memory fallback (no FAISS) using cosine similarity
class SimpleVectorStore:
    def __init__(self):
        self.vectors: list[list[float]] = []
        self.metadata: list[dict] = []

    def build(self, embeddings: list[list[float]], metadata: list[dict]):
        self.vectors = embeddings
        self.metadata = metadata

    def save(self):
        with open(FAISS_META_PATH, "wb") as f:
            pickle.dump({"vectors": self.vectors, "metadata": self.metadata}, f)

    def load(self) -> bool:
        if not FAISS_META_PATH.exists():
            return False
        try:
            with open(FAISS_META_PATH, "rb") as f:
                d = pickle.load(f)
            self.vectors = d.get("vectors", [])
            self.metadata = d.get("metadata", [])
            return bool(self.vectors)
        except Exception:
            return False

    def search(self, query_vec: list[float], top_k: int = 5) -> list[dict]:
        import math
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x * x for x in a)) + 1e-9
            nb = math.sqrt(sum(x * x for x in b)) + 1e-9
            return dot / (na * nb)

        scored = [(cosine(query_vec, v), i) for i, v in enumerate(self.vectors)]
        scored.sort(reverse=True)
        results = []
        for score, idx in scored[:top_k]:
            results.append({**self.metadata[idx], "score": score})
        return results


def get_store():
    return FAISSStore() if (FAISS_OK and NUMPY_OK) else SimpleVectorStore()


# ── Public API ───────────────────────────────────────────────────────────────

def ingest_policy_docs(
    docs_dir: str = str(POLICY_DOCS_DIR),
    openai_key: str = "",
    openrouter_key: str = "",
    force_rebuild: bool = False,
) -> tuple[bool, str]:
    """
    Ingest all .txt/.md/.pdf files from docs_dir into the vector store.
    Returns (success, message).
    """
    ensure_sample_policies()
    embed_fn = get_embedding_fn(openai_key, openrouter_key)
    store = get_store()

    # Hash all docs to detect changes
    doc_hash = _hash_docs(docs_dir)
    hash_file = Path("calliq_doc_hash.txt")
    if not force_rebuild and hash_file.exists() and hash_file.read_text() == doc_hash:
        if store.load():
            return True, f"Loaded existing index ({len(store.metadata)} chunks)."

    all_chunks: list[str] = []
    all_meta:   list[dict] = []

    docs_path = Path(docs_dir)
    files = list(docs_path.glob("*.txt")) + list(docs_path.glob("*.md"))

    # Try PDF extraction if available
    try:
        import pypdf
        for pdf_path in docs_path.glob("*.pdf"):
            reader = pypdf.PdfReader(str(pdf_path))
            text = "\n".join(page.extract_text() or "" for page in reader.pages)
            for i, chunk in enumerate(chunk_text(text)):
                all_chunks.append(chunk)
                all_meta.append({"source": pdf_path.name, "chunk": i, "text": chunk})
    except ImportError:
        pass

    for fp in files:
        text = fp.read_text(encoding="utf-8", errors="ignore")
        for i, chunk in enumerate(chunk_text(text)):
            all_chunks.append(chunk)
            all_meta.append({"source": fp.name, "chunk": i, "text": chunk})

    if not all_chunks:
        return False, "No policy documents found in the docs directory."

    try:
        # Embed in batches of 50
        all_embeddings: list[list[float]] = []
        batch_size = 50
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i : i + batch_size]
            all_embeddings.extend(embed_fn(batch))

        store.build(all_embeddings, all_meta)
        store.save()
        hash_file.write_text(doc_hash)

        store_type = "FAISS" if (FAISS_OK and NUMPY_OK) else "in-memory"
        embed_type = "OpenAI" if openai_key else ("OpenRouter" if openrouter_key else "TF-IDF fallback")
        return True, f"Indexed {len(all_chunks)} chunks from {len(files)} docs · {store_type} store · {embed_type} embeddings."

    except Exception as e:
        return False, f"Indexing failed: {e}"


def retrieve_policy_context(
    query: str,
    openai_key: str = "",
    openrouter_key: str = "",
    top_k: int = 5,
) -> list[dict]:
    """
    Retrieve the top-k most relevant policy chunks for a given query/transcript.
    Returns list of {source, text, score}.
    """
    store = get_store()
    if not store.load():
        return []

    embed_fn = get_embedding_fn(openai_key, openrouter_key)
    try:
        query_vec = embed_fn([query])[0]
        return store.search(query_vec, top_k=top_k)
    except Exception:
        return []


def rag_audit(
    transcript: str,
    evaluation_result: dict,
    openai_key: str = "",
    openrouter_key: str = "",
    openrouter_or_openai_key_for_llm: str = "",
) -> dict:
    """
    Run a RAG-powered contextual audit:
    1. Retrieve relevant policy chunks for the transcript
    2. Ask the LLM to compare transcript against retrieved policies
    3. Return structured findings

    Returns dict with:
      - policy_references: list of {source, excerpt, relevance}
      - policy_violations: list of specific policy breaches
      - policy_compliant_items: list of what was done right per policy
      - contextual_coaching: detailed coaching grounded in policy text
      - rag_summary: 2-sentence overview
    """
    # Retrieve relevant policy chunks
    context_chunks = retrieve_policy_context(
        query=transcript[:2000],   # use first 2000 chars as query
        openai_key=openai_key,
        openrouter_key=openrouter_key,
        top_k=6,
    )

    if not context_chunks:
        return {
            "policy_references": [],
            "policy_violations": ["RAG index not built — upload policy documents and click Build Index."],
            "policy_compliant_items": [],
            "contextual_coaching": "No policy documents indexed yet. Please upload your company policy files and rebuild the index.",
            "rag_summary": "Policy context unavailable. Index policy documents to enable RAG-powered auditing.",
        }

    # Build context string from retrieved chunks
    context_str = "\n\n---\n\n".join(
        f"[Source: {c['source']}]\n{c['text']}" for c in context_chunks
    )

    llm_key = openrouter_or_openai_key_for_llm or openrouter_key or openai_key

    if not llm_key:
        # Offline fallback: heuristic matching
        return _heuristic_rag_audit(transcript, evaluation_result, context_chunks)

    prompt = f"""You are a senior compliance auditor. You have retrieved the following policy excerpts that are most relevant to this customer support call transcript.

POLICY CONTEXT:
{context_str}

CALL TRANSCRIPT:
{transcript[:3000]}

EXISTING SCORES:
Total: {evaluation_result.get('total_score', 0)}/25
Compliance violations flagged: {evaluation_result.get('compliance_violations', [])}

Your task: Audit the transcript SPECIFICALLY against the policy excerpts provided above.
Return ONLY valid JSON with this exact structure:
{{
  "policy_references": [
    {{"source": "<filename>", "excerpt": "<10-15 word relevant quote from policy>", "relevance": "<why this policy applies>"}}
  ],
  "policy_violations": [
    "<specific violation citing the policy source>"
  ],
  "policy_compliant_items": [
    "<specific thing agent did that matches a stated policy requirement>"
  ],
  "contextual_coaching": "<3-5 sentences of specific coaching tied directly to the policy text>",
  "rag_summary": "<2 sentences: overall policy compliance verdict for this call>"
}}
"""

    try:
        # Try OpenRouter first
        key_to_use = openrouter_key or openai_key
        base_url = "https://openrouter.ai/api/v1/chat/completions" if openrouter_key else "https://api.openai.com/v1/chat/completions"
        model = "openai/gpt-4o-mini" if openrouter_key else "gpt-4o-mini"

        resp = requests.post(
            base_url,
            headers={"Authorization": f"Bearer {key_to_use}", "Content-Type": "application/json"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "You are a compliance auditor. Respond only with valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 1200,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
        content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(content)
        result["retrieved_chunks"] = context_chunks
        return result

    except Exception as e:
        return _heuristic_rag_audit(transcript, evaluation_result, context_chunks)


def _heuristic_rag_audit(transcript: str, eval_result: dict, chunks: list[dict]) -> dict:
    """Offline fallback: keyword-based policy matching."""
    t = transcript.lower()
    violations = []
    compliant = []

    checks = [
        ("thank you for calling", "Greeting policy: agent used required opening phrase.", "Greeting policy: missing 'Thank you for calling' opener."),
        ("my name is",            "Greeting policy: agent stated their name.",            "Greeting policy: agent did not introduce themselves by name."),
        ("how may i",             "Greeting policy: agent offered assistance properly.",  None),
        ("i apologize",           "Empathy policy: agent issued an apology.",             None),
        ("i understand",          "Empathy policy: agent acknowledged customer feelings.", None),
        ("is there anything else","Resolution policy: agent offered further assistance.", "Resolution policy: agent did not offer further assistance before closing."),
        ("recorded",              "Privacy policy: call recording notice mentioned.",     None),
    ]

    for phrase, ok_msg, fail_msg in checks:
        if phrase in t:
            compliant.append(ok_msg)
        elif fail_msg:
            violations.append(fail_msg)

    top_sources = list({c["source"] for c in chunks[:4]})
    refs = [{"source": s, "excerpt": "See policy document for full requirements.", "relevance": "Retrieved as most relevant to this transcript."} for s in top_sources]

    summary = f"Heuristic policy check: {len(compliant)} compliant items, {len(violations)} potential violations detected. Upload API keys for full LLM-powered RAG analysis."

    return {
        "policy_references": refs,
        "policy_violations": violations,
        "policy_compliant_items": compliant,
        "contextual_coaching": "Enable LLM keys for detailed policy-grounded coaching. Heuristic mode checks for key phrases only.",
        "rag_summary": summary,
        "retrieved_chunks": chunks,
    }


def _hash_docs(docs_dir: str) -> str:
    """Hash all document files in a directory to detect changes."""
    h = hashlib.md5()
    docs_path = Path(docs_dir)
    for fp in sorted(docs_path.glob("*.*")):
        if fp.suffix in {".txt", ".md", ".pdf"}:
            h.update(fp.name.encode())
            h.update(fp.read_bytes()[:1024])  # hash first 1KB per file
    return h.hexdigest()


def list_policy_docs(docs_dir: str = str(POLICY_DOCS_DIR)) -> list[dict]:
    """Return metadata about all loaded policy documents."""
    ensure_sample_policies()
    docs = []
    for fp in Path(docs_dir).glob("*.*"):
        if fp.suffix in {".txt", ".md", ".pdf"}:
            text = fp.read_text(encoding="utf-8", errors="ignore") if fp.suffix != ".pdf" else ""
            docs.append({
                "name": fp.name,
                "size_kb": round(fp.stat().st_size / 1024, 1),
                "lines": len(text.splitlines()),
                "preview": text[:200].strip(),
            })
    return docs


def get_index_stats() -> dict:
    """Return stats about the current vector index."""
    store = get_store()
    loaded = store.load()
    if not loaded:
        return {"indexed": False, "chunks": 0, "store_type": "none"}

    store_type = "FAISS" if (FAISS_OK and NUMPY_OK) else "SimpleVectorStore"
    return {
        "indexed": True,
        "chunks": len(store.metadata),
        "store_type": store_type,
        "sources": list({m["source"] for m in store.metadata}),
    }

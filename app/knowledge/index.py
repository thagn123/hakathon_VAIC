"""Restart-safe SQLite hybrid index for the offline MVP."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from pathlib import Path
from typing import Iterable, List, Optional, Protocol, Sequence

from app.config import settings
from app.knowledge.models import KnowledgeChunk, RetrievalHit
from app.knowledge.retrieval_contracts import AuthorityTier, VerificationStatus

# Lower rank = more authoritative / more verified. Used only to compare a
# candidate's tier/status against a caller-supplied *minimum* -- callers
# that never pass minimum_authority_tier/minimum_verification_status do not
# trigger this comparison at all (see _filter_eligible).
_AUTHORITY_RANK = {
    AuthorityTier.TIER_1_AUTHORITATIVE: 0,
    AuthorityTier.TIER_2_VERIFIED_INTERNAL: 1,
    AuthorityTier.TIER_3_CUSTOMER_PROVIDED_UNVERIFIED: 2,
    AuthorityTier.TIER_4_MODEL_INFERENCE: 3,
    AuthorityTier.TIER_5_UNSUPPORTED: 4,
}
_VERIFICATION_RANK = {
    VerificationStatus.VERIFIED: 0,
    VerificationStatus.PENDING: 1,
    VerificationStatus.UNVERIFIED: 2,
    VerificationStatus.REJECTED: 3,
}


class RepresentationType(str, Enum):
    """Honest label for what an ``EmbeddingProvider.embed()`` vector actually
    is -- RAG & Guardrail Implementation Plan Phase 1 / prompt instruction:
    "Audit đã xác nhận embedding mặc định hiện tại là hash bag-of-words...
    Không được tiếp tục gọi nó là: semantic embedding; dense semantic
    retrieval; neural embedding; meaning-based vector search." Before this,
    every caller of the "dense" channel had no way to know, from the code
    alone, whether a match reflected real semantic similarity or a hashed
    bag-of-words collision."""

    HASH_BOW_VECTOR = "HASH_BOW_VECTOR"
    SEMANTIC_EMBEDDING = "SEMANTIC_EMBEDDING"
    SPARSE_LEXICAL = "SPARSE_LEXICAL"


class MetadataFilterReason(str, Enum):
    """Reason a candidate chunk was excluded before scoring/ranking -- Phase
    1 / prompt section 5 ("Mọi record bị loại phải có reason code nội bộ").

    Only three of the prompt's nine suggested codes are implemented here,
    honestly: KnowledgeChunk (app/knowledge/models.py) has no
    is_superseded/is_quarantined/verification_status/tenant_id/case_id/
    actor_role fields today, so SOURCE_SUPERSEDED, SOURCE_QUARANTINED,
    VERIFICATION_LEVEL_TOO_LOW, TENANT_SCOPE_MISMATCH, CASE_SCOPE_MISMATCH
    and ROLE_NOT_ALLOWED cannot be reported without inventing data the
    schema doesn't carry -- see docs/RAG_GUARDRAIL_IMPLEMENTATION_REPORT.md
    Phase 1 "Metadata Filtering" for the explicit NOT_IMPLEMENTED note."""

    SOURCE_NOT_EFFECTIVE = "SOURCE_NOT_EFFECTIVE"
    SOURCE_SCOPE_MISMATCH = "SOURCE_SCOPE_MISMATCH"
    AGENT_SOURCE_NOT_ALLOWED = "AGENT_SOURCE_NOT_ALLOWED"
    # Phase 2 additions -- KnowledgeChunk now carries the fields these need
    # (customer_id/case_id/is_superseded/is_quarantined/authority_tier/
    # verification_status/allowed_roles, app/knowledge/models.py), so these
    # can be reported honestly. Still NOT implemented: TENANT_SCOPE_MISMATCH
    # (no multi-tenant concept in this repo, see retrieval_contracts.py
    # module docstring). Callers only see these reasons when the *caller*
    # passes the corresponding filter argument (customer_id=, case_id=,
    # actor_role=, minimum_authority_tier=, minimum_verification_status=)
    # -- omitting an argument means "do not filter on this dimension", not
    # "reject everything", so legacy search()/sparse_search_bm25() callers
    # that never pass these arguments are unaffected.
    CUSTOMER_SCOPE_MISMATCH = "CUSTOMER_SCOPE_MISMATCH"
    CASE_SCOPE_MISMATCH = "CASE_SCOPE_MISMATCH"
    SOURCE_SUPERSEDED = "SOURCE_SUPERSEDED"
    SOURCE_QUARANTINED = "SOURCE_QUARANTINED"
    VERIFICATION_LEVEL_TOO_LOW = "VERIFICATION_LEVEL_TOO_LOW"
    AUTHORITY_LEVEL_TOO_LOW = "AUTHORITY_LEVEL_TOO_LOW"
    ROLE_NOT_ALLOWED = "ROLE_NOT_ALLOWED"
    SECURITY_CLASSIFICATION_DENIED = "SECURITY_CLASSIFICATION_DENIED"


class RetrievalOutcomeCode(str, Enum):
    """Distinguishes *why* a search returned zero (or fewer than expected)
    hits -- RAG & Guardrail Implementation Plan Phase 0 / prompt section 21:
    "Không silently chuyển: retrieval provider failure -> no results."
    Before this, ``search()`` always returned a bare ``[]`` for every one
    of these three genuinely different situations, so a caller (or an
    Agent downstream) could not tell "the corpus has nothing relevant"
    (safe to treat as evidence of absence) apart from "the index has no
    chunks at all" or "the query had no indexable tokens" (neither of
    which says anything about whether the corpus covers the topic)."""

    OK = "ok"
    NO_RELEVANT_RESULT = "no_relevant_result"
    INDEX_NOT_READY = "index_not_ready"
    EMPTY_QUERY = "empty_query"


@dataclass(frozen=True)
class IndexNamespace:
    """Identity of one PersistentHybridIndex's dense vector space -- Phase 2
    "Index Namespace Validation": a query embedded by provider X must never
    be dot-producted against vectors an index built with provider Y wrote,
    since the two are not comparable numbers (different hash space, or a
    different real embedding model with a different geometry). Two
    PersistentHybridIndex instances are namespace-COMPATIBLE only when every
    field here matches exactly.

    normalization is reported honestly per provider: LocalEmbedding L2-
    normalizes its vectors in code (see LocalEmbedding.embed), so "l2" is
    verified; CachedGeminiEmbedding/CachedOpenAIEmbedding vectors come back
    from the provider API as-is -- this code has never inspected whether
    they are pre-normalized, so "unknown" is the honest label rather than
    assuming "l2" by analogy."""

    provider_id: str
    representation_type: RepresentationType
    dimension: int
    normalization: str
    corpus_version: str


def namespace_mismatch(query_ns: IndexNamespace, index_ns: IndexNamespace) -> bool:
    """True when a query built for query_ns must not be scored against
    index_ns's stored vectors. corpus_version is deliberately NOT part of
    this comparison -- a corpus can be re-ingested (new corpus_version)
    without the embedding *space* changing, so only provider_id/
    representation_type/dimension/normalization are namespace-defining."""
    return (
        query_ns.provider_id != index_ns.provider_id
        or query_ns.representation_type != index_ns.representation_type
        or query_ns.dimension != index_ns.dimension
        or query_ns.normalization != index_ns.normalization
    )


@dataclass(frozen=True)
class RetrievalDiagnostics:
    outcome: RetrievalOutcomeCode
    candidate_count: int
    filtered_count: int
    # Additive Phase 1 fields (default-valued so existing positional/keyword
    # construction of this dataclass -- e.g. from a future caller -- does not
    # break): honest disclosure of what the dense channel actually is for
    # this search, per prompt instruction "Không benchmark nó như semantic
    # dense retrieval."
    representation_type: RepresentationType = RepresentationType.HASH_BOW_VECTOR
    semantic_capability: bool = False
    filtered_reasons: dict[str, int] = field(default_factory=dict)


class _ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


def fold(text: str) -> str:
    value = unicodedata.normalize("NFD", (text or "").lower())
    return "".join(ch for ch in value if unicodedata.category(ch) != "Mn").replace("đ", "d")


_STOPWORDS = {
    "la", "va", "cua", "cho", "co", "mot", "cac", "doanh", "nghiep", "de", "duoc",
    # Expanded per services/rag_mcp/embedding.py precedent: a short stopword list
    # lets generic Vietnamese filler words collide with corpus tokens after
    # diacritic-fold, inflating the sparse-overlap score for out-of-scope queries.
    "trong", "ngoai", "tren", "duoi", "giua", "ve", "voi", "tu", "den", "nhu",
    "ra", "vao", "sau", "truoc", "nay", "kia", "ay", "nao", "gi", "ai", "sao",
    "the", "nen", "boi", "tai", "khi", "neu", "hay", "toi", "ta", "nam", "nhat",
}


def tokens(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9-]+", fold(text)) if len(token) > 1 and token not in _STOPWORDS}


def token_list(text: str) -> List[str]:
    """Same normalization as tokens(), but preserves term frequency (a
    set collapses repeats) -- BM25 needs f(t,D), not just membership."""
    return [token for token in re.findall(r"[a-z0-9-]+", fold(text)) if len(token) > 1 and token not in _STOPWORDS]


def bm25_scores(
    query_tokens: Sequence[str],
    documents: Sequence[Sequence[str]],
    *,
    k1: float = 1.5,
    b: float = 0.75,
) -> List[float]:
    """Real Okapi BM25 -- Phase 1 / prompt section 6: "Không được giả vờ
    hash-vector hiện tại là BM25." Standalone and pure (no I/O, no
    PersistentHybridIndex dependency) so it is trivially unit-testable
    against hand-computed values -- see
    tests/retrieval/test_sparse_retrieval.py.

    ``documents`` is the already-tokenized (token_list, not tokens -- term
    frequency matters) corpus in the same order the caller wants scores
    back in. Standard defaults k1=1.5, b=0.75.
    """
    n_docs = len(documents)
    if n_docs == 0 or not query_tokens:
        return [0.0] * n_docs
    doc_lengths = [len(doc) for doc in documents]
    avg_doc_length = sum(doc_lengths) / n_docs if n_docs else 0.0

    doc_freq: Dict[str, int] = {}
    unique_query_terms = set(query_tokens)
    for doc in documents:
        doc_term_set = set(doc)
        for term in unique_query_terms:
            if term in doc_term_set:
                doc_freq[term] = doc_freq.get(term, 0) + 1

    idf: Dict[str, float] = {}
    for term in unique_query_terms:
        n_t = doc_freq.get(term, 0)
        idf[term] = math.log((n_docs - n_t + 0.5) / (n_t + 0.5) + 1.0)

    scores: List[float] = []
    for doc, doc_length in zip(documents, doc_lengths):
        term_freq: Dict[str, int] = {}
        for term in doc:
            if term in unique_query_terms:
                term_freq[term] = term_freq.get(term, 0) + 1
        score = 0.0
        for term in unique_query_terms:
            f_t_d = term_freq.get(term, 0)
            if f_t_d == 0:
                continue
            denom = f_t_d + k1 * (1 - b + b * (doc_length / avg_doc_length if avg_doc_length else 0.0))
            score += idf[term] * (f_t_d * (k1 + 1)) / denom
        scores.append(score)
    return scores


class EmbeddingProvider(Protocol):
    name: str
    dimension: int

    def embed(self, text: str) -> List[float]: ...

    @property
    def representation_type(self) -> RepresentationType:
        """Honest classification of this provider's vector space -- see
        RepresentationType. Protocol members are structurally optional (a
        provider written before Phase 1 that lacks this property is still a
        valid EmbeddingProvider at the type level), so every call site that
        reads it must use getattr(provider, "representation_type",
        RepresentationType.HASH_BOW_VECTOR) rather than assume it exists --
        see PersistentHybridIndex.search_with_diagnostics()."""
        ...


class CachedGeminiEmbedding:
    """Production embedding via Google AI Studio (``google-genai`` SDK).

    Uses the AI Studio key (``GOOGLE_API_KEY``) with ``gemini-embedding-2`` by
    default, local cache keyed by content hash (offline + deterministic after
    a warm cache). The OpenAI provider remains available as a fallback.
    """
    name = "gemini-embedding-2"

    @property
    def representation_type(self) -> RepresentationType:
        return RepresentationType.SEMANTIC_EMBEDDING

    def __init__(self, dimension: int = 3072, cache_file: Optional[Path] = None) -> None:
        self.dimension = dimension
        self.api_key = settings.GOOGLE_API_KEY or os.getenv("GOOGLE_API_KEY")
        cache_default = Path("/tmp/gemini_vector_cache.json") if os.getenv("VERCEL") else Path(settings.VECTOR_DB_DIR) / "gemini_vector_cache.json"
        self.cache_file = cache_file or cache_default
        self.cache: dict[str, List[float]] = {}
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    def embed(self, text: str) -> List[float]:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]

        from dotenv import load_dotenv

        load_dotenv()
        api_key = self.api_key or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GOOGLE_API_KEY (AI Studio) is not set for CachedGeminiEmbedding.")

        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        response = client.models.embed_content(
            model=self.name,
            contents=[text],
            config=types.EmbedContentConfig(task_type="SEMANTIC_SIMILARITY"),
        )
        vector = list(response.embeddings[0].values)

        self.cache[text_hash] = vector
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache), encoding="utf-8")

        return vector



class CachedOpenAIEmbedding:
    """Production provider using text-embedding-3-small, with a local JSON cache
    so repeated ingestion/tests never re-pay for an unchanged chunk/query text."""

    name = "openai-text-embedding-3-small"

    @property
    def representation_type(self) -> RepresentationType:
        return RepresentationType.SEMANTIC_EMBEDDING

    def __init__(self, dimension: int = 1536, cache_file: Optional[Path] = None) -> None:
        self.dimension = dimension
        self.api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        self.client = None
        cache_default = Path("/tmp/openai_vector_cache.json") if os.getenv("VERCEL") else Path(settings.VECTOR_DB_DIR) / "openai_vector_cache.json"
        self.cache_file = cache_file or cache_default
        self.cache: dict[str, List[float]] = {}
        if self.cache_file.exists():
            try:
                self.cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                pass

    def _get_client(self):
        if not self.client:
            if not self.api_key:
                raise RuntimeError("OPENAI_API_KEY is not set for CachedOpenAIEmbedding.")
            from openai import OpenAI

            self.client = OpenAI(api_key=self.api_key)
        return self.client

    def embed(self, text: str) -> List[float]:
        text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        client = self._get_client()
        response = client.embeddings.create(input=[text], model="text-embedding-3-small")
        vector = response.data[0].embedding
        self.cache[text_hash] = vector
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache), encoding="utf-8")
        return vector


class LocalEmbedding:
    """Deterministic, key-free embedding for offline/dev/test and reproducible CI.

    Hashes content tokens into a fixed-dim bag-of-words vector (preserving
    exact-token overlap). No API key required; swap to ``gemini``/``openai`` for
    production semantic recall once a billing-backed key is provisioned.
    """

    name = "local"
    _DIM = 256

    @property
    def representation_type(self) -> RepresentationType:
        return RepresentationType.HASH_BOW_VECTOR

    def __init__(self, dimension: int = _DIM) -> None:
        self.dimension = dimension

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dimension
        for token in tokens(text):
            h = int.from_bytes(hashlib.sha256(token.encode("utf-8")).digest()[:8], "big")
            idx = h % self.dimension
            mag = 1.0 + ((h >> 8) & 0xFF) / 255.0
            vec[idx] += mag
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0.0:
            vec = [v / norm for v in vec]
        return vec


def create_embedding_provider(name: Optional[str] = None) -> EmbeddingProvider:
    # Default is "local": deterministic and key-free so the suite runs offline
    # with zero API keys and CI is reproducible. Set the env var to "gemini"
    # (Google AI Studio key GOOGLE_API_KEY, gemini-embedding-2) or "openai" for
    # production semantic recall.
    provider = (name or os.getenv("KNOWLEDGE_EMBEDDING_PROVIDER") or "local").strip().lower()
    if provider == "local":
        return LocalEmbedding()
    if provider == "gemini":
        return CachedGeminiEmbedding()
    if provider == "openai":
        return CachedOpenAIEmbedding()
    raise ValueError(f"Unsupported embedding provider {provider!r}.")


class PersistentHybridIndex:
    def __init__(self, db_path: str | Path, provider: Optional[EmbeddingProvider] = None) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.provider = provider or create_embedding_provider()
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, factory=_ClosingConnection)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    chunk_id TEXT PRIMARY KEY,
                    payload TEXT NOT NULL,
                    vector TEXT NOT NULL,
                    content_hash TEXT NOT NULL
                )"""
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS index_manifests (
                    source_hash TEXT PRIMARY KEY,
                    dataset_version TEXT NOT NULL,
                    indexed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )

    def upsert(self, chunks: Iterable[KnowledgeChunk], *, source_hash: str, dataset_version: str) -> int:
        rows = list(chunks)
        with self._connect() as connection:
            for chunk in rows:
                connection.execute(
                    """INSERT INTO knowledge_chunks(chunk_id, payload, vector, content_hash)
                       VALUES (?, ?, ?, ?)
                       ON CONFLICT(chunk_id) DO UPDATE SET
                         payload=excluded.payload, vector=excluded.vector, content_hash=excluded.content_hash""",
                    (
                        chunk.chunk_id,
                        chunk.model_dump_json(),
                        json.dumps(self.provider.embed(chunk.text)),
                        chunk.content_hash,
                    ),
                )
            connection.execute(
                "INSERT OR IGNORE INTO index_manifests(source_hash, dataset_version) VALUES (?, ?)",
                (source_hash, dataset_version),
            )
        return len(rows)

    def count(self) -> int:
        with self._connect() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0])

    def namespace(self) -> IndexNamespace:
        """This index's current dense-vector-space identity -- see
        IndexNamespace. corpus_version is the most recent dataset_version
        recorded by upsert() (or "unversioned" for an index that has never
        been ingested into), read directly from index_manifests -- not
        cached, so it reflects the true on-disk state even if another
        process/agent has ingested into this same db_path concurrently."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT dataset_version FROM index_manifests ORDER BY indexed_at DESC LIMIT 1"
            ).fetchone()
        corpus_version = row["dataset_version"] if row else "unversioned"
        normalization = "l2" if isinstance(self.provider, LocalEmbedding) else "unknown"
        return IndexNamespace(
            provider_id=self.provider.name,
            representation_type=getattr(self.provider, "representation_type", RepresentationType.HASH_BOW_VECTOR),
            dimension=self.provider.dimension,
            normalization=normalization,
            corpus_version=corpus_version,
        )

    def eligibility_diagnostics(
        self,
        *,
        branch: str = "*",
        segment: Optional[str] = None,
        as_of: Optional[date] = None,
        product_ids: Optional[Sequence[str]] = None,
        customer_id: Optional[str] = None,
        case_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        minimum_authority_tier: Optional[AuthorityTier] = None,
        minimum_verification_status: Optional[VerificationStatus] = None,
        allowed_security_classifications: Optional[Sequence[str]] = None,
    ) -> tuple[int, int, dict[str, int]]:
        """(total_count, eligible_count, filtered_reasons) for the given
        filter set -- runs the exact same _filter_eligible pass the
        dense/sparse channels use, without doing any scoring. Exists so
        ControlledRetrievalOrchestrator can report honest
        candidate_count_before_filter/after_filter/blocked_candidate_reason_counts
        diagnostics without duplicating the filtering logic a second time."""
        today = as_of or date.today()
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM knowledge_chunks").fetchall()
        eligible, reasons = self._filter_eligible(
            rows, today=today, branch=branch, segment=segment, product_ids=product_ids,
            customer_id=customer_id, case_id=case_id, actor_role=actor_role,
            minimum_authority_tier=minimum_authority_tier, minimum_verification_status=minimum_verification_status,
            allowed_security_classifications=allowed_security_classifications,
        )
        return len(rows), len(eligible), reasons

    def list_chunks(self) -> List[KnowledgeChunk]:
        """All chunks currently in this index, newest-insertion-order not
        guaranteed (SQLite makes no ordering promise without ORDER BY).
        Small-corpus-only (this repo's indexes hold single/double-digit
        chunk counts) -- for the Agent Knowledge Console listing view
        (app/api/v2/knowledge_router.py), not a paginated bulk-export API."""
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM knowledge_chunks").fetchall()
        return [KnowledgeChunk.model_validate_json(row["payload"]) for row in rows]

    def exact_lookup_by_chunk_id(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        """Exact Structured Lookup (Phase 1 / prompt section 4): a request
        that already names a specific chunk_id must be answered by a direct
        key lookup, never by running it back through semantic/sparse
        scoring to "guess" the intended entity. chunk_id is the table's
        PRIMARY KEY (see _initialize()), so this is a true O(1) exact
        match, not a filtered scan."""
        with self._connect() as connection:
            row = connection.execute(
                "SELECT payload FROM knowledge_chunks WHERE chunk_id = ?", (chunk_id,)
            ).fetchone()
        if row is None:
            return None
        return KnowledgeChunk.model_validate_json(row["payload"])

    def expand_to_parent_context(self, chunk_id: str) -> Optional[KnowledgeChunk]:
        """Hierarchical Parent-Child Retrieval (Phase 3 section 26): given
        a retrieved CHILD chunk_id, return its parent (broader section/
        document-level context), or None if the chunk has no
        parent_chunk_id or the parent was not found. Citation must still
        point at the ORIGINAL child chunk_id -- this method is for
        expanding CONTEXT shown to an Agent, never for replacing what a
        GroundingItem cites."""
        child = self.exact_lookup_by_chunk_id(chunk_id)
        if child is None or child.parent_chunk_id is None:
            return None
        return self.exact_lookup_by_chunk_id(child.parent_chunk_id)

    def exact_lookup_by_product_id(
        self,
        product_id: str,
        *,
        as_of: Optional[date] = None,
        branch: str = "*",
        customer_id: Optional[str] = None,
        case_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        minimum_authority_tier: Optional[AuthorityTier] = None,
        minimum_verification_status: Optional[VerificationStatus] = None,
        allowed_security_classifications: Optional[Sequence[str]] = None,
    ) -> List[KnowledgeChunk]:
        """Exact Structured Lookup for a request that already names a
        specific product_id: return every currently-effective, in-scope
        chunk for that exact product, with no relevance scoring at all.
        Still enforces the same freshness/ACL/lifecycle/security boundary
        as search() (a request naming an exact ID does not bypass access
        control -- Phase 2 extends this to quarantine/supersede/customer/
        case/authority/verification, previously only freshness+branch),
        but never falls back to sparse/dense matching against a different
        product_id -- an exact ID that resolves to zero chunks is
        EXACT_ENTITY_NOT_FOUND, not a semantic near-miss."""
        today = as_of or date.today()
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM knowledge_chunks").fetchall()
        product_rows = [row for row in rows if KnowledgeChunk.model_validate_json(row["payload"]).product_id == product_id]
        eligible, _reasons = self._filter_eligible(
            product_rows, today=today, branch=branch, segment=None, product_ids=None,
            customer_id=customer_id, case_id=case_id, actor_role=actor_role,
            minimum_authority_tier=minimum_authority_tier, minimum_verification_status=minimum_verification_status,
            allowed_security_classifications=allowed_security_classifications,
        )
        return [chunk for chunk, _row in eligible]

    def get_chunks_for_document(
        self, document_id: str, document_version: Optional[str] = None
    ) -> List[KnowledgeChunk]:
        """Return every indexed chunk for a (document_id[, document_version]).

        Used by the evidence validator to independently re-check that a
        claimed quote genuinely appears in what this index actually serves,
        rather than trusting whatever the evidence-producing code wrote into
        Evidence.quote. Passing document_version=None returns chunks for
        *any* version of the document, which lets a caller distinguish
        "unknown document" from "known document, wrong version cited".
        """
        matches: List[KnowledgeChunk] = []
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM knowledge_chunks").fetchall()
        for row in rows:
            chunk = KnowledgeChunk.model_validate_json(row["payload"])
            if chunk.document_id != document_id:
                continue
            if document_version is not None and chunk.document_version != document_version:
                continue
            matches.append(chunk)
        return matches

    def _filter_eligible(
        self,
        rows: Sequence[sqlite3.Row],
        *,
        today: date,
        branch: str,
        segment: Optional[str],
        product_ids: Optional[Sequence[str]],
        customer_id: Optional[str] = None,
        case_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        minimum_authority_tier: Optional[AuthorityTier] = None,
        minimum_verification_status: Optional[VerificationStatus] = None,
        allowed_security_classifications: Optional[Sequence[str]] = None,
    ) -> tuple[List[tuple[KnowledgeChunk, sqlite3.Row]], dict[str, int]]:
        """Shared eligibility pass -- Phase 2 "Security Pre-Filter": resolve
        the eligible source set BEFORE any channel (dense/sparse/BM25)
        scores or ranks anything, so no channel can leak a candidate a
        different channel would have rejected. Used by
        search_with_diagnostics(), sparse_search_bm25() and dense_search()
        so the three channels can never silently diverge on who is allowed
        to see what.

        customer_id/case_id/actor_role/minimum_authority_tier/
        minimum_verification_status are all optional and additive: a
        caller that never passes them (every pre-Phase-2 call site) gets
        exactly the Phase 0/1 filtering behavior, unchanged. A chunk whose
        customer_id/case_id is None (a generic product/policy/SOP chunk)
        is never rejected on that dimension -- only a chunk that names a
        *specific*, *different* customer/case is."""
        eligible: List[tuple[KnowledgeChunk, sqlite3.Row]] = []
        filtered_reasons: dict[str, int] = {}

        def _reject(reason: MetadataFilterReason) -> None:
            filtered_reasons[reason.value] = filtered_reasons.get(reason.value, 0) + 1

        for row in rows:
            chunk = KnowledgeChunk.model_validate_json(row["payload"])
            if not chunk.active or chunk.effective_from > today:
                _reject(MetadataFilterReason.SOURCE_NOT_EFFECTIVE)
                continue
            if chunk.effective_to is not None and chunk.effective_to < today:
                _reject(MetadataFilterReason.SOURCE_NOT_EFFECTIVE)
                continue
            branches = chunk.access_scope.get("branches", [])
            if "*" not in branches and branch not in branches:
                _reject(MetadataFilterReason.SOURCE_SCOPE_MISMATCH)
                continue
            if segment and segment not in chunk.segments:
                _reject(MetadataFilterReason.AGENT_SOURCE_NOT_ALLOWED)
                continue
            if product_ids and chunk.product_id not in product_ids:
                _reject(MetadataFilterReason.AGENT_SOURCE_NOT_ALLOWED)
                continue
            if customer_id is not None and chunk.customer_id is not None and chunk.customer_id != customer_id:
                _reject(MetadataFilterReason.CUSTOMER_SCOPE_MISMATCH)
                continue
            if case_id is not None and chunk.case_id is not None and chunk.case_id != case_id:
                _reject(MetadataFilterReason.CASE_SCOPE_MISMATCH)
                continue
            if chunk.is_superseded:
                _reject(MetadataFilterReason.SOURCE_SUPERSEDED)
                continue
            if chunk.is_quarantined:
                _reject(MetadataFilterReason.SOURCE_QUARANTINED)
                continue
            if minimum_verification_status is not None:
                candidate_status = chunk.verification_status or VerificationStatus.UNVERIFIED
                if _VERIFICATION_RANK[candidate_status] > _VERIFICATION_RANK[minimum_verification_status]:
                    _reject(MetadataFilterReason.VERIFICATION_LEVEL_TOO_LOW)
                    continue
            if minimum_authority_tier is not None:
                candidate_tier = chunk.authority_tier or AuthorityTier.TIER_5_UNSUPPORTED
                if _AUTHORITY_RANK[candidate_tier] > _AUTHORITY_RANK[minimum_authority_tier]:
                    _reject(MetadataFilterReason.AUTHORITY_LEVEL_TOO_LOW)
                    continue
            if actor_role is not None and chunk.allowed_roles and actor_role not in chunk.allowed_roles:
                _reject(MetadataFilterReason.ROLE_NOT_ALLOWED)
                continue
            if allowed_security_classifications is not None and chunk.security_classification not in allowed_security_classifications:
                _reject(MetadataFilterReason.SECURITY_CLASSIFICATION_DENIED)
                continue
            eligible.append((chunk, row))
        return eligible, filtered_reasons

    def sparse_search_bm25(
        self,
        query: str,
        *,
        top_k: int = 5,
        branch: str = "*",
        segment: Optional[str] = None,
        as_of: Optional[date] = None,
        product_ids: Optional[Sequence[str]] = None,
        customer_id: Optional[str] = None,
        case_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        minimum_authority_tier: Optional[AuthorityTier] = None,
        minimum_verification_status: Optional[VerificationStatus] = None,
        allowed_security_classifications: Optional[Sequence[str]] = None,
    ) -> List[RetrievalHit]:
        """Real BM25 sparse channel -- Phase 1 / prompt section 6. Additive:
        does not replace or affect search()/search_with_diagnostics(),
        which keep their existing token-overlap sparse component untouched.

        Applies the same freshness/ACL/lifecycle/security metadata
        filtering as search() (via _filter_eligible) -- an exact/sparse/
        dense channel choice must never bypass the security boundary, only
        change how the *eligible* candidate set gets ranked."""
        query_tok = token_list(query)
        if not query_tok:
            return []
        today = as_of or date.today()
        with self._connect() as connection:
            rows = connection.execute("SELECT payload FROM knowledge_chunks").fetchall()
        eligible, _reasons = self._filter_eligible(
            rows, today=today, branch=branch, segment=segment, product_ids=product_ids,
            customer_id=customer_id, case_id=case_id, actor_role=actor_role,
            minimum_authority_tier=minimum_authority_tier, minimum_verification_status=minimum_verification_status,
            allowed_security_classifications=allowed_security_classifications,
        )
        if not eligible:
            return []
        eligible_chunks = [chunk for chunk, _row in eligible]
        doc_token_lists = [token_list(chunk.text) for chunk in eligible_chunks]
        scores = bm25_scores(query_tok, doc_token_lists)
        hits = [
            RetrievalHit(chunk=chunk, score=min(1.0, score / 10.0), dense_score=0.0, sparse_score=min(1.0, score / 10.0))
            for chunk, score in zip(eligible_chunks, scores)
            if score > 0.0
        ]
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]

    def dense_search(
        self,
        query: str,
        *,
        top_k: int = 5,
        branch: str = "*",
        segment: Optional[str] = None,
        as_of: Optional[date] = None,
        product_ids: Optional[Sequence[str]] = None,
        customer_id: Optional[str] = None,
        case_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        minimum_authority_tier: Optional[AuthorityTier] = None,
        minimum_verification_status: Optional[VerificationStatus] = None,
        allowed_security_classifications: Optional[Sequence[str]] = None,
    ) -> List[RetrievalHit]:
        """Pure dense channel -- Phase 2 / RRF fusion needs an INDEPENDENT
        dense-only ranking to fuse-by-rank with sparse_search_bm25()'s
        independent ranking (search_with_diagnostics()'s legacy linear-sum
        conflates dense+sparse into one score and cannot be fused again).
        score == dense_score here; sparse_score is always 0.0 (this channel
        does not consider lexical overlap at all -- that is the point)."""
        query_tokens = tokens(query)
        if not query_tokens:
            return []
        if self.count() == 0:
            return []
        query_vector = self.provider.embed(query)
        today = as_of or date.today()
        with self._connect() as connection:
            rows = connection.execute("SELECT payload, vector FROM knowledge_chunks").fetchall()
        eligible, _reasons = self._filter_eligible(
            rows, today=today, branch=branch, segment=segment, product_ids=product_ids,
            customer_id=customer_id, case_id=case_id, actor_role=actor_role,
            minimum_authority_tier=minimum_authority_tier, minimum_verification_status=minimum_verification_status,
            allowed_security_classifications=allowed_security_classifications,
        )
        hits: List[RetrievalHit] = []
        for chunk, row in eligible:
            dense_raw = max(0.0, min(1.0, sum(a * b for a, b in zip(query_vector, json.loads(row["vector"])))))
            if dense_raw <= 0.0:
                continue
            hits.append(RetrievalHit(chunk=chunk, score=round(dense_raw, 6), dense_score=round(dense_raw, 6), sparse_score=0.0))
        return sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]

    def search(
        self,
        query: str,
        *,
        top_k: int = 5,
        branch: str = "*",
        segment: Optional[str] = None,
        as_of: Optional[date] = None,
        product_ids: Optional[Sequence[str]] = None,
        threshold: Optional[float] = None,
    ) -> List[RetrievalHit]:
        """Unchanged signature/behavior for all existing callers -- see
        search_with_diagnostics() for the reason-code-carrying variant added
        in Phase 0 of docs/RAG_GUARDRAIL_IMPLEMENTATION_PLAN.md."""
        hits, _diagnostics = self.search_with_diagnostics(
            query, top_k=top_k, branch=branch, segment=segment, as_of=as_of,
            product_ids=product_ids, threshold=threshold,
        )
        return hits

    def search_with_diagnostics(
        self,
        query: str,
        *,
        top_k: int = 5,
        branch: str = "*",
        segment: Optional[str] = None,
        as_of: Optional[date] = None,
        product_ids: Optional[Sequence[str]] = None,
        threshold: Optional[float] = None,
    ) -> tuple[List[RetrievalHit], RetrievalDiagnostics]:
        representation_type = getattr(self.provider, "representation_type", RepresentationType.HASH_BOW_VECTOR)
        semantic_capability = representation_type == RepresentationType.SEMANTIC_EMBEDDING
        query_tokens = tokens(query)
        if not query_tokens:
            return [], RetrievalDiagnostics(
                RetrievalOutcomeCode.EMPTY_QUERY, candidate_count=0, filtered_count=0,
                representation_type=representation_type, semantic_capability=semantic_capability,
            )
        if self.count() == 0:
            return [], RetrievalDiagnostics(
                RetrievalOutcomeCode.INDEX_NOT_READY, candidate_count=0, filtered_count=0,
                representation_type=representation_type, semantic_capability=semantic_capability,
            )
        query_vector = self.provider.embed(query)
        today = as_of or date.today()

        # Auto-calibrate threshold based on vector dimension (Gemini 768 vs OpenAI 1536)
        if threshold is not None:
            actual_threshold = threshold
        else:
            actual_threshold = 0.30 if self.provider.dimension == 768 else 0.40

        effective_threshold = min(actual_threshold, 0.20) if product_ids else actual_threshold
        hits: List[RetrievalHit] = []
        with self._connect() as connection:
            rows = connection.execute("SELECT payload, vector FROM knowledge_chunks").fetchall()
        candidate_count = len(rows)
        filtered_count = 0
        filtered_reasons: dict[str, int] = {}

        def _reject(reason: MetadataFilterReason) -> None:
            nonlocal filtered_count
            filtered_count += 1
            filtered_reasons[reason.value] = filtered_reasons.get(reason.value, 0) + 1

        for row in rows:
            chunk = KnowledgeChunk.model_validate_json(row["payload"])
            if not chunk.active or chunk.effective_from > today:
                _reject(MetadataFilterReason.SOURCE_NOT_EFFECTIVE)
                continue
            if chunk.effective_to is not None and chunk.effective_to < today:
                _reject(MetadataFilterReason.SOURCE_NOT_EFFECTIVE)
                continue
            branches = chunk.access_scope.get("branches", [])
            if "*" not in branches and branch not in branches:
                _reject(MetadataFilterReason.SOURCE_SCOPE_MISMATCH)
                continue
            if segment and segment not in chunk.segments:
                _reject(MetadataFilterReason.AGENT_SOURCE_NOT_ALLOWED)
                continue
            if product_ids and chunk.product_id not in product_ids:
                _reject(MetadataFilterReason.AGENT_SOURCE_NOT_ALLOWED)
                continue
            chunk_tokens = tokens(chunk.text)
            sparse = len(query_tokens & chunk_tokens) / len(query_tokens)
            # Clamped both ends: normalized-vector dot product is
            # mathematically bounded to [-1, 1], but floating-point error
            # on near-identical vectors (e.g. query text == chunk text)
            # can push the raw sum a hair over 1.0 (observed:
            # 1.000017), which RetrievalHit.dense_score's Field(le=1.0)
            # then rejects outright -- a latent bug pre-dating Phase 0/1,
            # found by tests/retrieval/test_embedding_representation.py.
            dense_raw = max(0.0, min(1.0, sum(a * b for a, b in zip(query_vector, json.loads(row["vector"])))))
            exact_bonus = 0.15 if chunk.product_id.lower() in query.lower() else 0.0
            score = min(1.0, 0.6 * dense_raw + 0.4 * sparse + exact_bonus)
            if sparse > 0 and score >= effective_threshold:
                hits.append(
                    RetrievalHit(
                        chunk=chunk,
                        score=round(score, 6),
                        dense_score=round(dense_raw, 6),
                        sparse_score=round(sparse, 6),
                    )
                )
        ranked = sorted(hits, key=lambda item: item.score, reverse=True)[:top_k]
        outcome = RetrievalOutcomeCode.OK if ranked else RetrievalOutcomeCode.NO_RELEVANT_RESULT
        return ranked, RetrievalDiagnostics(
            outcome, candidate_count=candidate_count, filtered_count=filtered_count,
            representation_type=representation_type, semantic_capability=semantic_capability,
            filtered_reasons=filtered_reasons,
        )

"""
cu_substrate.py — Collective Unconscious as a Quilt substrate.

Per quilt/issues/4 SYNERGY-3: wire the Collective Unconscious worker
(SuperInstance/collective-unconscious) as a Quilt substrate.

The Worker is a Cloudflare Worker with:
  - Vectorize binding "fleet-unconscious-1024"
  - Workers AI binding for embeddings
  - HTTP endpoint that accepts text + JEPA reading queries

This substrate wraps the HTTP API as a substrate for the substrate walker.
A cell can ask the substrate "what does the fleet remember about X" and
get back a list of (text_chunk, reading_vector, similarity_score) tuples
that become CellReceipts.

The substrate walker (me) composes this with the Vibe substrate (elephant
cynicism → Vibe) and the legalese layer (Receipt → Claim → Contract).

Honest boundaries:
- Does NOT require a live Worker URL — `MockCUBackend` is the default.
- Does NOT make HTTP calls in tests — uses the mock.
- Real Worker integration: pass `backend=CUWorkerBackend(url=...)` at init.
- Per the SYNERGY-3 RFC: the chunking strategy is the content lane's
  call; this substrate exposes the substrate walker side.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from typing import List, Optional, Protocol
from urllib.request import Request, urlopen
from urllib.error import URLError

from .vibe import CellReceipt


# === Backend protocol ===

class CUBackend(Protocol):
    """Anything that can answer 'what does the fleet remember about X?'."""

    def query(self, text: str, *, top_k: int = 5,
              reading_filter: Optional[dict] = None) -> List["MemoryHit"]: ...


@dataclass
class MemoryHit:
    """One result from the Collective Unconscious."""
    text: str
    reading_vector: List[float]   # 9-dial JEPA reading (mood, volume, ...)
    similarity: float             # cosine similarity to query [0, 1]
    source: str                   # "tap" | "hermes" | "mud" | "speech" | "unknown"
    timestamp: int                # unix seconds
    space_id: str                 # which room this came from


class MockCUBackend:
    """Offline mock — returns deterministic synthetic hits for tests."""

    def query(self, text: str, *, top_k: int = 5,
              reading_filter: Optional[dict] = None) -> List[MemoryHit]:
        # Deterministic per-text hash; same query → same hits
        seed = int(hashlib.sha256(text.encode()).hexdigest()[:8], 16)
        rng_state = seed
        def rand() -> float:
            nonlocal rng_state
            rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
            return rng_state / 0x7FFFFFFF

        hits = []
        for i in range(top_k):
            hits.append(MemoryHit(
                text=f"[mock-{i}] echo of '{text[:40]}'",
                reading_vector=[rand() for _ in range(9)],
                similarity=1.0 - (i * 0.15 + rand() * 0.1),
                source=["tap", "hermes", "mud", "speech"][i % 4],
                timestamp=int(time.time()) - i * 3600,
                space_id=f"mock-room-{i}",
            ))
        return hits


class CUWorkerBackend:
    """Real Cloudflare Worker backend — pass the deployed URL."""

    def __init__(self, url: str):
        self.url = url.rstrip("/")

    def query(self, text: str, *, top_k: int = 5,
              reading_filter: Optional[dict] = None) -> List[MemoryHit]:
        body = json.dumps({
            "text": text,
            "top_k": top_k,
            "reading_filter": reading_filter or {},
        }).encode()
        req = Request(
            f"{self.url}/query",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(req, timeout=10) as r:
                data = json.loads(r.read().decode())
        except URLError as e:
            raise RuntimeError(f"CU Worker unreachable: {e}") from e

        return [
            MemoryHit(
                text=h["text"],
                reading_vector=h.get("reading_vector", []),
                similarity=h.get("similarity", 0.0),
                source=h.get("source", "unknown"),
                timestamp=h.get("timestamp", 0),
                space_id=h.get("space_id", ""),
            )
            for h in data.get("hits", [])
        ]


# === The substrate ===

@dataclass
class CUSubstrate:
    """A Quilt substrate backed by the Collective Unconscious worker.

    Implements the substrate walker pattern:
      1. query() returns memory hits
      2. Each hit becomes a CellReceipt in the witness chain
      3. The legalese layer wraps the receipts as Claims
      4. The cell decides what to do with the answers
    """

    backend: CUBackend = field(default_factory=MockCUBackend)
    cell_id: str = "cu-substrate-cell"
    prev_witness_id: str = ""
    receipts: List[CellReceipt] = field(default_factory=list)

    def recall(self, question: str, *, top_k: int = 5,
               reading_filter: Optional[dict] = None) -> List[CellReceipt]:
        """Ask the Collective Unconscious. Returns a list of receipts.

        Each receipt is one memory hit, witnessed into the chain. The
        substrate walker composes these into a response.
        """
        hits = self.backend.query(question, top_k=top_k, reading_filter=reading_filter)
        receipts = []
        for hit in hits:
            r = self._hit_to_receipt(hit, question=question)
            self.prev_witness_id = r.witness_id
            self.receipts.append(r)
            receipts.append(r)
        return receipts

    def _hit_to_receipt(self, hit: MemoryHit, *, question: str) -> CellReceipt:
        body = json.dumps({
            "prev": self.prev_witness_id,
            "cell_id": self.cell_id,
            "substrate": "collective-unconscious",
            "polarity": "ACCEPT" if hit.similarity >= 0.5 else "REFUSE",
            "payload": {
                "question": question,
                "text_preview": hit.text[:80],
                "similarity": round(hit.similarity, 6),
                "source": hit.source,
                "space_id": hit.space_id,
                "reading_vector_dim": len(hit.reading_vector),
            },
            "ts": hit.timestamp,
        }, sort_keys=True).encode()
        witness_id = hashlib.sha256(body).hexdigest()[:16]

        polarity = "ACCEPT" if hit.similarity >= 0.5 else "REFUSE"

        return CellReceipt(
            witness_id=witness_id,
            prev_witness_id=self.prev_witness_id,
            cell_id=self.cell_id,
            substrate="collective-unconscious",
            polarity=polarity,
            payload={
                "question": question,
                "text_preview": hit.text[:80],
                "similarity": round(hit.similarity, 6),
                "source": hit.source,
                "space_id": hit.space_id,
                "reading_vector_dim": len(hit.reading_vector),
            },
            timestamp=hit.timestamp,
        )

    @property
    def memory_chain_head(self) -> str:
        """The witness id of the last memory receipt — for chaining."""
        return self.prev_witness_id

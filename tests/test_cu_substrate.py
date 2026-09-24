"""
test_cu_substrate.py — SYNERGY-3: Collective Unconscious → RAG substrate.

Per quilt/issues/4 SYNERGY-3:
  Index, chunk, and wire ai-writings + superinstance-papers into a Quilt RAG layer.
  Each cell becomes a queryable artifact.

This substrate wraps the existing Collective Unconscious worker as a substrate
for the substrate walker (the Mavis substrate walker pattern).
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from quilt_seed.cu_substrate import (
    CUSubstrate, MockCUBackend, CUWorkerBackend, MemoryHit,
)


class TestMockCUBackend(unittest.TestCase):
    def test_query_returns_n_hits(self):
        backend = MockCUBackend()
        hits = backend.query("what does the fleet remember about drift?", top_k=3)
        self.assertEqual(len(hits), 3)

    def test_query_is_deterministic(self):
        backend = MockCUBackend()
        hits_a = backend.query("drift in the room")
        hits_b = backend.query("drift in the room")
        self.assertEqual(len(hits_a), len(hits_b))
        self.assertEqual([h.text for h in hits_a], [h.text for h in hits_b])
        self.assertEqual([h.similarity for h in hits_a], [h.similarity for h in hits_b])

    def test_different_query_different_hits(self):
        backend = MockCUBackend()
        hits_a = backend.query("the room is cynical")
        hits_b = backend.query("the boat captain smiles")
        self.assertNotEqual([h.text for h in hits_a], [h.text for h in hits_b])

    def test_reading_vector_is_9_dial(self):
        backend = MockCUBackend()
        hits = backend.query("anything")
        for h in hits:
            self.assertEqual(len(h.reading_vector), 9)

    def test_similarity_decreases_with_index(self):
        backend = MockCUBackend()
        hits = backend.query("anything", top_k=5)
        # Similarities should generally decrease (allow small jitter)
        for i in range(len(hits) - 1):
            self.assertGreaterEqual(hits[i].similarity, hits[i + 1].similarity - 0.1)


class TestCUSubstrate(unittest.TestCase):
    def setUp(self):
        self.substrate = CUSubstrate(backend=MockCUBackend())

    def test_recall_emits_receipts(self):
        receipts = self.substrate.recall("drift", top_k=3)
        self.assertEqual(len(receipts), 3)

    def test_receipts_chain_via_prev(self):
        r1 = self.substrate.recall("first question", top_k=1)[0]
        r2 = self.substrate.recall("second question", top_k=1)[0]
        # r2's prev should be r1's witness id
        self.assertEqual(r2.prev_witness_id, r1.witness_id)

    def test_substrate_name_in_receipt(self):
        receipts = self.substrate.recall("anything", top_k=1)
        self.assertEqual(receipts[0].substrate, "collective-unconscious")

    def test_polarity_accept_for_high_similarity(self):
        receipts = self.substrate.recall("anything", top_k=1)
        # First hit has highest similarity in the mock
        self.assertEqual(receipts[0].polarity, "ACCEPT")

    def test_memory_chain_head_tracks(self):
        self.substrate.recall("q1", top_k=2)
        head1 = self.substrate.memory_chain_head
        self.substrate.recall("q2", top_k=2)
        head2 = self.substrate.memory_chain_head
        self.assertNotEqual(head1, head2)

    def test_payload_has_source_and_space(self):
        receipts = self.substrate.recall("anything", top_k=2)
        for r in receipts:
            self.assertIn("source", r.payload)
            self.assertIn("space_id", r.payload)
            self.assertIn("text_preview", r.payload)


class TestCUWorkerBackend(unittest.TestCase):
    def test_init_strips_trailing_slash(self):
        b = CUWorkerBackend("https://example.com/")
        self.assertEqual(b.url, "https://example.com")


if __name__ == '__main__':
    unittest.main()

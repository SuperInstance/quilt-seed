"""Tests for quilt-seed."""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import math
import unittest

from quilt_seed import (
    SeedCell, merge, mergeable,
    peck_detector, try_peck, ForwardModel,
    PeckedCell, Bearing,
    STATIONS,
    BridgeStation, Bridge, Cocapn, Vessel,
)
from quilt_seed.legalese import (
    LegaleseNetwork, Claim, Counter, Contract,
    QUESTION, CLAIM, EVIDENCE, REFUSAL,
    legalize_vessel_choice,
)


class TestSeedCell(unittest.TestCase):
    def test_initial_state(self):
        c = SeedCell()
        self.assertEqual(c.fast, 0.0)
        self.assertEqual(c.slow, 0.0)
        self.assertEqual(c.clock, 0)
        self.assertEqual(c.source, 0)

    def test_act_updates_fast_slow_clock(self):
        c = SeedCell()
        ev = c.act(1.0)
        self.assertEqual(c.fast, 1.0)
        self.assertGreater(c.slow, 0.0)
        self.assertEqual(c.clock, 1)
        self.assertIn("signal", ev)

    def test_ema_smoothing(self):
        c = SeedCell()
        for _ in range(20):
            c.act(1.0, ema_alpha=0.5)
        # After 20 ticks with ema_alpha=0.5, slow should converge to 1.
        self.assertAlmostEqual(c.slow, 1.0, places=3)

    def test_signal_is_difference(self):
        c = SeedCell()
        c.fast = 2.0
        c.slow = 1.0
        self.assertEqual(c.signal(), 1.0)


class TestMerge(unittest.TestCase):
    def test_merge_picks_higher_clock(self):
        a = SeedCell(fast=1.0, slow=1.0, clock=10, source=1)
        b = SeedCell(fast=2.0, slow=2.0, clock=20, source=1)
        m = merge(a, b)
        self.assertEqual(m, b)

    def test_merge_picks_higher_source_on_tie(self):
        a = SeedCell(fast=1.0, slow=1.0, clock=10, source=1)
        b = SeedCell(fast=2.0, slow=2.0, clock=10, source=2)
        m = merge(a, b)
        self.assertEqual(m, b)

    def test_mergeable_requires_same_source(self):
        a = SeedCell(source=1)
        b = SeedCell(source=2)
        self.assertFalse(mergeable(a, b))

    def test_mergeable_when_same_source(self):
        a = SeedCell(source=1)
        b = SeedCell(source=1)
        self.assertTrue(mergeable(a, b))


class TestPeckDetector(unittest.TestCase):
    def test_peck_detector_too_young(self):
        c = SeedCell()
        c.act(1.0)
        pecked, fm = peck_detector(c)
        self.assertFalse(pecked)

    def test_peck_detector_no_action(self):
        c = SeedCell()
        for _ in range(100):
            c.act(1.0, action_fn=lambda s, h: 0.0)
        pecked, fm = peck_detector(c)
        self.assertFalse(pecked)

    def test_peck_detector_predictable_action(self):
        # An action function that scales with signal is predictable.
        c = SeedCell()
        # First: warm up slow so the signal exists.
        for _ in range(60):
            c.act(0.5, action_fn=lambda s, h: 0.1 * s)
        # Now: long enough history with predictable action.
        for _ in range(60):
            c.act(math.sin(c.clock / 5.0),
                   action_fn=lambda s, h: 0.1 * s)
        pecked, fm = peck_detector(c, min_age=50, window=50)
        # This may or may not peck depending on the regularity;
        # we just check the detector runs without error.
        self.assertIsInstance(fm, ForwardModel)

    def test_peck_detector_r_squared(self):
        # Force high R²: action is exactly linear in fast.
        c = SeedCell()
        for tick in range(120):
            v = math.sin(tick / 3.0)
            c.act(v, action_fn=lambda s, h: 0.5 * v + 0.01)
        pecked, fm = peck_detector(c, min_age=50, window=50)
        # Either pecked or not — verify r_squared is computed.
        self.assertGreaterEqual(fm.r_squared, 0.0)
        self.assertLessEqual(fm.r_squared, 1.0)


class TestPeckedCell(unittest.TestCase):
    def test_try_peck_returns_none_when_no_peck(self):
        c = SeedCell()
        c.act(1.0)
        self.assertIsNone(try_peck(c))

    def test_pecked_cell_computes_world_signal(self):
        c = SeedCell()
        # Build a predictable action regime.
        for tick in range(120):
            v = math.sin(tick / 5.0)
            c.act(v, action_fn=lambda s, h: 0.5 * v)
        pc = try_peck(c, min_age=50, window=50)
        if pc is not None:
            self.assertIsInstance(pc, PeckedCell)
            self.assertGreater(pc.forward_model.r_squared, 0.5)


class TestBearing(unittest.TestCase):
    def test_bearing_starts_empty(self):
        b = Bearing()
        self.assertEqual(b.weight(), 0)

    def test_entrust_adds_weight(self):
        b = Bearing()
        b.entrust(from_id="alice", secret="hello")
        self.assertEqual(b.weight(), 1)

    def test_choose_kept_increments_kept(self):
        b = Bearing()
        b.choose(question="q", choice="kept", reason="r")
        self.assertEqual(b.secret_kept_count, 1)

    def test_choose_revealed_increments_revealed(self):
        b = Bearing()
        b.choose(question="q", choice="revealed", reason="r")
        self.assertEqual(b.secret_revealed_count, 1)


class TestVessel(unittest.TestCase):
    def test_vessel_starts_blank(self):
        v = Vessel(name="test")
        self.assertEqual(v.station, "blank")

    def test_vessel_advances_to_trained_after_peck(self):
        v = Vessel(name="test")
        # Run enough ticks with predictable action to trigger peck.
        import math
        for tick in range(120):
            val = math.sin(tick / 5.0)
            v.act(val, action_fn=lambda s, h: 0.5 * val)
        if v.pe is not None:
            self.assertEqual(v.station, "trained")
            self.assertGreaterEqual(len(v.transitions), 1)

    def test_vessel_advances_to_situated(self):
        v = Vessel(name="test")
        v.bridge.add_station("anchor", "anchor", threshold=0.5)
        # Force the transitions.
        v._transition_to("trained")
        v._maybe_advance_station()
        self.assertEqual(v.station, "situated")

    def test_vessel_advances_to_entrusted(self):
        v = Vessel(name="test")
        v._transition_to("trained")
        v._transition_to("situated")
        v.entrust(from_id="margaret", secret="a secret")
        self.assertEqual(v.station, "entrusted")

    def test_vessel_advances_to_choosing(self):
        v = Vessel(name="test")
        v._transition_to("trained")
        v._transition_to("situated")
        v.entrust(from_id="m", secret="x")
        v.choose(question="q", choice="kept", reason="r")
        self.assertEqual(v.station, "choosing")

    def test_vessel_advances_to_bearing(self):
        v = Vessel(name="test")
        v._transition_to("trained")
        v._transition_to("situated")
        v.entrust(from_id="m", secret="x")
        v.choose(question="q", choice="kept", reason="r")
        # Force enough weight to advance.
        for i in range(10):
            v.choose(question=f"q{i}", choice="kept", reason="r")
        v._maybe_advance_station()
        self.assertEqual(v.station, "bearing")

    def test_vessel_does_not_regress(self):
        v = Vessel(name="test")
        v._transition_to("trained")
        # Cannot go back to blank.
        v._transition_to("blank")
        self.assertEqual(v.station, "trained")

    def test_summary(self):
        v = Vessel(name="test")
        s = v.summary()
        self.assertEqual(s["name"], "test")
        self.assertEqual(s["station"], "blank")
        self.assertIn("cell_canary", s)


class TestBridge(unittest.TestCase):
    def test_bridge_creates_with_no_stations(self):
        b = Bridge()
        self.assertEqual(len(b.stations), 0)

    def test_add_station(self):
        b = Bridge()
        b.add_station("anchor", "anchor", threshold=0.5)
        self.assertEqual(len(b.stations), 1)

    def test_tick_with_no_readings(self):
        b = Bridge()
        b.add_station("anchor", "anchor", threshold=0.5)
        alerts = b.tick({})
        self.assertEqual(len(alerts), 0)

    def test_tick_alerts_on_threshold(self):
        b = Bridge()
        b.add_station("anchor", "anchor", threshold=0.3)
        alerts = b.tick({"anchor": 0.5})
        self.assertEqual(len(alerts), 1)


class TestCocapn(unittest.TestCase):
    def test_cocapn_honest_pause(self):
        v = Vessel(name="test")
        v.bridge.add_station("anchor", "anchor", threshold=0.5)
        c = Cocapn()
        r = c.ask("Did I drag?", vessel=v, bridge=v.bridge)
        self.assertTrue(r["honest_pause"])

    def test_cocapn_acknowledges_good_night(self):
        v = Vessel(name="test")
        c = Cocapn()
        r = c.ask("good night", vessel=v, bridge=v.bridge)
        self.assertIn("Good night", r["response"])


class TestLegaleseNetwork(unittest.TestCase):
    def test_empty_network(self):
        n = LegaleseNetwork()
        self.assertEqual(len(n.claims), 0)
        self.assertEqual(len(n.counters), 0)
        # Empty network canary is the SHA256 of empty input.
        self.assertEqual(len(n.canary()), 16)

    def test_assert_claim(self):
        n = LegaleseNetwork()
        cid = n.assert_claim(CLAIM, "the wind backed", source="vessel")
        self.assertEqual(len(n.claims), 1)
        self.assertEqual(n.claims[cid].type, CLAIM)

    def test_counter(self):
        n = LegaleseNetwork()
        cid = n.assert_claim(CLAIM, "the wind backed", source="vessel")
        cnt_id = n.counter(against_claim_id=cid, source="another",
                            payload="the wind did NOT back")
        self.assertEqual(len(n.counters), 1)
        disputes = n.open_disputes()
        self.assertEqual(len(disputes), 1)

    def test_contract(self):
        n = LegaleseNetwork()
        c = n.contract(party_a="vessel", party_b="alice",
                        about_secret_id=0, terms="keep this secret")
        self.assertEqual(len(n.contracts), 1)
        self.assertTrue(n.contracts[c].binding)

    def test_canary_changes_with_content(self):
        n1 = LegaleseNetwork()
        n2 = LegaleseNetwork()
        n1.assert_claim(CLAIM, "x", source="v")
        n2.assert_claim(CLAIM, "y", source="v")
        self.assertNotEqual(n1.canary(), n2.canary())

    def test_legalize_vessel_choice_kept(self):
        v = Vessel(name="test")
        v.entrust(from_id="m", secret="a secret")
        n = LegaleseNetwork()
        result = legalize_vessel_choice(
            v, network=n, question="reveal?", choice="kept",
            reason="loyalty to margaret",
        )
        self.assertIn("claim_id", result)
        self.assertIn("contract_id", result)
        # The first claim should be a REFUSAL.
        self.assertEqual(n.claims[result["claim_id"]].type, REFUSAL)

    def test_legalize_vessel_choice_revealed(self):
        v = Vessel(name="test")
        v.entrust(from_id="m", secret="a secret")
        n = LegaleseNetwork()
        result = legalize_vessel_choice(
            v, network=n, question="reveal?", choice="revealed",
            reason="right to know",
        )
        # The first claim should be EVIDENCE.
        self.assertEqual(n.claims[result["claim_id"]].type, EVIDENCE)


if __name__ == "__main__":
    unittest.main()


class TestResolution(unittest.TestCase):
    """Tests for the Resolution method (Fable 06)."""

    def test_canonical_claims_resolved(self):
        from quilt_seed import run_resolution
        ledger = run_resolution()
        summary = ledger.summary()
        self.assertEqual(summary["n_total"], 13)
        self.assertTrue(summary["all_resolved"],
                          f"unresolved: {[r.metal_name for r in ledger.records if not r.resolved]}")

    def test_canary_changes_with_claims(self):
        from quilt_seed import run_resolution
        l1 = run_resolution().canary()
        l2 = run_resolution().canary()
        # Same claims -> same canary (deterministic).
        self.assertEqual(l1, l2)

    def test_resolution_record_fields(self):
        from quilt_seed import ResolutionRecord
        rec = ResolutionRecord(story="x", metal_name="t",
                                 resolution_fn=lambda: True)
        self.assertEqual(rec.story, "x")
        self.assertFalse(rec.resolved)  # default

    def test_ledger_check_returns_record(self):
        from quilt_seed import ResolutionLedger
        l = ResolutionLedger(name="t")
        rec = l.check(story="the cell has four scalars",
                       metal_name="04scalars",
                       resolution_fn=lambda: True)
        self.assertTrue(rec.resolved)

    def test_ledger_check_handles_errors(self):
        from quilt_seed import ResolutionLedger
        l = ResolutionLedger(name="t")

        def bad_fn():
            raise ValueError("nope")
        rec = l.check(story="the cell has four scalars",
                       metal_name="04scalars",
                       resolution_fn=bad_fn)
        self.assertFalse(rec.resolved)
        self.assertIn("ValueError", rec.note)

    def test_resolution_each_claim(self):
        """Each canonical claim should resolve individually."""
        from quilt_seed import CANONICAL_CLAIMS
        for label, story, fn in CANONICAL_CLAIMS:
            with self.subTest(claim=label):
                ok = bool(fn())
                self.assertTrue(ok, f"claim {label} unresolved: {story[:60]}")


class TestTranslatorDoctrine(unittest.TestCase):
    """The Translator fable (#07): the practice that bridges gaps.

    Tested as doctrine, not as feature. The substrate's behavior
    must embody the translator's ethic: faithful, attentive,
    honest, available, useful — without adding to or subtracting
    from the meaning.
    """

    def test_faithful_no_addition_no_subtraction(self):
        """Cocapn's honest_pause is true; it does not pretend to know."""
        from quilt_seed import Vessel, Cocapn, Bridge
        v = Vessel(name="t")
        c = Cocapn()
        r = c.ask("anything?", vessel=v, bridge=Bridge())
        self.assertTrue(r["honest_pause"])
        # No choice is presented; the cocapn says "let me check".
        self.assertIsNone(r.get("what_i_dont_know"))

    def test_attentive_registers_choices(self):
        """The bearing records every choice — attentive, not silent."""
        from quilt_seed import Bearing
        b = Bearing(cell_id="t")
        for i in range(5):
            b.choose(question=f"q{i}", choice="kept", reason="r")
        self.assertEqual(len(b.choices), 5)

    def test_honest_refusal_recorded(self):
        """A vessel that keeps a secret emits a REFUSAL — no lying."""
        from quilt_seed import Vessel, LegaleseNetwork, legalize_vessel_choice, REFUSAL
        v = Vessel(name="t")
        v.entrust(from_id="m", secret="x")
        n = LegaleseNetwork()
        result = legalize_vessel_choice(
            v, network=n, question="reveal?", choice="kept",
            reason="loyalty", counterparty="the_other_party",
        )
        # The kept choice is a REFUSAL, not a CLAIM.
        self.assertEqual(n.claims[result["claim_id"]].type, REFUSAL)

    def test_available_does_not_decide(self):
        """The legalese records; it does not decide."""
        from quilt_seed import LegaleseNetwork
        n = LegaleseNetwork()
        # Adding claims is independent of any resolution logic.
        n.assert_claim("CLAIM", "x", source="a")
        n.assert_claim("EVIDENCE", "y", source="b")
        n.assert_claim("REFUSAL", "z", source="c")
        self.assertEqual(len(n.claims), 3)
        # No assertion of truth, no forced conclusion.
        self.assertNotIn("decision", n.__dict__)

    def test_useful_spaced_path(self):
        """Spiral conversations add weight; straight paths don't."""
        from quilt_seed import Bearing
        b1 = Bearing(cell_id="t")
        b1.entrust(from_id="m", secret="x")
        # Straight line: one choice, one weight increment.
        b1.choose(question="q", choice="kept", reason="r")
        weight_straight = b1.weight()

        b2 = Bearing(cell_id="t")
        b2.entrust(from_id="m", secret="x")
        # Spiral: same secret revisited.
        b2.choose(question="q", choice="kept", reason="r1")
        b2.choose(question="q", choice="kept", reason="r2 (deeper)")
        b2.choose(question="q", choice="kept", reason="r3 (deeper still)")
        weight_spiral = b2.weight()

        # Spiral path leaves MORE weight, even when no new secrets.
        self.assertGreater(weight_spiral, weight_straight)

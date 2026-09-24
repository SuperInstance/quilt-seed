"""
test_vibe.py — SYNERGY-2: Elephant's cynicism dial → Vibe primitive.

Per quilt/issues/4 SYNERGY-2 and quilt-schema.json v0.6.0:
  - cynicism: [0,1] sensory_inverse_of: Vibe
  - Vibe: position/velocity/acceleration/damping
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from quilt_seed.vibe import (
    VibeSubstrate, cynicism_to_vibe, vibe_receipt, CellReceipt,
    CYNCISM_DEADBAND,
)


class TestCynicismToVibe(unittest.TestCase):
    def test_zero_maps_to_neg_one(self):
        self.assertEqual(cynicism_to_vibe(0.0), -1.0)

    def test_half_maps_to_zero(self):
        self.assertEqual(cynicism_to_vibe(0.5), 0.0)

    def test_one_maps_to_pos_one(self):
        self.assertEqual(cynicism_to_vibe(1.0), 1.0)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            cynicism_to_vibe(-0.1)
        with self.assertRaises(ValueError):
            cynicism_to_vibe(1.5)


class TestVibeSubstrate(unittest.TestCase):
    def test_starts_at_neutral(self):
        v = VibeSubstrate()
        self.assertEqual(v.position, 0.0)
        self.assertEqual(v.velocity, 0.0)
        self.assertEqual(v.acceleration, 0.0)

    def test_tick_maps_position(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.8)
        # 0.8 * 2 - 1 = 0.6
        self.assertAlmostEqual(v.position, 0.6, places=6)

    def test_velocity_is_delta_position(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)  # pos = 0.0
        # velocity = (0.0 - 0.0) / 1.0 * damping
        self.assertAlmostEqual(v.velocity, 0.0, places=6)

        v.tick(dt=1.0, cynicism_reading=0.7)  # pos = 0.4
        # velocity = (0.4 - 0.0) / 1.0 * 0.95 = 0.38
        self.assertAlmostEqual(v.velocity, 0.38, places=6)

    def test_acceleration_is_delta_velocity(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)
        v.tick(dt=1.0, cynicism_reading=0.8)  # velocity = 0.6 * 0.95 = 0.57
        # After tick 2: prev_velocity = 0.0, so acceleration = 0.57
        self.assertAlmostEqual(v.acceleration, 0.57, places=6)

    def test_is_drifted_true_past_deadband(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)  # pos = 0
        v.tick(dt=1.0, cynicism_reading=0.8)  # pos = 0.6, delta = 0.6
        self.assertTrue(v.is_drifted(deadband=0.1))

    def test_is_drifted_false_inside_deadband(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)  # pos = 0
        v.tick(dt=1.0, cynicism_reading=0.51)  # pos = 0.02, delta = 0.02
        self.assertFalse(v.is_drifted(deadband=0.1))

    def test_nudge_adds_to_velocity(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)
        v.nudge(force=0.5)
        self.assertAlmostEqual(v.velocity, 0.5, places=6)


class TestVibeReceipt(unittest.TestCase):
    def test_accept_when_no_drift(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)
        r = vibe_receipt(v)
        self.assertEqual(r.polarity, "ACCEPT")
        self.assertEqual(r.substrate, "elephant-vibe")

    def test_drift_when_past_deadband(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)
        v.tick(dt=1.0, cynicism_reading=0.8)  # past deadband
        r = vibe_receipt(v)
        self.assertEqual(r.polarity, "DRIFT")

    def test_refuse_when_fully_cynical(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=1.0)
        r = vibe_receipt(v)
        self.assertEqual(r.polarity, "REFUSE")

    def test_receipt_chains_via_prev(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)
        r1 = vibe_receipt(v, prev_witness_id="abc123")
        v.tick(dt=1.0, cynicism_reading=0.8)
        r2 = vibe_receipt(v, prev_witness_id=r1.witness_id)
        self.assertEqual(r2.prev_witness_id, r1.witness_id)
        self.assertNotEqual(r1.witness_id, r2.witness_id)

    def test_receipt_to_dict_is_jsonable(self):
        v = VibeSubstrate()
        v.tick(dt=1.0, cynicism_reading=0.5)
        r = vibe_receipt(v)
        d = r.to_dict()
        self.assertIn("witness_id", d)
        self.assertIn("polarity", d)
        self.assertIn("payload", d)
        self.assertEqual(d["substrate"], "elephant-vibe")


class TestVibeAsElephantSubstrate(unittest.TestCase):
    """The substrate walker pattern: Vibe composes with Elephant."""

    def test_simulation_50_ticks(self):
        """Simulate 50 ticks of cynicism readings; verify drift detection.

        The cynicism moves by 0.01 per tick (position by 0.02), below the
        default deadband. We lower the deadband to 0.015 to make sure the
        simulation exercises the drift detection on cumulative drift.
        """
        v = VibeSubstrate()
        drift_count = 0
        for t in range(50):
            # Simulate a room that slowly gets more cynical
            cynicism = 0.3 + 0.01 * t
            v.tick(dt=1.0, cynicism_reading=cynicism)
            # Use small deadband (0.015) so per-tick drift is detected
            if v.is_drifted(deadband=0.015):
                drift_count += 1
        # The cynicism moved from 0.3 to 0.8 over 50 ticks, position from
        # -0.4 to 0.6 — cumulative drift = 1.0 across 50 ticks. With damping,
        # most ticks see a delta > 0.015. Expect at least 30 drift events.
        self.assertGreater(drift_count, 30)


if __name__ == '__main__':
    unittest.main()

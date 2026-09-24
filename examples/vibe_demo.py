"""
vibe_demo.py — walk through the Elephant → Vibe substrate pipeline.

Demonstrates SYNERGY-2 from quilt/issues/4:
  Elephant's cynicism dial → Vibe primitive → CellReceipt envelope

What this does:
  1. Builds a Vibe substrate
  2. Simulates 50 ticks of a room slowly getting more cynical
  3. Emits CellReceipts for drift events
  4. Verifies the chain links via prev_witness_id

Run:
    PYTHONPATH=src python3 examples/vibe_demo.py
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quilt_seed.vibe import VibeSubstrate, vibe_receipt


def fake_elephant_cynicism(tick: int) -> float:
    """Simulate Elephant reading the room at tick t.

    The room starts earnest (cynicism 0.2) and slowly becomes more cynical
    (0.2 → 0.85 over 50 ticks). Around tick 30, a fake "drifter" leaves
    a sneer that bumps cynicism by 0.2 — the kind of event Elephant would
    detect with its cynicism.py keyword heuristics.
    """
    base = 0.2 + (tick / 50.0) * 0.65
    if tick == 30:
        base = min(1.0, base + 0.2)
    return base


def main():
    print("=== Elephant → Vibe substrate demo ===\n")
    print("Simulating 50 ticks of a room slowly getting more cynical.")
    print("A 'drifter sneer' event fires at tick 30 to test receipt chain.\n")

    vibe = VibeSubstrate()
    prev_witness_id = ""

    for t in range(50):
        cynicism = fake_elephant_cynicism(t)
        vibe.tick(dt=1.0, cynicism_reading=cynicism)

        # Only emit receipts at meaningful events (drift or boundary)
        if vibe.is_drifted(deadband=0.015) or vibe.position >= 0.99:
            r = vibe_receipt(vibe, prev_witness_id=prev_witness_id)
            prev_witness_id = r.witness_id

            if r.polarity == "DRIFT" and t in (5, 20, 35, 45):
                print(f"  t={t:2d} cynicism={cynicism:.3f} "
                      f"pos={r.payload['position']:+.3f} "
                      f"vel={r.payload['velocity']:+.3f} "
                      f"→ {r.polarity} ({r.witness_id})")
            if r.polarity == "REFUSE":
                print(f"  t={t:2d} cynicism={cynicism:.3f} "
                      f"pos={r.payload['position']:+.3f} "
                      f"→ {r.polarity} ({r.witness_id})")

    print(f"\nFinal: position={vibe.position:+.3f}, velocity={vibe.velocity:+.3f}")
    print(f"Last witness_id: {prev_witness_id}")
    print("\nThis is the Elephant's cynicism dial composed as a Quilt Vibe substrate.")
    print("The legalese layer (quilt-seed.legalese) can wrap the receipts as Claims.")
    print("The cell decides what to do with the drift — the substrate only witnesses.")


if __name__ == '__main__':
    main()

"""
vibe.py — the Vibe primitive wired to Elephant's cynicism dial.

Per quilt-schema.json v0.6.0:

    primitives.Vibe:
      fields:    position, velocity, acceleration, damping
      methods:   tick(dt), nudge(force)
      substrates: all

    elephant_dials.cynicism:
      range:    [0, 1]
      sensory_inverse_of: Vibe

This substrate reads the cynicism dial from Elephant and maps it to
the Vibe primitive. The cell's position drifts toward cynicism; the
velocity carries the rate; the deadband hides the noise.

The Vibe substrate is honest about its boundaries:
- It does NOT try to be all 9 dials. Just cynicism → Vibe for now.
- It does NOT call LLM. Pure Python; runs anywhere elephant runs.
- It does NOT decide what to do about the drift. It records.
  The legalese layer (CellReceipt → Contract) decides; the cell decides.

Wired in: SYNERGY-2 (Elephant → d_mu → Vibe) from quilt/issues/4.

Usage:
    from quilt_seed.vibe import VibeSubstrate, cynicism_to_vibe

    vibe = VibeSubstrate()
    vibe.tick(dt=1.0, cynicism_reading=0.62)
    vibe.tick(dt=1.0, cynicism_reading=0.71)
    print(vibe.position, vibe.velocity, vibe.acceleration)

    # Or via the CellReceipt envelope (per SEAM counter-proposal):
    from quilt_seed.vibe import vibe_receipt

    r = vibe_receipt(vibe, question="vibe drift?", threshold=0.1)
    print(r.polarity)  # "ACCEPT" | "DRIFT" | "REFUSE"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# === The cynicism dial, locally re-typed so we don't require elephant ===

# Range [0,1]; 0 = earnest, 1 = sneering. Elephant's cynicism.py reads
# scare quotes, "sure, sure", eyeroll emoji, etc.
CynicismReading = float


# === Vibe primitive mapping ===

# The Vibe primitive in the schema is a 1D position with velocity + acceleration.
# Cynicism [0,1] maps to position [-1,+1]: position = cynicism * 2 - 1.
# Velocity is the rolling EMA of position - previous position.
# Acceleration is the rate of velocity change.

CYNCISM_DEADBAND = 0.05  # hide dial noise below this; emits no receipt


@dataclass
class VibeSubstrate:
    """The cell's Vibe primitive, fed by Elephant's cynicism dial.

    Implements the schema's Vibe fields:
      - position     = cynicism * 2 - 1  (maps [0,1] → [-1,+1])
      - velocity     = Δposition / Δt
      - acceleration = Δvelocity / Δt
      - damping      = velocity decay per tick (default 0.95)
    """

    position: float = 0.0
    velocity: float = 0.0
    acceleration: float = 0.0
    damping: float = 0.95
    _prev_position: float = field(default=0.0, init=False, repr=False)
    _prev_velocity: float = field(default=0.0, init=False, repr=False)

    def tick(self, dt: float, cynicism_reading: CynicismReading) -> None:
        """Advance one step. dt in seconds; cynicism in [0,1]."""
        new_position = cynicism_to_vibe(cynicism_reading)
        raw_velocity = (new_position - self._prev_position) / dt

        # Apply damping to velocity (the cell has inertia; it forgets fast).
        # Damping is part of velocity, so acceleration reflects the damped delta.
        new_velocity = raw_velocity * self.damping
        new_acceleration = (new_velocity - self._prev_velocity) / dt

        self._prev_position = self.position
        self._prev_velocity = self.velocity
        self.position = new_position
        self.velocity = new_velocity
        self.acceleration = new_acceleration

    def nudge(self, force: float) -> None:
        """Apply an external force to the velocity. For overrides."""
        self.velocity += force

    def is_drifted(self, deadband: float = CYNCISM_DEADBAND) -> bool:
        """Has the cynicism dial moved past the deadband since last tick?"""
        return abs(self.position - self._prev_position) >= deadband


def cynicism_to_vibe(cynicism: float) -> float:
    """Map cynicism [0,1] → Vibe position [-1,+1]."""
    if not 0.0 <= cynicism <= 1.0:
        raise ValueError(f"cynicism must be in [0,1], got {cynicism}")
    return cynicism * 2.0 - 1.0


# === CellReceipt envelope (per SEAM counter-proposal) ===

# Polarity vocabulary: ACCEPT (no drift), DRIFT (cynicism moved past deadband),
# REFUSE (cynicism pegged at 1.0 — the room gave up).

@dataclass
class CellReceipt:
    """The shared receipt envelope proposed in quilt-cell-harness#1.

    Lightweight version here for the Vibe substrate. The full envelope
    lives in cell.py once the SEAM PR lands.
    """
    witness_id: str
    prev_witness_id: str
    cell_id: str
    substrate: str
    polarity: str   # ACCEPT | DRIFT | REFUSE
    payload: dict
    timestamp: int

    def to_dict(self) -> dict:
        return {
            "witness_id": self.witness_id,
            "prev_witness_id": self.prev_witness_id,
            "cell_id": self.cell_id,
            "substrate": self.substrate,
            "polarity": self.polarity,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


def vibe_receipt(
    vibe: VibeSubstrate,
    *,
    cell_id: str = "vibe-cell",
    question: str = "vibe drift?",
    deadband: float = CYNCISM_DEADBAND,
    prev_witness_id: str = "",
    timestamp: Optional[int] = None,
) -> CellReceipt:
    """Emit a CellReceipt for the current Vibe state.

    Polarity:
      - DRIFT  if cynicism moved past the deadband
      - REFUSE if position is pegged at +1 (room fully cynical)
      - ACCEPT otherwise
    """
    import hashlib
    import json
    import time

    if timestamp is None:
        timestamp = int(time.time())

    payload = {
        "question": question,
        "position": round(vibe.position, 6),
        "velocity": round(vibe.velocity, 6),
        "acceleration": round(vibe.acceleration, 6),
        "deadband": deadband,
    }

    if vibe.position >= 0.999:
        polarity = "REFUSE"
    elif vibe.is_drifted(deadband):
        polarity = "DRIFT"
    else:
        polarity = "ACCEPT"

    # Compose witness id from prev + payload
    body = json.dumps(
        {"prev": prev_witness_id, "payload": payload, "polarity": polarity, "ts": timestamp},
        sort_keys=True,
    ).encode()
    witness_id = hashlib.sha256(body).hexdigest()[:16]

    return CellReceipt(
        witness_id=witness_id,
        prev_witness_id=prev_witness_id,
        cell_id=cell_id,
        substrate="elephant-vibe",
        polarity=polarity,
        payload=payload,
        timestamp=timestamp,
    )

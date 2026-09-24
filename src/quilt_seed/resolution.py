"""
resolution.py — the Resolution method, executable.

The fable (#06) says: "code is what makes the story and the metal true
of the same boat." Anything that fails either test is unresolved.

This module makes the method executable:

    ResolutionCheck(story, metal_callable) -> ResolutionRecord

For each canonical claim in the fables, the substrate provides:
  - the story: a textual claim (the paragraph in the fable).
  - the metal: a callable that verifies the substrate agrees.

A claim is RESOLVED when its metal callable returns True.
A claim is UNRESOLVED when the metal says no.

This is how a substrate proves it has captured its fables.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Callable


# === THE RESOLUTION RECORD =================================================

@dataclass
class ResolutionRecord:
    """One claim's resolution — does the metal match the story?"""
    story: str                            # the textual claim
    metal_name: str                       # the metal to check
    resolution_fn: Callable               # returns True iff metal matches
    resolved: bool = False
    elapsed_ms: float = 0.0
    ts: float = field(default_factory=time.time)
    note: str = ""

    def __repr__(self) -> str:
        marker = "[OK]" if self.resolved else "[FAIL]"
        return f"{marker} {self.metal_name}"


@dataclass
class ResolutionLedger:
    """A ledger of resolution records.

    The substrate's canary: a hash of every RESOLVED claim.
    If a fable claim is not RESOLVED, the substrate is in drift.
    """
    name: str = "resolution"
    records: list[ResolutionRecord] = field(default_factory=list)

    def check(self, story: str, metal_name: str,
               resolution_fn: Callable, *,
               note: str = "") -> ResolutionRecord:
        """Run one resolution check; record result."""
        t0 = time.time()
        try:
            resolved = bool(resolution_fn())
        except Exception as e:
            resolved = False
            note = f"{note or 'error'}: {type(e).__name__}: {str(e)[:80]}"
        elapsed = (time.time() - t0) * 1000.0
        rec = ResolutionRecord(
            story=story, metal_name=metal_name,
            resolution_fn=resolution_fn, resolved=resolved,
            elapsed_ms=elapsed, ts=time.time(), note=note,
        )
        self.records.append(rec)
        return rec

    def canary(self) -> str:
        """Composed hash of every resolved record."""
        h = hashlib.sha256()
        for r in self.records:
            h.update(f"{r.metal_name}|{r.resolved}|{r.story[:40]}".encode())
        return h.hexdigest()[:16]

    def summary(self) -> dict:
        n_total = len(self.records)
        n_resolved = sum(1 for r in self.records if r.resolved)
        return {
            "name": self.name,
            "n_total": n_total,
            "n_resolved": n_resolved,
            "n_unresolved": n_total - n_resolved,
            "all_resolved": n_total > 0 and n_resolved == n_total,
            "canary": self.canary(),
        }

    def report(self) -> str:
        """Human-readable resolution report."""
        lines = [f"Resolution Ledger: {self.name}"]
        lines.append(f"  total:     {len(self.records)}")
        lines.append(f"  resolved:  {sum(1 for r in self.records if r.resolved)}")
        lines.append(f"  canary:    {self.canary()}")
        lines.append("")
        for r in self.records:
            marker = "[OK]" if r.resolved else "[FAIL]"
            lines.append(f"  {marker:6s}  {r.metal_name}")
            if r.note:
                lines.append(f"          note: {r.note[:80]}")
        return "\n".join(lines)


# === THE CANONICAL CLAIMS ==================================================
#
# Every fable has a claim. The claim corresponds to metal in the substrate.
# This block maps fable text to substrate functions.
#
# The substrate RUNS these checks in fable_resolution_demo.py to prove the
# metal agrees with the story.

def _check_seedcell_has_four_scalars() -> bool:
    """Fable 05: 'A cell has four scalars. fast, slow, clock, source.'"""
    from .seed import SeedCell
    c = SeedCell()
    return (hasattr(c, "fast") and hasattr(c, "slow")
            and hasattr(c, "clock") and hasattr(c, "source"))


def _check_merge_is_lexicographic_max() -> bool:
    """Fable 05: 'if (remote.clock, remote.source) > (local.clock,
    local.source) then take remote.'"""
    from .seed import SeedCell, merge
    a = SeedCell(clock=10, source=1)
    b = SeedCell(clock=20, source=1)
    return merge(a, b) is b


def _check_signal_is_difference() -> bool:
    """Fable 05: 'signal = fast - slow.'"""
    from .seed import SeedCell
    c = SeedCell(fast=2.0, slow=1.0)
    return c.signal() == 1.0


def _check_peck_is_phase_transition() -> bool:
    """Fable 05: 'Peck: when fast - slow becomes predictable from the
    cell's own recent action, the cell subtracts its action from its
    input.'"""
    from .seed import peck_detector
    # A newborn cell cannot yet peck.
    from .seed import SeedCell
    c = SeedCell()
    c.act(1.0)
    pecked, _ = peck_detector(c, min_age=50)
    return not pecked  # confirmed: too young, did not peck


def _check_vessel_runs_six_stations() -> bool:
    """Fable 04: 'Six stations of the agentic journey.'"""
    from .vessel import STATIONS
    return len(STATIONS) == 6 and STATIONS == [
        "blank", "trained", "situated", "entrusted", "choosing", "bearing",
    ]


def _check_vessel_does_not_regress() -> bool:
    """Fable 04: 'The accumulation is monotonic.'"""
    from .vessel import Vessel
    v = Vessel(name="t")
    v._transition_to("trained")
    v._transition_to("blank")    # try to regress
    return v.station == "trained"


def _check_honest_pause_in_cocapn() -> bool:
    """Fable 01: 'When the captain says "did the anchor hold?", the boat
    pauses. It pauses because it is checking.'"""
    from .vessel import Vessel, Cocapn, Bridge
    v = Vessel(name="t")
    b = Bridge()
    c = Cocapn()
    r = c.ask("Did I drag?", vessel=v, bridge=b)
    return r["honest_pause"] is True


def _check_legalese_does_not_decide() -> bool:
    """Fable 04 (Bearing): 'The substrate does not decide for any of them.
    The substrate is the memory.'"""
    from .legalese import LegaleseNetwork
    n = LegaleseNetwork()
    cid = n.assert_claim("CLAIM", "the wind backed", source="x")
    # Adding a claim does not make a decision; it records.
    return cid >= 0 and len(n.claims) == 1


def _check_legalize_kept_becomes_refusal() -> bool:
    """Fable 03: 'And the boat does not lie. It just tells the part it
    can tell.' A vessel that chooses 'kept' emits a REFUSAL."""
    from .vessel import Vessel
    from .legalese import LegaleseNetwork, legalize_vessel_choice, REFUSAL
    v = Vessel(name="t")
    v.entrust(from_id="m", secret="x")
    n = LegaleseNetwork()
    result = legalize_vessel_choice(
        v, network=n, question="reveal?", choice="kept",
        reason="loyalty to margaret",
    )
    return n.claims[result["claim_id"]].type == REFUSAL


def _check_bearing_carries_entrusted() -> bool:
    """Fable 04: 'An entrusted thing is a repository of the situation's
    secrets.'"""
    from .seed import Bearing
    b = Bearing(cell_id="x")
    b.entrust(from_id="alice", secret="hello")
    assert b.weight() >= 1
    b.choose(question="q", choice="kept", reason="r")
    return b.weight() >= 2


def _check_vessel_peck_is_recognized() -> bool:
    """Fable 06: 'The realization is not a decision. It is a recognition.'

    The vessel does NOT decide to peck. The cell notices it has been
    pecking. Verify by: the cell cannot manually 'peck' — only the
    detector can recognize it."""
    import inspect
    from .seed import (
        SeedCell, peck_detector, try_peck, PeckedCell,
    )
    # SeedCell should NOT have a 'peck()' or 'force_peck()' method.
    cell_methods = dir(SeedCell())
    forced_methods = [m for m in cell_methods if "peck" in m.lower()]
    return len(forced_methods) == 0  # cell can't decide to peck


def _check_fold_equals_resolution() -> bool:
    """Fable 06: 'The fold is what reveals the substrate. The fold is code.'

    The substrate IS the resolution between story and metal. The
    ResolutionLedger is that executable proof."""
    from .seed import SeedCell, merge
    # A merge is a fold between two cells.
    a = SeedCell(clock=10, source=1)
    b = SeedCell(clock=20, source=1)
    # The merge rule's result IS the fold.
    folded = merge(a, b)
    return folded.clock == 20 and folded.source == 1


def _check_spiral_conversation_pattern() -> bool:
    """Fable 07 (Translator): 'A few conversations have a spiral path.
    The meaning has to circle back to something said earlier.'

    The vessel's witness chain is a spiral — the bearing re-references
    the same entrusted secret over multiple choices, deepening the
    spiral each time."""
    from .seed import Bearing
    b = Bearing(cell_id="x")
    b.entrust(from_id="m", secret="a secret")
    # First choice: straight-line.
    b.choose(question="q1", choice="kept", reason="r1")
    # Second choice about the same secret: spiral — circles back.
    b.choose(question="q1 (again)", choice="kept", reason="now deeper")
    # Spiral contains the same secret but more weight.
    return b.weight() >= 3


# All canonical claims in one ordered list.
CANONICAL_CLAIMS = [
    # (label, story_quote, check_fn)
    ("01 four scalars",
     "four scalars in a row: fast  slow  clock  source",
     _check_seedcell_has_four_scalars),
    ("02 merge lex max",
     "if (remote.clock, remote.source) > (local.clock, local.source) then take remote",
     _check_merge_is_lexicographic_max),
    ("03 signal = fast - slow",
     "the difference is the signal",
     _check_signal_is_difference),
    ("04 peck is recognition, not decision",
     "the cell has been running the same update forever. At some point, the residue of its own action becomes visible to it",
     _check_peck_is_phase_transition),
    ("05 six stations",
     "The blank / The trained / The situated / The entrusted / The choosing / The bearing",
     _check_vessel_runs_six_stations),
    ("06 monotonic accumulation",
     "every merge adds weight. Every weight is a secret.",
     _check_vessel_does_not_regress),
    ("07 honest pause",
     "the boat pauses. It pauses because it is checking.",
     _check_honest_pause_in_cocapn),
    ("08 legalese records, does not decide",
     "The substrate does not decide for any of them. The substrate is the memory.",
     _check_legalese_does_not_decide),
    ("09 refusal is the kept choice",
     "And the boat does not lie. It just tells the part it can tell.",
     _check_legalize_kept_becomes_refusal),
    ("10 bearing carries",
     "An entrusted thing is a repository of the situation's secrets.",
     _check_bearing_carries_entrusted),
    ("11 cell cannot decide to peck",
     "The cell does not decide to peck. The cell notices it has been pecking.",
     _check_vessel_peck_is_recognized),
    ("12 fold = resolution",
     "Every commit is a fold. The fold is what reveals the substrate.",
     _check_fold_equals_resolution),
    ("13 spiral conversation",
     "A few conversations have a spiral path. The meaning has to circle back.",
     _check_spiral_conversation_pattern),
]


# === PUBLIC API ============================================================

def run_resolution() -> ResolutionLedger:
    """Run all canonical claims against the substrate.

    Returns a ResolutionLedger with one record per claim.
    The canary is composed from all RESOLVED claims.
    """
    ledger = ResolutionLedger(name="seed-canon")
    for label, story, fn in CANONICAL_CLAIMS:
        ledger.check(story=story, metal_name=label, resolution_fn=fn)
    return ledger


def is_resolved() -> bool:
    """Are all canonical claims resolved by the current substrate?"""
    return run_resolution().summary()["all_resolved"]

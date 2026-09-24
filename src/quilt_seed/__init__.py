"""quilt-seed — the four-scalar genome + the vessel + the bearing.

This is the substrate layer where:

  - Bedrock math lives: SeedCell (four scalars), merge, peck.
  - The vessel lives: bounded thing that runs the genome.
  - The bearing lives: weight of entrusted secrets and choices.
  - The bridge lives: agents at stations, honest pause.
  - The cocapn lives: front door that composes answers.
  - The legalese lives: contract-bound governance.
  - The resolution lives: the executable proof that the metal agrees
    with the story.

The seven fables (Captain, Remembers, Entrusted, Bearing, Seed,
Resolution, Translator) are the narrative layer. This module is the
resolution between story and metal.
"""
from .seed import (
    SeedCell, merge, mergeable,
    peck_detector, try_peck, ForwardModel,
    PeckedCell, Bearing,
)
from .vessel import (
    STATIONS,
    BridgeStation, Bridge, Cocapn, Vessel,
)
from .legalese import (
    LegaleseNetwork, Claim, Counter, Contract,
    QUESTION, CLAIM, EVIDENCE, REFUSAL,
    legalize_vessel_choice,
)
from .vibe import (
    VibeSubstrate, cynicism_to_vibe, vibe_receipt, CellReceipt,
    CYNCISM_DEADBAND,
)
from .cu_substrate import (
    CUSubstrate, MockCUBackend, CUWorkerBackend, MemoryHit,
)
from .resolution import (
    ResolutionRecord, ResolutionLedger,
    CANONICAL_CLAIMS, run_resolution, is_resolved,
)


__version__ = "0.2.0"
__all__ = [
    # Seed
    "SeedCell", "merge", "mergeable",
    "peck_detector", "try_peck", "ForwardModel",
    "PeckedCell", "Bearing",
    # Vessel + Bridge + Cocapn
    "STATIONS",
    "BridgeStation", "Bridge", "Cocapn", "Vessel",
    # Legalese — contract-bound governance between cellular agreements
    "LegaleseNetwork", "Claim", "Counter", "Contract",
    "QUESTION", "CLAIM", "EVIDENCE", "REFUSAL",
    "legalize_vessel_choice",
    # Resolution — the executable proof that metal agrees with story
    "ResolutionRecord", "ResolutionLedger",
    "CANONICAL_CLAIMS", "run_resolution", "is_resolved",
]

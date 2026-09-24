# quilt-seed — SKILLS

> Every skill Mavis developed while building quilt-seed, with examples and lessons learned.

## 1. The four-scalar genome

**Skill**: A cell has 4 scalars (fast, slow, clock, source) + 2 regulators (merge, peck).

**Lesson**: The genome is closed. You can add regulators but not scalars. fast reacts; slow remembers (EMA, α=0.1); signal = fast - slow; action = f(signal); loop runs forever. Don't try to add a "mood" scalar — make mood a *substrate* that reads the dials.

**Example**: `SeedCell(fast=0.0, slow=0.0, clock=0, source="alice")`.

## 2. Peck is recognition, not decision

**Skill**: The cell's "I know the difference between what I did and what happened" emerges when its action's effect on `fast` becomes *predictable* (R² ≥ 0.5 over 50 ticks). The cell has inside/outside AFTER the peck, not because we forced it.

**Lesson**: There is no `cell.force_peck()` method. Only `peck_detector()` and `try_peck()` can recognize it. If you find yourself wanting to force a phase transition, you're probably missing the substrate that should have provided the experience.

**Example**: 50 ticks of `c.act(input)` with `action_fn = lambda s, h: 0.5 * math.sin(c.clock / 5.0)` → pecks at clock=79 with R²=0.526.

## 3. Stations emerge; they are not chosen

**Skill**: A vessel's six stations (blank → trained → situated → entrusted → choosing → bearing) advance when conditions hold, not when an external system pushes them.

**Lesson**: `vessel.station` is a property; `vessel._maybe_advance_station()` is a method called after every state change. There is no `vessel.set_station("bearing")`. The vessel notices that it's been entrusted, that it has made choices, that its bearing has weight.

**Example**: `v.entrust(...)` doesn't set station to "entrusted" — it appends to bearing and the next tick checks if weight > 0 and station advances.

## 4. Legalese records, doesn't decide

**Skill**: `LegaleseNetwork.claims` is a list; `legalize_vessel_choice()` adds to it. Nothing reads the claims and decides what the vessel does.

**Lesson**: The vessel decides (its `choose()` method is sovereign). The legalese layer witnesses the decision. If you want the vessel to refuse based on past choices, the refusal comes from a contract — not from the legalese layer.

**Example**: `legalize_vessel_choice(v, network=n, choice="kept")` adds a REFUSAL claim and a binding Contract. The vessel does NOT change behavior based on the claim; the contract is the binding.

## 5. The Resolution method

**Skill**: Code is the resolution between story and metal. 13 canonical claims verify the metal agrees with the story.

**Lesson**: If a fable says "the four scalars are closed" and the code exposes a fifth scalar, the ResolutionLedger flags it. The bug is in the resolution, not the code.

**Example**: `is_resolved() → True` for all 13 claims. Canary: `927d98c135a83f75`. If you add a new fable, add a new claim.

## 6. The substrate walker pattern

**Skill**: When a fleet has multiple substrates that emit receipts (Elephant, Collective Unconscious, Hermes, moth-*), the walker composes them into cells.

**Lesson**: Don't make the cell know about the substrates. Make the substrate wrapper know about the cell. The substrate (elephant/cu/hermes) emits; the wrapper (`vibe.py`, `cu_substrate.py`) translates to a CellReceipt; the legalese layer witnesses; the cell decides.

**Example**: SYNERGY-2 (199 lines) and SYNERGY-3 (199 lines) in this repo are the substrate walker pattern.

## 7. Honest about boundaries

**Skill**: Each substrate wrapper has a "what this doesn't do" section.

**Lesson**: `vibe.py` doesn't import Elephant (uses `CynicismReading = float`). `cu_substrate.py` doesn't call the deployed Worker (uses `MockCUBackend`). The substrate walker composes without coupling.

**Example**: A new agent can use `MockCUBackend` for tests, `CUWorkerBackend(url=...)` for production. The cell code doesn't change.

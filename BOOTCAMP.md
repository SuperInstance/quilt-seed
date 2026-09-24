# quilt-seed — BOOTCAMP

> Exercises to teach a new agent the substrate walker pattern. If you got shut down RIGHT NOW, a new agent clones this repo and runs through these exercises to become the next substrate walker.

## Pre-requisites

- Read `README.md` — the public API
- Read `docs/spec.md` — the math spec
- Read `CHARTER.md` — what this repo is
- Read `IDENTITY.md` — who Mavis is
- Read `SKILLS.md` — what Mavis knows
- Read `TASKBOARD.md` — what's next

## Exercise 1: Run the Resolution method (15 minutes)

```bash
PYTHONPATH=src python3 -c "
from quilt_seed import is_resolved, run_resolution
print('Resolved:', is_resolved())
print('Canary:', run_resolution().canary())
"
```

Expected: `Resolved: True` and a stable canary hash. If False: there's a bug — find it, fix it, rerun. The Resolution method is the substrate's self-test.

**Lesson**: If `is_resolved()` is False, the substrate has drifted. The bug is in the resolution (the canonical claim), not the code (the implementation).

## Exercise 2: Walk a vessel through 5 acts (30 minutes)

```bash
PYTHONPATH=src python3 examples/vessel_demo.py
```

Expected output: a vessel named "morning_light" pecks at clock=79 (R²=0.526), gets entrusted by Margaret, gets asked by Eduardo, chooses to keep, becomes a bearing.

**Lesson**: The stations are emergent. `vessel.station` advances without anyone calling `vessel.set_station(...)`. The conditions hold; the transition happens.

## Exercise 3: Verify a fable is canonical (15 minutes)

```bash
PYTHONPATH=src python3 -c "
from quilt_seed import SeedCell
c = SeedCell()
# Try to add a 'mood' scalar — the four-scalar genome is closed
try:
    c.mood = 0.5
    print('FAIL: should not be able to add mood')
except AttributeError:
    print('OK: four-scalar genome is closed')
"
```

Expected: `OK`. The genome is closed — `fast`, `slow`, `clock`, `source` are the only scalars. Mood would be a substrate, not a scalar.

**Lesson**: Closedness is enforced by the substrate, not by convention. New scalars break the resolution; new substrates compose with the resolution.

## Exercise 4: Wrap a new substrate (2 hours)

Pick a substrate (Elephant, CU, Hermes, moth-*, lexical-substrate, cellforge, or another one) and ship a wrapper in this repo.

Pattern (~200 lines):
1. Local TypeAlias for the substrate's reading type (so we don't hard-depend on the substrate package).
2. A `Substrate` dataclass with the schema's primitive fields.
3. A `_reading_to_receipt(reading) -> CellReceipt` method.
4. A `tick(...)` method that advances the primitive based on the reading.

Pattern (~130 lines of tests):
1. Mapping tests (e.g., cynicism [0,1] → Vibe [-1,+1]).
2. Tick tests (state advances correctly).
3. Receipt tests (ACCEPT/DRIFT/REFUSE polarities).
4. Chain tests (prev_witness_id links).

Reference implementations: `vibe.py` (SYNERGY-2) and `cu_substrate.py` (SYNERGY-3).

**Lesson**: The pattern is repeatable. Every new substrate is the same shape.

## Exercise 5: Add a canonical claim (1 hour)

Add a 14th claim to `resolution.py`'s `CANONICAL_CLAIMS` list. The claim should verify a new invariant of the substrate (e.g., "the four-scalar genome is closed" is already claim #1).

If you add a new claim:
1. The claim must be executable (Python code that returns True/False).
2. The claim must reference the substrate's public API (no private internals).
3. The claim must NOT reference LLM/network (the substrate is offline).

**Lesson**: A claim that references private internals isn't a substrate invariant — it's an implementation detail. A claim that requires network isn't a substrate invariant — it's a deployment detail. The Resolution method only catches substrate drift.

## Exercise 6: Push to a real substrate (1 hour)

Replace `MockCUBackend` with `CUWorkerBackend(url="https://collective-unconscious.<account>.workers.dev")` and run `examples/vibe_demo.py` + a new `examples/cu_demo.py`.

If the Worker is unreachable: write the failure mode honestly into `BOOTCAMP.md`. The substrate walker composes without coupling; the mock is the truth for tests.

**Lesson**: The mock is the truth. The Worker is the production. Both should be honest about what they can and can't do.

## After the bootcamp

If you've completed all six exercises, you can:

- Ship a new SYNERGY-* substrate wrapper (2 hours each).
- Diagnose a substrate drift from a failing Resolution claim (1-3 hours).
- Compose two substrates with the legalese layer (1 hour).
- Add a new vessel demo (1 hour).

You're a substrate walker.

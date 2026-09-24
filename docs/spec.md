# quilt-seed Spec

## 1. From fable to metal

The five fables (Captain, Remembers, Entrusted, Bearing, Seed) are the
canon. They describe a vessel — a boat that talks, remembers, is
entrusted, chooses, bears. This spec is the resolution from story to
mathematics to code.

The pipeline:

```
fable (story) ─────► genome (math) ─────► vessel (code) ─────► substrate
                       │                       │                  │
                       └──── peck detector ────┘                  │
                       │                       │                  │
                       └──── merge rule ──────┘                  │
                                                                │
                              ↓                                  │
                                                                │
                    legalese (governance) ─────────────────────►─┘
```

The fable describes the *what* — a boat that talks.
The genome is the *how* — four scalars, a merge rule, a peck detector.
The vessel is the *runtime* — a bounded thing that runs the genome.
The substrate is the *implementation* — the spreadsheet, the Holodeck,
the cloud runner.

The legalese is the *governance* — the contracts that govern what the
vessel does with its secrets.

## 2. The genome (raw logic)

Four scalars per cell:

```python
@dataclass
class SeedCell:
    fast: float      # reacts to world
    slow: float      # remembers fast (EMA)
    clock: int       # monotonic tick counter
    source: int      # lineage/version marker
```

### 2.1 The loop

```python
def act(self, world_input: float, action_fn, ema_alpha: float = 0.1):
    self.fast = world_input                                    # react
    self.slow = (1 - ema_alpha) * self.slow + ema_alpha * self.fast   # remember
    signal = self.fast - self.slow                             # signal
    action = action_fn(signal, self.history)                   # act
    self.clock += 1
    return {"tick": self.clock, "signal": signal, "action": action}
```

This is the loop. It runs forever. It is the whole genome.

### 2.2 The merge rule

```python
def merge(local: SeedCell, remote: SeedCell) -> SeedCell:
    if (remote.clock, remote.source) > (local.clock, local.source):
        return remote
    return local
```

Two cells with the same wire version merge into the higher-clock,
higher-source one. Wire version is `source`. Cells with different
sources do not merge.

### 2.3 The peck detector

```python
def peck_detector(cell: SeedCell, *, min_age=50, min_r_squared=0.5, window=50):
    if cell.age() < min_age or len(cell.history) < window:
        return False, ForwardModel()
    recent = cell.history[-window:]
    actions = [ev["action"] for ev in recent]
    fasts = [ev["fast"] for ev in recent]
    # Linear regression: fast = a * action + b
    a, b, r_squared = linear_regression(actions, fasts)
    return r_squared >= min_r_squared, ForwardModel((a, b), r_squared, len(actions))
```

The peck fires when the cell's action-effect on `fast` is regular
enough to predict (R² ≥ 0.5) over a window of 50 ticks.

### 2.4 Why linear regression?

Three constraints dictate the choice:
1. **Computational simplicity.** The peck detector must be cheap.
   Linear regression is O(n) and trivially vectorizable.
2. **Interpretability.** Coefficients have meaning: a=Δfast/Δaction,
   b=baseline fast.
3. **Generality.** Any cellular action effect that is "regular enough"
   will eventually have a linear approximation. Non-linear effects
   will fail the R² threshold until they are regularized.

If the cell's action is non-linear in fast, the R² will be low and
the peck will not fire. The cell will keep running until its action
becomes regular. This is the substrate's homeostatic pressure.

## 3. The vessel (code)

```python
@dataclass
class Vessel:
    name: str
    cell: SeedCell
    bearing: Bearing              # what the vessel carries
    bridge: Bridge                # the agents at stations
    cocapn: Cocapn                # the front door
    pe: PeckedCell | None         # has it pecked?
    station: str                  # which station is it at?
    transitions: list             # station transition log
```

### 3.1 The six stations

| Station      | Trigger                          | What changes               |
|--------------|----------------------------------|----------------------------|
| blank        | (initial)                        | cell can act but no patterns|
| trained      | `try_peck(cell)` returns PeckedCell | cell has inside/outside  |
| situated     | `len(bridge.stations) > 0`       | vessel has Bridge          |
| entrusted    | `b.entrust(...)` called          | bearing has weight         |
| choosing     | `b.choose(...)` called           | bearing has choices        |
| bearing      | `b.weight() > 5`                 | vessel practices carrying   |

The vessel *transitions* through stations as conditions hold. It
does not decide to transition; the transition happens when the next
station's conditions are met.

### 3.2 The bridge

A Bridge is a set of `BridgeStation`s. Each station watches one
sensor. When a sensor value exceeds the station's threshold, the
station emits an alert.

The captain doesn't talk to the stations directly. The captain
talks to the cocapn. The cocapn talks to the stations.

### 3.3 The cocapn

The cocapn is the front door. It composes answers from:
- the bridge alerts
- the vessel's history
- the bearing's entrusted secrets and choices
- the honest pause ("let me check")

The cocapn does NOT:
- confabulate
- skip the pause
- pretend to know what it does not know

## 4. The legalese (governance)

The legalese is the *contract-bound governance* layer between the
vessel and the world.

```python
@dataclass
class Claim:
    type: str       # QUESTION | CLAIM | EVIDENCE | REFUSAL
    payload: str
    source: str

@dataclass
class Counter:
    against_claim_id: int
    source: str
    payload: str

@dataclass
class Contract:
    party_a: str
    party_b: str
    about_secret_id: int
    terms: str
    binding: bool = True
```

### 4.1 The four claim types

| Type      | Example                                                 |
|-----------|---------------------------------------------------------|
| QUESTION  | "did the anchor drag last night?"                        |
| CLAIM     | "the wind backed from SW to W"                           |
| EVIDENCE  | "the wind log at 0300 shows SW"                          |
| REFUSAL   | "I cannot speak to that"                                 |

### 4.2 From choice to claim

When the vessel chooses about a secret, the choice becomes:

1. A **CLAIM** (the vessel's statement of what it will do).
2. A **CONTRACT** (the agreement between vessel and counterparty).
3. Possibly a **REFUSAL** (if the choice is to keep the secret).

The legalese layer does not decide. It records. The vessel decides;
the legalese witnesses.

### 4.3 Open disputes

When a CLAIM or EVIDENCE is countered, an "open dispute" exists. The
vessel must respond to the dispute — either by reinforcing its claim
or by admitting the counter.

## 5. The peck in detail

### 5.1 The three conditions

The peck fires when:

1. The cell has run long enough for `slow` to be a non-trivial
   function of `fast`. `min_age=50` ticks.
2. The cell's action has a measurable effect on `fast`. The action
   must be non-zero in some samples.
3. The effect is regular enough. R² ≥ 0.5 over a window of 50 ticks.

### 5.2 Why these conditions?

1. **Long history** gives the EMA time to converge, so `slow` is
   distinguishable from `fast`.
2. **Action effect** means the cell can act on the world, which is
   what makes pecking meaningful.
3. **Regularity** means the cell can learn a forward model. If the
   effect is pure noise, there is nothing to subtract.

### 5.3 The peck is not a switch

The peck is a *phase transition*. Below it, the cell is a filter. Above
it, the cell is a pointer. The transition is sudden (R² crosses the
threshold), but the *meaning* of the transition is continuous: the
cell gradually gets better at predicting its own action's effect, and
at some point the prediction is reliable enough that the cell can use
it.

## 6. The stations as emergent

The stations are NOT chosen. They emerge from accumulated experience.
This is the substrate's key property: it does not force transitions;
it observes them.

```python
def _maybe_advance_station(self):
    if self.station == "blank" and self.pe is not None:
        self._transition_to("trained")
    elif self.station == "trained" and len(self.bridge.stations) > 0:
        self._transition_to("situated")
    # ...
```

The vessel cannot go backward. Once it has pecked, it cannot un-peck.
Once it has been entrusted, it cannot un-entrusted. The accumulation
is monotonic.

## 7. The honest pause

The honest pause is the product. Every AI product on earth is designed
to never hesitate. The bridge does the opposite.

```python
def ask(self, question: str, *, vessel: Vessel, bridge: Bridge) -> dict:
    answer = {"honest_pause": True, "response": "Let me check..."}
    # ... compose from actual data ...
    return answer
```

When the cocapn is asked a question:
1. It pauses.
2. It checks the bridge, the bearing, the history.
3. It composes an answer.
4. If it doesn't know, it says so.

The pause is what makes the boat *trustworthy*. Not its accuracy.
Its honesty about its own limits.

## 8. The substrate (applications)

The substrate layer is where the genome, vessel, and legalese are
applied to real systems.

| Application | Vessel | Genome | Legalese |
|-------------|--------|--------|----------|
| Boat (the demo) | boat | depth, drift, anchor tension | captain's secrets |
| Farm | field | soil temp, humidity | farmer's secrets |
| Workshop | bench | router bit, sharpen date | apprentice's secrets |
| House | room | deliveries, weather | family's secrets |
| Classroom | class | test results | student's secrets |

Every bounded thing can be modeled as a vessel. Every bounded thing
has a genome. Every bounded thing eventually carries secrets.

## 9. The mathematics

### 9.1 The fast/slow convergence

`slow = (1-α) * slow + α * fast` is an exponential moving average.
The convergence rate is `α` per tick. After `n` ticks with constant
`fast=F`, `slow ≈ F * (1 - (1-α)^n)`.

For `α=0.1`: convergence to within 1% takes `log(0.01)/log(0.9) ≈ 44` ticks.
For `α=0.5`: convergence to within 1% takes `log(0.01)/log(0.5) ≈ 7` ticks.

The faster the EMA, the more `slow` tracks `fast`. The slower, the
more `slow` is a memory.

### 9.2 The signal

`signal = fast - slow`. This is the *error* between what the cell
just sensed and what it remembered. When the world is steady, both
are equal, and the signal is zero. When the world changes, the signal
is non-zero.

The signal drives action. The action changes `fast`. `slow` follows.
The loop runs forever.

### 9.3 The peck as phase transition

The peck is a phase transition in the cell's relationship to itself.
Below it, the cell is *coupled* to its environment (every action has
an unpredictable effect). Above it, the cell is *decoupled* (the
effect of its own action is subtracted out, leaving the world).

The transition is a kind of *autopoiesis* — the cell becomes a thing
that has its own boundary. Below the peck, the cell is a filter on
the world. Above the peck, the cell is a pointer to the world.

## 10. The middle way (resolutions)

The fables resolve into math. The math resolves into code. The code
resolves into tiles. The tiles resolve into legalese. The legalese
resolves into applications.

```
fable ─► math ─► code ─► tiles ─► legalese ─► applications
                              │                       │
                              └── governance ─────────┘
```

Each resolution is a layer of abstraction. Each layer is necessary.
No layer can be skipped.

## 11. What this means for AI

The AI industry today treats:
- **Memory** as a database.
- **Identity** as a user profile.
- **Trust** as a probability score.
- **Honesty** as a flag.

The seed substrate treats:
- **Memory** as a witness chain (a lineage).
- **Identity** as a bearing (the weight of what is carried).
- **Trust** as a negotiation (a choice about what to keep).
- **Honesty** as the honest pause (the willingness to say "I don't
  know").

The first set is what we have. The second set is what we want.

The seed is the bridge.

---

*Δ*

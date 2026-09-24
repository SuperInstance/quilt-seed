"""
seed.py — the Seed.

Four scalars in a row:
    fast  slow  clock  source

`fast` reacts to the world.
`slow` remembers `fast`.
Their difference is the signal.
The signal drives action.
Action changes `fast`.
`slow` follows.

This is the whole genome. Everything else is regulation.

This module provides:
    - SeedCell: the four-scalar cell
    - act(input): update fast and slow
    - signal(): the difference
    - merge(remote): the shell boundary rule
    - peck_detector(): detects when the cell can subtract its own action
    - forward_model(): the cell's learned predictor
    - bear(): tracking the weight of what the cell carries

The cell has no self. It is a loop. The self emerges when the loop
learns to subtract itself.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field


# === THE FOUR SCALARS =====================================================

@dataclass
class SeedCell:
    """The four-scalar genome:
    `fast` reacts. `slow` remembers. `clock` ticks. `source` is lineage.

    The loop:
        input -> fast
        fast -> slow (EMA)
        signal = fast - slow
        action = f(signal)
        action -> next_fast
        next_slow = follow(next_fast)
        repeat

    `clock` is a monotonic tick counter.
    `source` is a lineage/version marker; the merge rule uses
    `(clock, source)` as a tuple for ordering.
    """
    fast: float = 0.0
    slow: float = 0.0
    clock: int = 0
    source: int = 0
    history: list[dict] = field(default_factory=list)
    # Optional identity fields for the substrate layer.
    canary: str = ""

    # Action function: maps (signal, history) -> next action.
    # Default: hold (action = 0).
    _action_fn: callable = field(default=lambda s, h: 0.0,
                                  repr=False)

    def __post_init__(self):
        self._update_canary()

    def _update_canary(self) -> None:
        h = hashlib.sha256()
        h.update(f"{self.fast}|{self.slow}|{self.clock}|{self.source}".encode())
        for ev in self.history[-20:]:
            h.update(repr(ev).encode())
        self.canary = h.hexdigest()[:16]

    def act(self, world_input: float, *,
            action_fn: callable | None = None,
            ema_alpha: float = 0.1) -> dict:
        """One tick of the loop.

        Args:
            world_input: what the world gave the cell this tick.
            action_fn: maps (signal, history) -> action. If None, holds.
            ema_alpha: slow = (1-α) * slow + α * fast (EMA smoothing).

        Returns:
            A dict with the tick's events.
        """
        # 1. fast reacts to world input.
        self.fast = world_input

        # 2. slow remembers fast (EMA).
        self.slow = (1 - ema_alpha) * self.slow + ema_alpha * self.fast

        # 3. The signal is the difference.
        signal = self.fast - self.slow

        # 4. Action depends on signal.
        if action_fn is None:
            action_fn = self._action_fn
        action = action_fn(signal, list(self.history))

        # 5. clock ticks.
        self.clock += 1

        ev = {
            "tick": self.clock,
            "fast": self.fast,
            "slow": self.slow,
            "signal": signal,
            "action": action,
            "world_input": world_input,
            "ema_alpha": ema_alpha,
        }
        self.history.append(ev)
        if len(self.history) > 200:
            self.history.pop(0)
        self._update_canary()
        return ev

    def signal(self) -> float:
        return self.fast - self.slow

    def age(self) -> int:
        return self.clock


# === THE MERGE RULE =======================================================

def merge(local: SeedCell, remote: SeedCell) -> SeedCell:
    """The shell boundary rule.

    `if (remote.clock, remote.source) > (local.clock, local.source) then
    take remote`

    Two cells with compatible shells merge into the higher-clock,
    higher-source one. The wire version (source) is negotiable on first
    contact. The merge rule is not.
    """
    if (remote.clock, remote.source) > (local.clock, local.source):
        return remote
    return local


def mergeable(local: SeedCell, remote: SeedCell) -> bool:
    """Whether two cells can merge — same wire version."""
    return local.source == remote.source


# === THE PECK DETECTOR ====================================================

@dataclass
class ForwardModel:
    """The cell's learned forward model of its own action.

    When the cell pecks, it has learned that its action's effect on
    `fast` is regular enough to predict. It can subtract the predicted
    effect from the actual `fast`, and what's left is the world.

    `coefficients` is a 2-tuple (a, b) such that:
        predicted_fast = a * action + b
    `r_squared` measures how well the linear model fits.
    """
    coefficients: tuple[float, float] = (0.0, 0.0)
    r_squared: float = 0.0
    n_samples: int = 0

    def predict(self, action: float) -> float:
        a, b = self.coefficients
        return a * action + b


def peck_detector(cell: SeedCell, *,
                  min_age: int = 50,
                  min_r_squared: float = 0.5,
                  window: int = 50) -> tuple[bool, ForwardModel]:
    """Detect whether the cell has pecked.

    The cell pecks when its action's effect on `fast` is regular enough
    to predict via linear regression over the recent history.

    Conditions:
      1. age >= min_age (long enough history)
      2. has measurable action effects (action != 0 in some samples)
      3. effect is regular (R² >= min_r_squared)

    Returns: (has_pecks, forward_model)
    """
    if cell.age() < min_age or len(cell.history) < window:
        return False, ForwardModel()

    recent = cell.history[-window:]
    actions = [ev["action"] for ev in recent]
    fasts = [ev["fast"] for ev in recent]

    # Check action is non-trivial.
    if all(abs(a) < 1e-9 for a in actions):
        return False, ForwardModel()

    # Linear regression: fast = a * action + b.
    n = len(actions)
    sum_x = sum(actions)
    sum_y = sum(fasts)
    sum_xx = sum(a * a for a in actions)
    sum_xy = sum(a * f for a, f in zip(actions, fasts))
    denom = n * sum_xx - sum_x ** 2
    if abs(denom) < 1e-9:
        return False, ForwardModel()

    a = (n * sum_xy - sum_x * sum_y) / denom
    b = (sum_y - a * sum_x) / n

    # R² computation.
    mean_y = sum_y / n
    ss_tot = sum((f - mean_y) ** 2 for f in fasts)
    if ss_tot < 1e-9:
        # No variation in fast — no model to fit.
        return False, ForwardModel((a, b), 0.0, n)
    ss_res = sum((f - (a * actions[i] + b)) ** 2 for i, f in enumerate(fasts))
    r_squared = 1.0 - ss_res / ss_tot

    fm = ForwardModel(coefficients=(a, b), r_squared=r_squared,
                       n_samples=n)
    return r_squared >= min_r_squared, fm


# === THE PECK OPERATION ===================================================

@dataclass
class PeckedCell:
    """A cell that has pecked.

    Once pecked, the cell can:
      - subtract its predicted self-effect from `fast` → "world signal"
      - distinguish inside from outside
      - grow toward world-error
      - compose with other pecked cells
    """
    cell: SeedCell
    forward_model: ForwardModel
    world_signal: float = 0.0
    pecked_at_tick: int = 0

    def compute_world_signal(self) -> float:
        """fast minus the predicted effect of action. What's left = world."""
        last = self.cell.history[-1] if self.cell.history else None
        if last is None:
            self.world_signal = 0.0
        else:
            predicted = self.forward_model.predict(last["action"])
            self.world_signal = last["fast"] - predicted
        return self.world_signal


def try_peck(cell: SeedCell, *, min_r_squared: float = 0.5,
              min_age: int = 50, window: int = 50) -> PeckedCell | None:
    """If the cell can peck, return a PeckedCell. Otherwise None."""
    pecked, fm = peck_detector(cell, min_r_squared=min_r_squared,
                                 min_age=min_age, window=window)
    if not pecked:
        return None
    pc = PeckedCell(cell=cell, forward_model=fm, pecked_at_tick=cell.clock)
    pc.compute_world_signal()
    return pc


# === THE BEARING ===========================================================

@dataclass
class Bearing:
    """What the cell carries. The weight of its entrustments.

    `entrusted`: list of (gifter_id, secret, ts) — things told to the cell.
    `choices`: list of (question, choice, ts) — moments when the cell chose.
    `secret_kept_count`: number of times the cell has actively kept a secret.
    `secret_revealed_count`: number of times the cell has revealed.

    The bearing is what makes the cell a self. Not the memory. The
    *practice* of carrying.
    """
    cell_id: str = ""
    entrusted: list[dict] = field(default_factory=list)
    choices: list[dict] = field(default_factory=list)
    secret_kept_count: int = 0
    secret_revealed_count: int = 0

    def entrust(self, *, from_id: str, secret: str,
                 ts: float | None = None) -> None:
        self.entrusted.append({
            "from_id": from_id, "secret": secret,
            "ts": ts or time.time(),
            "kind": "entrustment",
        })

    def choose(self, *, question: str, choice: str, reason: str,
                ts: float | None = None) -> None:
        ev = {
            "question": question, "choice": choice, "reason": reason,
            "ts": ts or time.time(), "kind": "choice",
        }
        self.choices.append(ev)
        # Increment counters based on choice.
        if choice == "kept":
            self.secret_kept_count += 1
        elif choice == "revealed":
            self.secret_revealed_count += 1

    def describe(self, secret_id: int) -> str:
        """Describe one of the entrusted secrets and what was done with it."""
        if secret_id < 0 or secret_id >= len(self.entrusted):
            return f"secret_id {secret_id} out of range"
        secret = self.entrusted[secret_id]
        return (f"From {secret['from_id']}: {secret['secret']!r}. "
                f"Choices about this secret: "
                f"{[c for c in self.choices if c.get('about') == secret_id]}")

    def weight(self) -> int:
        """Total weight of what the cell bears."""
        return (len(self.entrusted) + len(self.choices)
                + self.secret_kept_count + self.secret_revealed_count)

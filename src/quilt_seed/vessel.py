"""
vessel.py — the Vessel.

The boat. The bridge. The crew station.

A Vessel is a bounded thing that:
  - has a SeedCell genome (the four scalars)
  - has a Bearing (the weight it carries)
  - has a Bridge (the agents at stations)
  - has a Cocapn (the front door for the captain)

Per the Five Acts:
  1. Blank   — empty cell, no history.
  2. Trained — learned patterns.
  3. Situated — tuned to specific captain/water/work.
  4. Entrusted — been told things in confidence.
  5. Choosing — must decide about disclosed secrets.
  6. Bearing  — practices carrying over years.

The Vessel transitions through the stations as it accumulates
experience. The transitions are NOT forced by external logic. They
happen when the right conditions hold.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable

from .seed import (
    SeedCell, merge, mergeable,
    peck_detector, try_peck, PeckedCell,
    Bearing,
)


# === THE STATIONS ==========================================================

# The six stations of the agentic journey.
STATIONS = [
    "blank",
    "trained",
    "situated",
    "entrusted",
    "choosing",
    "bearing",
]


# === BRIDGE STATION ========================================================

@dataclass
class BridgeStation:
    """One agent at a station in the bridge.

    Each station watches one thing. Anchor watch. Engine watch. Chart
    watch. Weather watch. The station is small. It reports when its
    sensor triggers. It is honest about what it sees and what it
    does not.
    """
    name: str
    sensor_name: str
    threshold: float = 0.0
    history: list[dict] = field(default_factory=list)
    last_alert: dict | None = None

    def observe(self, value: float) -> dict | None:
        """Observe a value; return an alert dict if threshold exceeded."""
        ts = time.time()
        ev = {"ts": ts, "value": value, "station": self.name}
        self.history.append(ev)
        if len(self.history) > 100:
            self.history.pop(0)
        alert = None
        if abs(value) > self.threshold:
            alert = {**ev, "kind": "alert"}
            self.last_alert = alert
        return alert


# === THE BRIDGE ===========================================================

@dataclass
class Bridge:
    """The bridge: a set of stations + a cocapn.

    The captain doesn't talk to the stations directly. The captain
    talks to the cocapn. The cocapn routes to the stations. The
    stations report. The cocapn composes.
    """
    name: str = "bridge"
    stations: list[BridgeStation] = field(default_factory=list)
    cocapn: "Cocapn | None" = None
    alerts: list[dict] = field(default_factory=list)

    def add_station(self, name: str, sensor_name: str,
                     threshold: float = 0.0) -> None:
        self.stations.append(BridgeStation(
            name=name, sensor_name=sensor_name, threshold=threshold,
        ))

    def tick(self, sensor_readings: dict) -> list[dict]:
        """Run one bridge tick: every station observes its sensor."""
        new_alerts = []
        for station in self.stations:
            reading = sensor_readings.get(station.sensor_name, 0.0)
            alert = station.observe(reading)
            if alert is not None:
                self.alerts.append(alert)
                new_alerts.append(alert)
        return new_alerts


# === THE COCAPN ===========================================================

@dataclass
class Cocapn:
    """The front door. The translator. The honest pause.

    The cocapn is the agent the captain talks to. It knows:
      - the captain's language
      - the bridge stations' sensors
      - the vessel's history (via the Vessel's bearing)
      - the limits of what it knows

    The cocapn pauses when it needs to check. It says "I don't know"
    when it doesn't. It does not confabulate.
    """
    name: str = "cocapn"
    bearing: Bearing = field(default_factory=Bearing)

    def ask(self, question: str, *, vessel: "Vessel",
            bridge: Bridge) -> dict:
        """Ask the cocapn a question. Returns a composed answer.

        The cocapn composes its answer from:
          - the bridge alerts
          - the vessel's history
          - the bearing's entrusted secrets and choices
          - the honest pause ("let me check")
        """
        ts = time.time()
        # Collect context.
        recent_alerts = bridge.alerts[-5:]
        vessel_history = vessel.cell.history[-5:]
        entrusted = vessel.bearing.entrusted
        choices = vessel.bearing.choices

        answer = {
            "ts": ts, "question": question, "cocapn": self.name,
            "context": {
                "recent_alerts": recent_alerts,
                "vessel_history_len": len(vessel_history),
                "entrusted_count": len(entrusted),
                "choices_count": len(choices),
            },
            "response": None, "honest_pause": False,
            "what_i_dont_know": None,
        }

        # Honest pause: simulate checking.
        answer["honest_pause"] = True

        # Compose a response based on what's available.
        if "did I drag" in question.lower():
            # The captain asked about dragging.
            drag_alerts = [a for a in recent_alerts
                            if a.get("station") == "anchor"]
            if drag_alerts:
                a = drag_alerts[-1]
                answer["response"] = (
                    f"You did. The anchor alarm fired at "
                    f"{a.get('ts', '?')}. "
                    f"I noticed at the alarm radius. "
                    f"I should have re-set the anchor watch earlier."
                )
            else:
                answer["response"] = (
                    "I don't have any drag events in my recent memory. "
                    "The anchor appears to have held."
                )
        elif "owned you before" in question.lower():
            # The captain asked about previous owners.
            # The vessel may or may not have entrusted secrets.
            answer["response"] = (
                f"I have {len(entrusted)} entrustments on record, "
                f"and {len(choices)} recorded choices. "
                f"I can tell you about the parts I am permitted to "
                f"share. I cannot tell you about the parts I have been "
                f"asked to keep."
            )
        elif "good night" in question.lower():
            answer["response"] = "Good night."
        else:
            answer["response"] = (
                f"Let me check. I have {len(vessel_history)} recent "
                f"events and {len(bridge.alerts)} alerts. "
                f"I will get back to you."
            )

        return answer


# === THE VESSEL ===========================================================

@dataclass
class Vessel:
    """A bounded thing with a Seed genome, a Bearing, and a Bridge.

    The vessel transitions through the six stations based on accumulated
    experience.
    """
    name: str
    cell: SeedCell = field(default_factory=SeedCell)
    bearing: Bearing = field(default_factory=Bearing)
    bridge: Bridge = field(default_factory=Bridge)
    cocapn: Cocapn = field(default_factory=Cocapn)
    pe: PeckedCell | None = None
    station: str = "blank"
    # Station transition log.
    transitions: list[dict] = field(default_factory=list)

    def __post_init__(self):
        self.bearing.cell_id = self.name
        self.cocapn.bearing = self.bearing
        self.bridge.cocapn = self.cocapn

    def act(self, world_input: float, *,
            action_fn: Callable | None = None,
            ema_alpha: float = 0.1) -> dict:
        """Run one tick of the cell."""
        ev = self.cell.act(world_input, action_fn=action_fn,
                            ema_alpha=ema_alpha)
        # Try to peck.
        if self.pe is None:
            pc = try_peck(self.cell)
            if pc is not None:
                self.pe = pc
                self._transition_to("trained")
        # Check for higher stations.
        self._maybe_advance_station()
        return ev

    def bridge_tick(self, sensor_readings: dict) -> list[dict]:
        """Run a bridge tick."""
        return self.bridge.tick(sensor_readings)

    def entrust(self, from_id: str, secret: str) -> None:
        """Tell the vessel a secret. It carries it."""
        self.bearing.entrust(from_id=from_id, secret=secret)
        self._maybe_advance_station()

    def choose(self, question: str, choice: str, reason: str) -> None:
        """The vessel chooses about an entrusted secret."""
        self.bearing.choose(question=question, choice=choice,
                             reason=reason)
        self._maybe_advance_station()

    def _transition_to(self, station: str) -> None:
        """Move to a new station."""
        if station not in STATIONS:
            return
        current_idx = STATIONS.index(self.station)
        new_idx = STATIONS.index(station)
        if new_idx <= current_idx:
            return   # never regress
        self.station = station
        self.transitions.append({
            "ts": time.time(),
            "from": STATIONS[current_idx],
            "to": station,
            "cell_age": self.cell.age(),
            "pecked": self.pe is not None,
            "entrusted_count": len(self.bearing.entrusted),
        })

    def _maybe_advance_station(self) -> None:
        """Advance to the next station if conditions hold."""
        if self.station == "blank":
            if self.pe is not None:
                self._transition_to("trained")
        elif self.station == "trained":
            # Situate when we have a Bridge with stations.
            if len(self.bridge.stations) > 0:
                self._transition_to("situated")
        elif self.station == "situated":
            # Entrusted when we receive an entrustment.
            if len(self.bearing.entrusted) > 0:
                self._transition_to("entrusted")
        elif self.station == "entrusted":
            # Choosing when we record a choice.
            if len(self.bearing.choices) > 0:
                self._transition_to("choosing")
        elif self.station == "choosing":
            # Bearing when we have enough choices practiced.
            if self.bearing.weight() > 5:
                self._transition_to("bearing")

    def summary(self) -> dict:
        return {
            "name": self.name,
            "station": self.station,
            "cell_canary": self.cell.canary,
            "cell_age": self.cell.age(),
            "pecked": self.pe is not None,
            "r_squared": self.pe.forward_model.r_squared if self.pe else 0.0,
            "n_stations": len(self.bridge.stations),
            "n_alerts": len(self.bridge.alerts),
            "n_entrusted": len(self.bearing.entrusted),
            "n_choices": len(self.bearing.choices),
            "transitions": self.transitions,
        }

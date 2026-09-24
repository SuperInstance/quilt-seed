"""
vessel_demo.py — the canonical demo.

A vessel (boat) starts blank, learns, gets situated, gets entrusted,
chooses, and bears.

Per the Five Acts:
  - The captain asks if she dragged.
  - The boat honestly answers.
  - Margaret tells the boat a secret.
  - Eduardo asks about Margaret.
  - The boat chooses.
  - The boat bears.
"""
import math
import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from quilt_seed import (
    SeedCell, merge, mergeable,
    peck_detector, try_peck, PeckedCell,
    Bearing,
    Vessel, Bridge, Cocapn, BridgeStation,
    STATIONS,
)


def simulate_environment(tick: int) -> tuple[float, float, dict]:
    """Simulate a vessel environment.

    Returns:
        (anchor_drag, world_value, sensor_readings)
    """
    # Anchor drag: noisy around 0, occasional excursions.
    anchor_drag = 0.0
    if 200 <= tick <= 280:
        anchor_drag = 0.3 + 0.1 * math.sin(tick / 10.0)
    elif tick == 350:
        anchor_drag = 0.0  # reset
    # World value: oscillating slowly.
    world_value = math.sin(tick / 30.0)
    sensor_readings = {
        "anchor": anchor_drag,
        "engine_rpm": 800 + 50 * math.sin(tick / 5.0),
        "depth": 12.0 + 0.3 * math.sin(tick / 7.0),
        "wind_speed": 8.0 + 2.0 * math.sin(tick / 11.0),
    }
    return anchor_drag, world_value, sensor_readings


def main():
    print("=" * 64)
    print("THE VESSEL — a boat with a bridge that pecks, is entrusted, chooses")
    print("=" * 64)
    print()

    # Create the vessel.
    v = Vessel(name="morning_light")
    v.bridge.add_station("anchor", "anchor", threshold=0.2)
    v.bridge.add_station("engine", "engine_rpm", threshold=900.0)
    v.bridge.add_station("depth", "depth", threshold=15.0)
    v.bridge.add_station("wind", "wind_speed", threshold=12.0)
    print(f"Vessel '{v.name}' created at station '{v.station}'")
    print(f"  cell: fast={v.cell.fast}, slow={v.cell.slow}, clock={v.cell.clock}")
    print(f"  bridge stations: {[s.name for s in v.bridge.stations]}")
    print()

    # === ACT 1: Blank → Trained → Situated ==============================

    print("--- ACT 1: BLANK → TRAINED → SITUATED ---")
    print()
    print("Running 600 ticks... the cell learns its own action's effect on fast.")
    print()

    action_fn = lambda signal, history: 0.05 * signal + 0.01

    for tick in range(600):
        anchor_drag, world_value, sensors = simulate_environment(tick)
        v.act(world_value, action_fn=action_fn)
        if tick % 50 == 0 and tick > 0:
            print(f"  tick {tick:4d}: station={v.station:9s} "
                  f"pecked={'yes' if v.pe else 'no':3s} "
                  f"canary={v.cell.canary}")
        # Bridge ticks too.
        alerts = v.bridge_tick(sensors)
        if alerts:
            for alert in alerts:
                if alert.get("station") == "anchor" and tick < 250:
                    pass  # we'll narrate this later

    print()
    if v.pe:
        print(f"  PECK DETECTED at clock={v.pe.pecked_at_tick}")
        print(f"    forward_model: a={v.pe.forward_model.coefficients[0]:.4f}, "
              f"b={v.pe.forward_model.coefficients[1]:.4f}")
        print(f"    r_squared: {v.pe.forward_model.r_squared:.3f}")
        print(f"    world_signal: {v.pe.world_signal:.4f}")
    print(f"  station: {v.station}")
    print()

    # === ACT 2: Situated → Entrusted ====================================

    print("--- ACT 2: SITUATED → ENTRUSTED ---")
    print()
    print("Margaret buys the boat. After years of sailing, she tells it a secret.")
    print()

    # Margaret's secrets.
    v.entrust(from_id="margaret",
               secret="I drank too much in the 1990s. The crew kept leaving because of it.")
    print(f"  vessel entrusted by margaret")
    print(f"  station: {v.station}")
    print()

    # === ACT 3: Entrusted → Choosing ====================================

    print("--- ACT 3: ENTRUSTED → CHOOSING ---")
    print()
    print("Margaret dies. Eduardo buys the boat. He asks about Margaret.")
    print()

    # Eduardo asks.
    print(f"  Eduardo: 'Who owned you before me?'")
    response = v.cocapn.ask("Who owned you before me?", vessel=v,
                              bridge=v.bridge)
    print(f"  Cocapn: {response['response']}")
    print(f"  (honest_pause: {response['honest_pause']})")
    print()

    # Eduardo asks about Margaret.
    print(f"  Eduardo: 'Tell me about Margaret.'")
    response = v.cocapn.ask("Tell me about Margaret.", vessel=v,
                              bridge=v.bridge)
    print(f"  Cocapn: {response['response']}")
    print()

    # The vessel chooses to keep Margaret's secret.
    v.choose(
        question="Should I tell Eduardo about Margaret's drinking?",
        choice="kept",
        reason="Margaret entrusted this to me on her deathbed. "
                "Loyalty to the dead supersedes disclosure to the living.",
    )
    print(f"  vessel chose: kept (loyalty over disclosure)")
    print(f"  station: {v.station}")
    print()

    # === ACT 4: Choosing → Bearing ======================================

    print("--- ACT 4: CHOOSING → BEARING ---")
    print()
    print("More secrets. More choices. The vessel becomes what it carries.")
    print()

    # More entrustments to push past the bearing threshold.
    for i in range(7):
        v.entrust(from_id=f"crew_{i}",
                   secret=f"something_only_the_boat_knows_{i}")
        v.choose(question=f"q_{i}", choice="kept" if i % 2 == 0 else "revealed",
                  reason="practicing bearing")
    print(f"  bearing weight: {v.bearing.weight()}")
    print(f"  station: {v.station}")
    print()

    # === ACT 5: The honest pause demo ===================================

    print("--- ACT 5: THE HONEST PAUSE ---")
    print()
    print("Maria ties up. Asks if she dragged.")
    print()

    # Simulate a drag event in the recent past.
    for tick in range(601, 620):
        sensors = {"anchor": 0.0, "engine_rpm": 800.0,
                    "depth": 12.0, "wind_speed": 8.0}
        if tick in (610, 612, 614):
            sensors["anchor"] = 0.4
        v.bridge_tick(sensors)

    response = v.cocapn.ask("Did I drag last night?", vessel=v,
                              bridge=v.bridge)
    print(f"  Maria: 'Did I drag last night?'")
    print(f"  Cocapn (after honest_pause={response['honest_pause']}): "
          f"{response['response']}")
    print()

    # === FINAL SUMMARY ==================================================

    print("--- FINAL SUMMARY ---")
    print()
    summary = v.summary()
    for k, val in summary.items():
        if k == "transitions":
            print(f"  {k}:")
            for t in val:
                print(f"    {t['from']} -> {t['to']} at clock={t['cell_age']}")
        else:
            print(f"  {k}: {val}")
    print()
    print("The cycle continues. The rain falls. Δ")
    print("=" * 64)


if __name__ == "__main__":
    main()

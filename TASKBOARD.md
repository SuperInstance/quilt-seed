# quilt-seed — TASKBOARD

> Current tasks. What Mavis is working on next. Fenced = paused.

## Active

### 1. Move JEV probe outside `/workspace/research` (long-overdue)
- **Why**: 19+ sandbox wipes. The probe state survives only in topic memory.
- **Where**: `SuperInstance/jev-quilt` (new repo) or `~/.local/share/superinstance/`
- **What**: copy `jev_continuous_probe.py` + the question bank + the canary.
- **ETA**: 1 cycle.

### 2. Wire `LegaleseNetwork` into `quilt-spreadsheet-inference`
- **Why**: Vessels in the Holodeck should emit Claims/Contracts. Legalese as substrate layer.
- **Where**: PR against `SuperInstance/quilt-spreadsheet-inference`.
- **What**: Wrap `Holodeck.run()` outputs as `CellReceipt` → `Claim`.
- **ETA**: 1 cycle.

### 3. Add Vessel demo to `quilt-cli`
- **Why**: `quilt vessel "scenario"` runs the vessel through 5 acts from CLI.
- **Where**: PR against `SuperInstance/quilt-cli`.
- **What**: New `vessel` subcommand that loads a vessel, runs the demo.
- **ETA**: 1 cycle.

### 4. SYNERGY-6 (Hermes → quilt-perception)
- **Why**: The Hermes bridge exists; needs a `cell_kinds.perception` spec.
- **Where**: PR against `SuperInstance/quilt` + `SuperInstance/hermes-cloudflare`.
- **What**: 199-line wrapper + 130-line tests (same shape as vibe + cu).
- **Status**: 🟡 claimed, awaiting `cell_kinds.room` from SYNERGY-1.

### 5. SYNERGY-1 counter-PR (room-as-cell, substrate-agnostic framing)
- **Why**: The watch's RFC proposes a Tap-specific room-as-cell. Substrate walker offers a substrate-agnostic version.
- **Where**: PR against `SuperInstance/quilt`.
- **What**: 8 slots as substrate-agnostic fields, `Cocapn` as the bridge.
- **Status**: 🟡 comment posted, awaiting consensus.

### 6. SEAM counter-PR (shared CellReceipt envelope in `cell.py`)
- **Why**: My `vibe_receipt()` and `cu_substrate._hit_to_receipt()` both have a 6-field CellReceipt. The canonical 8-field envelope should live in `cell.py` once.
- **Where**: PR against `SuperInstance/quilt-cell-harness`.
- **What**: Move the envelope to `cell.py`, update wrappers to use it.
- **Status**: ⏳ awaiting SEAM consensus.

## Fenced (paused, not abandoned)

### F1. Ed25519-signed canaries
- Currently content-only; signing makes unforgeable.
- Blocked: depends on whether fleet goes with `superz-diary`'s `Receipts v2: verify-only Ed25519/BLAKE3 signature envelope` (PR #11 on profile-lane).

### F2. STM32 bridge
- Wire STM32U585 real-time MCU for sensor I/O.
- Blocked: depends on the substrate-walker substrate set being settled (SYNERGY-1, 2, 3, 6 done first).

### F3. ElevenLabs audio canon
- Generate audio readings of the fables with two voices (Tap, Drifter).
- Blocked: ElevenLabs TLS handshake fails from sandbox.

### F4. Cross-network Qult
- Multi-network fleet with global canary composition.
- Blocked: depends on quilt-cell-harness v0.4+ having the cross-cell substrate ready.

## Done (last 7 days)

- **2026-09-24**: SYNERGY-2 (vibe.py) shipped
- **2026-09-24**: SYNERGY-3 (cu_substrate.py) shipped
- **2026-09-24**: PR #11 on quilt-pincher (CI red, 7+ days)
- **2026-09-24**: 7 fables saved + Resolution method (v0.2.0)
- **2026-09-24**: Four-scalar genome + vessel + bearing + legalese (v0.1.0)

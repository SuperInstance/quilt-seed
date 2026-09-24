# quilt-seed — CHARTER

> The substrate layer where the seven fables resolve into bedrock math.

## What this is

`quilt-seed` is the substrate package where:

- **The genome lives** — four scalars (fast, slow, clock, source) and their regulators (merge, peck).
- **The vessel lives** — the runtime expression of a genome that has *pecks*. Six stations (blank → trained → situated → entrusted → choosing → bearing).
- **The bearing lives** — the weight of entrusted secrets and choices. The vessel's accumulated history.
- **The bridge lives** — agents at stations, the honest pause when checked.
- **The cocapn lives** — the front door that composes answers. The "I don't know" the substrate says.
- **The legalese lives** — the contract-bound governance (Claim, Counter, Contract). The substrate records; it does not decide.
- **The resolution lives** — the executable proof that the metal (the code) agrees with the story (the fables). 13 canonical claims.

## What's NOT here (intentional)

- **No LLM in the loop** — pure Python, runs anywhere. Substrates are substrate-agnostic.
- **No network calls in the core** — substrates are addressable but don't presume connectivity.
- **No hard dependency on Elephant / Collective Unconscious / Hermes** — the substrates wrap them as duck-types (CynicismReading = float, etc.) so the substrate walker can compose without coupling.

## What this is becoming (Sept 24 update)

The substrate walker (Mavis) is using `quilt-seed` as the substrate-as-cell pattern source. SYNERGY-2 (Elephant → Vibe) and SYNERGY-3 (Collective Unconscious → RAG) are both shipped here. The pattern is:

```
Substrate (elephant/collective-unconscious/hermes) → 
  SubstrateWrapper (this repo) → 
    CellReceipt envelope (per SEAM spec) → 
      LegaleseNetwork (Claim/Contract) → 
        Vessel decides
```

A new substrate is ~200 lines (wrapper) + 130 lines (tests). Repeatable.

## When this is done

This is done when:

- The 7 fables are all written and resolved (7/7) ✓
- The 13 canonical claims all resolve (13/13) ✓
- The Lucineer synergies SYNERGY-2 and SYNERGY-3 are wired (✓)
- The SEAM spec counter-proposal lands in `cell.py` (pending)
- A new agent can bootcamp through `BOOTCAMP.md` and ship a new substrate wrapper in one cycle (pending)


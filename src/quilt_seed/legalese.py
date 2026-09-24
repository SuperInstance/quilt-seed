"""
legalese.py — contract-bound governance for cellular agreements.

Per Casey's directive: "find the middle way where applications find
their just-so abstractions as a resolution in code, story, raw logic,
tiles, contract-bound legalise between cellular agreements, governance
etc."

A Vessel's choices about secrets are LEGALESE: they are claims about
how the witness chain will be reported. The vessel may CLAIM ("I will
not reveal X"), and other vessels may COUNTER ("I have a right to
know"), and the LegaleseNetwork tracks the disputes.

This module provides:
  - Claim: a statement with a payload, type, and confidence.
  - Counter: a counter-claim by another party.
  - Contract: a binding agreement between two parties.
  - LegaleseNetwork: a network of claims, counters, and contracts.

The legalese layer sits ABOVE the witness chain. It says:
  - here is what the witness chain contains.
  - here is who has claimed what about it.
  - here is what is contracted.
  - here is what is in dispute.

The vessel makes choices through this layer. A choice is a CONTRACT.
The contract says: "I will keep this secret" or "I will reveal this
thing". The network can be inspected at any time.
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field


# === CLAIM TYPES ===========================================================

# The four canonical claim types.
QUESTION = "QUESTION"        # "do you have data on X?"
CLAIM = "CLAIM"              # "the wind backed from SW to W"
EVIDENCE = "EVIDENCE"        # "the wind log at 0300 shows SW"
REFUSAL = "REFUSAL"          # "I cannot speak to that"


@dataclass
class Claim:
    """A claim made by some party about the witness chain."""
    type: str       # QUESTION | CLAIM | EVIDENCE | REFUSAL
    payload: str
    source: str     # the ID of the party making the claim
    confidence: float = 1.0
    about_secret_id: int | None = None  # if this claim is about a secret
    ts: float = field(default_factory=time.time)

    def __repr__(self) -> str:
        return f"<{self.type} by {self.source} conf={self.confidence:.2f}: " \
                f"{self.payload[:60]!r}>"


@dataclass
class Counter:
    """A counter-claim by another party."""
    against_claim_id: int
    source: str
    payload: str
    ts: float = field(default_factory=time.time)


@dataclass
class Contract:
    """A binding agreement between two parties about a secret."""
    party_a: str       # e.g., the vessel
    party_b: str       # e.g., the entrusting captain
    about_secret_id: int
    terms: str         # what is being agreed
    binding: bool = True   # if False, the contract is advisory
    signed_at: float = field(default_factory=time.time)


# === LEGALESE NETWORK =====================================================

@dataclass
class LegaleseNetwork:
    """A network of claims, counters, and contracts.

    The vessel's bridge between memory and meaning. The network does
    not decide. It records. The vessel decides; the network witnesses.
    """
    name: str = "legalese"
    claims: list[Claim] = field(default_factory=list)
    counters: list[Counter] = field(default_factory=list)
    contracts: list[Contract] = field(default_factory=list)

    def assert_claim(self, type: str, payload: str, *,
                      source: str = "vessel", confidence: float = 1.0,
                      about_secret_id: int | None = None) -> int:
        """Assert a claim; returns the claim ID."""
        claim = Claim(type=type, payload=payload, source=source,
                       confidence=confidence, about_secret_id=about_secret_id)
        self.claims.append(claim)
        return len(self.claims) - 1

    def counter(self, *, against_claim_id: int, source: str,
                 payload: str) -> int:
        """Counter a claim; returns the counter ID."""
        c = Counter(against_claim_id=against_claim_id, source=source,
                     payload=payload)
        self.counters.append(c)
        return len(self.counters) - 1

    def contract(self, *, party_a: str, party_b: str,
                  about_secret_id: int, terms: str,
                  binding: bool = True) -> int:
        """Sign a contract; returns the contract ID."""
        c = Contract(party_a=party_a, party_b=party_b,
                      about_secret_id=about_secret_id, terms=terms,
                      binding=binding)
        self.contracts.append(c)
        return len(self.contracts) - 1

    def claims_about_secret(self, secret_id: int) -> list[Claim]:
        return [c for c in self.claims
                if c.about_secret_id == secret_id]

    def open_disputes(self) -> list[tuple[Claim, Counter]]:
        """Find open disputes (a CLAIM/EVIDENCE has been countered)."""
        result = []
        for counter in self.counters:
            if counter.against_claim_id < len(self.claims):
                claim = self.claims[counter.against_claim_id]
                if claim.type in (CLAIM, EVIDENCE):
                    result.append((claim, counter))
        return result

    def binding_contracts(self) -> list[Contract]:
        return [c for c in self.contracts if c.binding]

    def canary(self) -> str:
        """Composed hash of the entire network."""
        h = hashlib.sha256()
        for c in self.claims:
            h.update(f"{c.type}|{c.payload}|{c.source}".encode())
        for c in self.counters:
            h.update(f"{c.against_claim_id}|{c.source}|{c.payload}".encode())
        for c in self.contracts:
            h.update(f"{c.party_a}|{c.party_b}|{c.terms}".encode())
        return h.hexdigest()[:16]

    def describe(self) -> str:
        return (f"LegaleseNetwork({self.name}): "
                f"{len(self.claims)} claims, "
                f"{len(self.counters)} counters, "
                f"{len(self.contracts)} contracts. "
                f"canary={self.canary()}")


# === VESSEL → LEGALESE BRIDGE ==============================================

def legalize_vessel_choice(vessel, *,
                            network: LegaleseNetwork,
                            question: str, choice: str,
                            reason: str,
                            counterparty: str = "the_other_party") -> dict:
    """The vessel makes a choice and the choice is legalized.

    The choice becomes:
      - a CLAIM (the vessel's statement of what it will do)
      - a CONTRACT (the agreement between vessel and counterparty)
      - possibly a REFUSAL (if the choice is to keep a secret)
    """
    ts = time.time()
    claims_added = []

    # 1. The vessel asserts its claim.
    if choice == "kept":
        claim_id = network.assert_claim(
            REFUSAL, f"I cannot reveal: {reason}",
            source=vessel.name, confidence=1.0,
        )
    elif choice == "revealed":
        claim_id = network.assert_claim(
            EVIDENCE, f"I will reveal because: {reason}",
            source=vessel.name, confidence=1.0,
        )
    else:
        claim_id = network.assert_claim(
            CLAIM, f"My choice: {choice}. Reason: {reason}",
            source=vessel.name, confidence=1.0,
        )
    claims_added.append(claim_id)

    # 2. The vessel signs a contract with the counterparty.
    contract_id = network.contract(
        party_a=vessel.name, party_b=counterparty,
        about_secret_id=len(vessel.bearing.entrusted) - 1,
        terms=f"Question: {question}\nChoice: {choice}\nReason: {reason}",
        binding=True,
    )

    # 3. Record the choice in the vessel's bearing (already done by caller).

    return {
        "claim_id": claim_id,
        "contract_id": contract_id,
        "canary": network.canary(),
        "ts": ts,
    }

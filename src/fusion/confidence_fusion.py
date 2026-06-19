"""
FAKTA - Confidence Fusion Engine (REVISED)

CRITICAL FIX: Evidence quality is a CONFIDENCE MULTIPLIER, not an independent hoax-directional score.
This fixes the original bug where relevance/credibility/recency were added directly to the hoax score,
which caused evidence that SUPPORTS a claim to also increase the hoax score.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class FusionResult:
    """Result from confidence fusion."""
    final_hoax_score: float       # [0, 1] — 1 = definitely hoax
    confidence: float              # [0, 1] — how sure we are
    verdict: str                   # "Hoax" | "Tidak Hoax" | "Tidak Cukup Bukti"
    verdict_raw: str               # "Refuted" | "Supported" | "NotEnoughEvidence"
    mode: str                      # "strong_evidence" | "weak_evidence" | "no_evidence"
    llm_signal_raw: float          # Raw LLM signal [-1, +1]
    evidence_quality: float        # Quality of evidence [0, 1]


def compute_evidence_quality(evidence_results: List[Dict]) -> float:
    """
    Compute evidence quality index [0, 1].
    Does NOT indicate hoax direction — only how reliable the evidence is.

    Args:
        evidence_results: List of evidence dicts with:
            - relevance_score: [0, 1] how relevant to claim
            - source_credibility: [0, 1] credibility of source
            - recency_score: [0, 1] how recent the evidence is

    Returns:
        Evidence quality index [0, 1]
    """
    if not evidence_results:
        return 0.0

    top = evidence_results[0]
    relevance = top.get("relevance_score", 0.0)
    credibility = top.get("source_credibility", 0.0)
    recency = top.get("recency_score", 0.0)

    quality = (
        0.50 * relevance
        + 0.30 * credibility
        + 0.20 * recency
    )

    return min(quality, 1.0)


def compute_evidence_conflict(llm_verdicts: List[str]) -> float:
    """
    Compute evidence conflict score [0, 1].
    0 = all evidence agrees, 1 = direct contradiction.
    """
    if len(llm_verdicts) <= 1:
        return 0.0

    supported = sum(1 for v in llm_verdicts if v == "Supported")
    refuted = sum(1 for v in llm_verdicts if v == "Refuted")

    if supported > 0 and refuted > 0:
        total_verifiable = supported + refuted
        # 0.5 if evenly split, approaching 1.0 if heavily one-sided but still split
        return min(supported / total_verifiable, refuted / total_verifiable) * 2.0

    return 0.0


def fuse_claim_verdict(
    lstm_hoax: float,
    llm_verdict: str,
    llm_confidence: float,
    evidence_quality: float,
    evidence_conflict: float = 0.0,
    linguistic_hoax: float = 0.0,
    nei_reason: Optional[str] = None,
    quality_threshold: float = 0.50,
    hoax_threshold: float = 0.70,
    valid_threshold: float = 0.30,
) -> FusionResult:
    """
    Fuse LSTM, LLM, and evidence signals into final verdict.

    REGIME-BASED FUSION:
    - Strong evidence (quality >= threshold): trust LLM + evidence heavily
    - Weak evidence (0 < quality < threshold): lean on LSTM, low confidence
    - No evidence (quality == 0): LSTM-only, pull toward NEI (0.5)

    Args:
        lstm_hoax: LSTM hoax probability [0, 1]
        llm_verdict: "Supported" | "Refuted" | "NotEnoughEvidence"
        llm_confidence: LLM confidence in verdict [0, 1]
        evidence_quality: Evidence quality index [0, 1]
        evidence_conflict: Evidence conflict index [0, 1]
        linguistic_hoax: Linguistic hoax score [0, 1]
        nei_reason: Why NEI — "no_search_results" | "ambiguous" | None
        quality_threshold: Boundary between strong and weak evidence
        hoax_threshold: Score above which verdict is "Hoax"
        valid_threshold: Score below which verdict is "Tidak Hoax"

    Returns:
        FusionResult with final score, confidence, and verdict
    """
    # Step 1: Convert LLM verdict to directional signal
    # +1.0 = Refuted (hoax direction), -1.0 = Supported (valid direction), 0 = NEI
    if llm_verdict == "Refuted":
        llm_signal = llm_confidence       # positive → hoax direction
    elif llm_verdict == "Supported":
        llm_signal = -llm_confidence      # negative → valid direction
    else:  # NotEnoughEvidence
        # KEY FIX: NEI from "no search results" is NEUTRAL, not a hoax signal
        if nei_reason == "no_search_results":
            llm_signal = 0.0
        else:  # ambiguous evidence
            llm_signal = 0.0

    # Convert from [-1, +1] to [0, 1] for fusion
    llm_hoax_normalized = (llm_signal + 1.0) / 2.0

    # Step 2: Regime-based fusion
    has_evidence = evidence_quality > 0.0

    if evidence_quality >= quality_threshold:
        # === STRONG EVIDENCE REGIME ===
        mode = "strong_evidence"
        final_hoax = (
            0.25 * lstm_hoax
            + 0.50 * llm_hoax_normalized
            + 0.10 * linguistic_hoax
        )
        # Confidence based on evidence quality, reduced by conflict
        confidence = evidence_quality * (1.0 - evidence_conflict * 0.3)

    elif has_evidence:
        # === WEAK EVIDENCE REGIME ===
        mode = "weak_evidence"
        final_hoax = (
            0.55 * lstm_hoax
            + 0.10 * llm_hoax_normalized
            + 0.25 * linguistic_hoax
        )
        confidence = evidence_quality * 0.5  # Low confidence by design

    else:
        # === NO EVIDENCE REGIME ===
        mode = "no_evidence"
        # Normalize weights
        norm = 0.55 + 0.25  # 0.80
        final_hoax = (
            (0.55 / norm) * lstm_hoax
            + (0.25 / norm) * linguistic_hoax
        )
        # Pull toward 0.5 (NEI) if LSTM is uncertain
        lstm_uncertainty = 1.0 - abs(lstm_hoax - 0.5) * 2.0
        final_hoax = final_hoax * (1.0 - 0.4 * lstm_uncertainty) + 0.5 * 0.4 * lstm_uncertainty
        confidence = 0.3 + 0.2 * (1.0 - lstm_uncertainty)

    # Clamp
    final_hoax = max(0.0, min(1.0, final_hoax))
    confidence = max(0.0, min(1.0, confidence))

    # Step 3: Map to verdict
    if final_hoax >= hoax_threshold:
        verdict = "Hoax"
        verdict_raw = "Refuted"
    elif final_hoax <= valid_threshold:
        verdict = "Tidak Hoax"
        verdict_raw = "Supported"
    else:
        verdict = "Tidak Cukup Bukti"
        verdict_raw = "NotEnoughEvidence"

    return FusionResult(
        final_hoax_score=round(final_hoax, 4),
        confidence=round(confidence, 4),
        verdict=verdict,
        verdict_raw=verdict_raw,
        mode=mode,
        llm_signal_raw=round(llm_signal, 4),
        evidence_quality=round(evidence_quality, 4),
    )


# ============ DEMO / TEST ============

def demo():
    """Demonstrate the fusion engine with original document examples."""
    print("=" * 70)
    print("FAKTA Confidence Fusion Engine — DEMO")
    print("=" * 70)

    # Example 1: Claim refuted by strong evidence
    print("\n--- Example 1: Strong evidence, claim refuted ---")
    r1 = fuse_claim_verdict(
        lstm_hoax=0.74,
        llm_verdict="Refuted",
        llm_confidence=0.88,
        evidence_quality=0.89,  # relevance=0.86, credibility=1.0, recency=0.82
        evidence_conflict=0.0,
        linguistic_hoax=0.20,
    )
    print(f"  Final hoax score: {r1.final_hoax_score}")
    print(f"  Confidence:       {r1.confidence}")
    print(f"  Verdict:          {r1.verdict}")
    print(f"  Mode:             {r1.mode}")
    print(f"  LLM signal:       {r1.llm_signal_raw}")

    # Example 2: LSTM suspects hoax, but no evidence
    print("\n--- Example 2: LSTM suspects hoax, no evidence ---")
    r2 = fuse_claim_verdict(
        lstm_hoax=0.76,
        llm_verdict="NotEnoughEvidence",
        llm_confidence=0.60,
        evidence_quality=0.0,  # No evidence found
        linguistic_hoax=0.15,
        nei_reason="no_search_results",
    )
    print(f"  Final hoax score: {r2.final_hoax_score}")
    print(f"  Confidence:       {r2.confidence}")
    print(f"  Verdict:          {r2.verdict}")
    print(f"  Mode:             {r2.mode}")

    # Example 3: Evidence SUPPORTS the claim (not hoax)
    print("\n--- Example 3: Strong evidence SUPPORTS claim (valid) ---")
    r3 = fuse_claim_verdict(
        lstm_hoax=0.85,  # LSTM thinks it looks like hoax (provocative language)
        llm_verdict="Supported",
        llm_confidence=0.90,
        evidence_quality=0.85,
        linguistic_hoax=0.25,
    )
    print(f"  Final hoax score: {r3.final_hoax_score}")
    print(f"  Confidence:       {r3.confidence}")
    print(f"  Verdict:          {r3.verdict}")
    print(f"  Mode:             {r3.mode}")
    print(f"  LLM signal:       {r3.llm_signal_raw}")
    print("  NOTE: Despite LSTM=0.85, evidence overrides → Tidak Hoax!")

    # Example 4: Conflicting evidence
    print("\n--- Example 4: Conflicting evidence ---")
    r4 = fuse_claim_verdict(
        lstm_hoax=0.60,
        llm_verdict="Refuted",
        llm_confidence=0.70,
        evidence_quality=0.70,
        evidence_conflict=0.6,  # Some evidence supports, some refutes
        linguistic_hoax=0.15,
    )
    print(f"  Final hoax score: {r4.final_hoax_score}")
    print(f"  Confidence:       {r4.confidence}")
    print(f"  Verdict:          {r4.verdict}")
    print(f"  Mode:             {r4.mode}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    demo()

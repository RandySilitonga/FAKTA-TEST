"""
FAKTA - Article-Level Aggregation

Replaces the broken "1 hoax = article hoax" rule with weighted aggregation
based on claim importance, claim type, and proportion.
"""

from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ClaimVerdict:
    """Verdict for a single claim."""
    claim_text: str
    claim_type: str
    importance: float
    verdict: str           # "Hoax" | "Tidak Hoax" | "Tidak Cukup Bukti"
    final_hoax_score: float
    confidence: float
    mode: str
    evidence_sources: List[str]
    reasoning: str

    def to_dict(self) -> Dict:
        return asdict(self)


# Claim type priority weights
CLAIM_TYPE_WEIGHTS = {
    "factual": 1.0,       # Most important — direct factual claims
    "causal": 1.0,        # Cause-effect claims are critical
    "statistical": 0.8,   # Statistical claims
    "attribution": 0.6,   # Attribution claims (less critical)
    "opinion": 0.0,       # Opinions are not verified
}


def aggregate_article_verdicts(
    claim_verdicts: List[ClaimVerdict],
) -> Dict:
    """
    Aggregate multiple claim verdicts into an article-level verdict.

    Rules:
    - Opinion claims are skipped (weight 0)
    - Each claim weighted by importance × claim_type_weight
    - Weighted average of hoax scores
    - If ANY high-weight claim is Hoax with high confidence → article = Hoax
    - If ALL verifiable claims are Tidak Hoax → article = Tidak Hoax
    - Otherwise → Tidak Cukup Bukti

    Args:
        claim_verdicts: List of claim verdicts

    Returns:
        Article-level verdict dict
    """
    if not claim_verdicts:
        return {
            "verdict": "Tidak dapat diverifikasi",
            "confidence": 0.0,
            "summary": "Tidak ada klaim faktual yang dapat diverifikasi.",
            "claims": [],
        }

    # Filter out opinion claims
    verifiable = [
        cv for cv in claim_verdicts
        if CLAIM_TYPE_WEIGHTS.get(cv.claim_type, 0.0) > 0.0
    ]

    if not verifiable:
        return {
            "verdict": "Tidak dapat diverifikasi",
            "confidence": 0.0,
            "summary": "Semua klaim dalam artikel bersifat opini dan tidak dapat diverifikasi.",
            "claims": [cv.to_dict() for cv in claim_verdicts],
        }

    # Compute weighted hoax score
    total_weight = 0.0
    weighted_hoax_sum = 0.0
    weighted_confidence_sum = 0.0

    high_confidence_hoax = False

    for cv in verifiable:
        weight = cv.importance * CLAIM_TYPE_WEIGHTS.get(cv.claim_type, 0.5)
        total_weight += weight
        weighted_hoax_sum += weight * cv.final_hoax_score
        weighted_confidence_sum += weight * cv.confidence

        # Check for high-confidence hoax
        if cv.verdict == "Hoax" and cv.confidence >= 0.70 and weight >= 0.5:
            high_confidence_hoax = True

    avg_hoax = weighted_hoax_sum / total_weight if total_weight > 0 else 0.5
    avg_confidence = weighted_confidence_sum / total_weight if total_weight > 0 else 0.0

    # Determine verdict
    hoax_claims = sum(1 for cv in verifiable if cv.verdict == "Hoax")
    valid_claims = sum(1 for cv in verifiable if cv.verdict == "Tidak Hoax")
    nei_claims = sum(1 for cv in verifiable if cv.verdict == "Tidak Cukup Bukti")

    if high_confidence_hoax and hoax_claims > valid_claims:
        verdict = "Hoax"
        summary = (
            f"Artikel mengandung {hoax_claims} klaim yang dibantah oleh sumber kredibel. "
            f"Dari {len(verifiable)} klaim faktual, {valid_claims} didukung evidence "
            f"dan {nei_claims} tidak cukup bukti."
        )
    elif valid_claims == len(verifiable):
        verdict = "Tidak Hoax"
        summary = f"Semua {len(verifiable)} klaim faktual didukung oleh evidence."
    elif nei_claims > 0 and hoax_claims == 0:
        verdict = "Tidak Cukup Bukti"
        summary = (
            f"Tidak ada klaim yang dibantah, namun {nei_claims} dari {len(verifiable)} "
            f"klaim tidak memiliki evidence yang cukup."
        )
    else:
        verdict = "Tidak Cukup Bukti"
        summary = (
            f"Campuran verdict: {hoax_claims} hoax, {valid_claims} valid, "
            f"{nei_claims} tidak cukup bukti dari {len(verifiable)} klaim faktual."
        )

    return {
        "verdict": verdict,
        "confidence": round(avg_confidence, 4),
        "avg_hoax_score": round(avg_hoax, 4),
        "summary": summary,
        "claims": [cv.to_dict() for cv in claim_verdicts],
        "claim_stats": {
            "total_claims": len(claim_verdicts),
            "verifiable_claims": len(verifiable),
            "hoax_claims": hoax_claims,
            "valid_claims": valid_claims,
            "nei_claims": nei_claims,
        },
    }


if __name__ == "__main__":
    from confidence_fusion import fuse_claim_verdict

    # Simulate: article with 3 claims
    claims_data = [
        {"text": "Matcha menyebabkan gagal ginjal", "type": "causal", "importance": 1.0, "lstm": 0.74, "llm_v": "Refuted", "llm_c": 0.88, "eq": 0.89},
        {"text": "BPOM sudah meneliti matcha", "type": "factual", "importance": 0.7, "lstm": 0.40, "llm_v": "Supported", "llm_c": 0.92, "eq": 0.85},
        {"text": "Matcha enak diminum panas", "type": "opinion", "importance": 0.3, "lstm": 0.20, "llm_v": "NotEnoughEvidence", "llm_c": 0.5, "eq": 0.0},
    ]

    verdicts = []
    for c in claims_data:
        r = fuse_claim_verdict(
            lstm_hoax=c["lstm"], llm_verdict=c["llm_v"], llm_confidence=c["llm_c"],
            evidence_quality=c["eq"], linguistic_hoax=0.1,
        )
        verdicts.append(ClaimVerdict(
            claim_text=c["text"], claim_type=c["type"], importance=c["importance"],
            verdict=r.verdict, final_hoax_score=r.final_hoax_score,
            confidence=r.confidence, mode=r.mode, evidence_sources=["Test"], reasoning="",
        ))

    result = aggregate_article_verdicts(verdicts)
    print(f"Article Verdict: {result['verdict']}")
    print(f"Confidence: {result['confidence']}")
    print(f"Summary: {result['summary']}")
    print(f"Stats: {result['claim_stats']}")

"""
FAKTA - Source Credibility and Recency Scoring
"""

from typing import Dict, Optional
from datetime import datetime


# Tier-based source credibility scores
SOURCE_CREDIBILITY = {
    # Tier 1: Fact-check APIs
    "google_factcheck": 1.0,

    # Tier 2: Official government
    "Kemenkes RI": 0.95,
    "BPOM": 0.95,
    "BMKG": 0.95,
    "Kominfo": 0.90,
    "KPU": 0.95,
    "Bawaslu": 0.90,
    "BI": 0.95,
    "OJK": 0.90,
    "BPS": 0.90,
    "WHO": 0.95,
    "BNPB": 0.90,

    # Tier 3: Media & fact-check
    "TurnBackHoax": 0.80,
    "CekFakta": 0.75,
    "Antara News": 0.70,
    "Kompas": 0.70,
    "Tempo": 0.70,
    "CNN Indonesia": 0.65,
    "Reuters": 0.80,
    "AP News": 0.80,
    "BBC": 0.75,

    # Tier 4: Wikipedia
    "Wikipedia": 0.40,
}


def get_source_credibility(source: str) -> float:
    """Get credibility score for a source."""
    return SOURCE_CREDIBILITY.get(source, 0.5)


def get_source_tier(source: str) -> int:
    """Get tier number for a source."""
    cred = get_source_credibility(source)
    if cred >= 0.95:
        return 2
    elif cred >= 0.70:
        return 3
    elif cred >= 0.40:
        return 4
    else:
        return 3  # Default to tier 3


def compute_recency_score(date_str: Optional[str]) -> float:
    """
    Compute recency score from date string.

    Args:
        date_str: Date in YYYY-MM-DD format

    Returns:
        Recency score [0, 1] — 1.0 for fresh, decays over time
    """
    if not date_str:
        return 0.5

    try:
        pub_date = datetime.strptime(date_str, "%Y-%m-%d")
        days_ago = (datetime.now() - pub_date).days

        if days_ago <= 30:
            return 1.0
        elif days_ago <= 90:
            return 0.9
        elif days_ago <= 180:
            return 0.7
        elif days_ago <= 365:
            return 0.5
        elif days_ago <= 730:
            return 0.3
        else:
            return 0.1
    except (ValueError, TypeError):
        return 0.5


def score_evidence(evidence: Dict) -> Dict:
    """
    Score a single evidence item for relevance, credibility, and recency.

    Args:
        evidence: Evidence dict

    Returns:
        Evidence dict with added score fields
    """
    source = evidence.get("source", "")

    evidence["source_credibility"] = get_source_credibility(source)
    evidence["source_tier"] = get_source_tier(source)
    evidence["recency_score"] = compute_recency_score(
        evidence.get("date_published") or evidence.get("date")
    )

    # Relevance is typically computed by the retriever
    if "relevance_score" not in evidence:
        evidence["relevance_score"] = 0.5  # Default

    return evidence


if __name__ == "__main__":
    sources = ["BPOM", "TurnBackHoax", "Kompas", "Wikipedia", "Unknown Source"]
    for s in sources:
        print(f"  {s}: credibility={get_source_credibility(s)}, tier={get_source_tier(s)}")

    dates = ["2026-06-01", "2026-03-01", "2025-12-01", "2024-01-01", ""]
    for d in dates:
        print(f"  {d or 'None'}: recency={compute_recency_score(d):.2f}")

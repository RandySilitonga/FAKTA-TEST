"""
FAKTA - Pydantic API Schemas
Request/response schemas for the FastAPI backend.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict


class CheckRequest(BaseModel):
    """Request to check an article/post for hoaxes."""
    text: str = Field(..., min_length=10, max_length=10000, description="Full article or post text")
    title: Optional[str] = Field(None, max_length=500, description="Article title (optional)")
    url: Optional[str] = Field(None, description="Article URL (optional)")


class ClaimResult(BaseModel):
    """Result for a single claim."""
    claim_text: str
    claim_type: str
    verdict: str  # "Hoax" | "Tidak Hoax" | "Tidak Cukup Bukti"
    final_hoax_score: float
    confidence: float
    mode: str  # "strong_evidence" | "weak_evidence" | "no_evidence"
    lstm_hoax_proba: float
    llm_verdict: str  # "Supported" | "Refuted" | "NotEnoughEvidence"
    llm_confidence: float
    evidence_sources: List[str]
    reasoning: str


class CheckResponse(BaseModel):
    """Full response from the FAKTA system."""
    verdict: str  # "Hoax" | "Tidak Hoax" | "Tidak Cukup Bukti" | "Tidak dapat diverifikasi"
    confidence: float
    avg_hoax_score: float
    summary: str
    claims: List[ClaimResult]
    claim_stats: Dict
    processing_time_ms: float


class FeedbackRequest(BaseModel):
    """Human feedback on a system verdict."""
    claim: str
    system_verdict: str
    human_verdict: str  # "Hoax" | "Tidak Hoax" | "Tidak Cukup Bukti"
    is_correct: bool
    notes: Optional[str] = None


class FeedbackResponse(BaseModel):
    """Response after recording feedback."""
    success: bool
    message: str


class HealthResponse(BaseModel):
    """System health check."""
    status: str
    version: str
    components: Dict[str, str]

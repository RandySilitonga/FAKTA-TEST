"""
FAKTA - FastAPI Backend
REST API for the FAKTA fact-checking system.
"""

import os
import time
import logging
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from schemas import (
    CheckRequest, CheckResponse, ClaimResult,
    FeedbackRequest, FeedbackResponse, HealthResponse,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="FAKTA API",
    description="Fact-Checking AI — Hybrid LSTM + LLM + Evidence",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# Pipeline Components (lazy initialization)
# ============================================================

class FAKTAPipeline:
    """End-to-end fact-checking pipeline."""

    def __init__(self):
        self._initialized = False
        self._preprocessor = None
        self._claim_extractor = None
        self._lstm_predictor = None
        self._retriever = None
        self._factcheck_api = None
        self._wikipedia = None
        self._judge = None
        self._cache = None

    def initialize(self):
        """Initialize all pipeline components."""
        if self._initialized:
            return

        logger.info("Initializing FAKTA pipeline...")

        # Preprocessing
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from preprocessing.cleaning import clean_text
        from preprocessing.slang_normalizer import normalize_slang
        from preprocessing.feature_extractor import extract_features
        self._preprocessor = {
            "clean": clean_text,
            "normalize": normalize_slang,
            "extract_features": extract_features,
        }

        # Claim extraction
        from claim_extraction.gemini_extractor import GeminiClaimExtractor
        self._claim_extractor = GeminiClaimExtractor()

        # Evidence retrieval
        from evidence.retriever import HybridRetriever
        self._retriever = HybridRetriever()

        from evidence.factcheck_api import GoogleFactCheckAPI
        self._factcheck_api = GoogleFactCheckAPI()

        from evidence.wikipedia_fallback import WikipediaFallback
        self._wikipedia = WikipediaFallback()

        # LLM Judge
        from judge.gemini_evidence_judge import GeminiEvidenceJudge
        self._judge = GeminiEvidenceJudge()

        # Cache
        from evidence.cache import EvidenceCache
        self._cache = EvidenceCache()

        # LSTM (optional — may not be trained yet)
        model_path = "models/lstm/lstm_model.keras"
        if os.path.exists(model_path):
            from classifier.lstm_model import LSTMPredictor
            self._lstm_predictor = LSTMPredictor(model_path)
            logger.info("LSTM model loaded")
        else:
            logger.warning("LSTM model not found, using fallback")
            self._lstm_predictor = None

        self._initialized = True
        logger.info("FAKTA pipeline initialized")

    def process(self, text: str, title: Optional[str] = None) -> dict:
        """
        Run full fact-checking pipeline on text.

        Args:
            text: Article/post text
            title: Optional title

        Returns:
            Full result dict
        """
        start_time = time.time()

        self.initialize()

        # Step 1: Preprocessing
        full_text = f"{title or ''}\n{text}"
        cleaned = self._preprocessor["clean"](full_text)
        normalized = self._preprocessor["normalize"](cleaned)
        linguistic_feats = self._preprocessor["extract_features"](normalized)
        linguistic_hoax = linguistic_feats.hoax_score()

        # Step 2: Claim extraction
        claims = self._claim_extractor.extract_claims(normalized)

        if not claims:
            elapsed = (time.time() - start_time) * 1000
            return {
                "verdict": "Tidak dapat diverifikasi",
                "confidence": 0.0,
                "avg_hoax_score": 0.5,
                "summary": "Tidak ada klaim faktual yang dapat diekstrak.",
                "claims": [],
                "claim_stats": {"total_claims": 0, "verifiable_claims": 0},
                "processing_time_ms": round(elapsed, 1),
            }

        # Step 3: Process each claim
        claim_results = []

        for claim in claims:
            # Skip opinion claims
            if claim.claim_type == "opinion":
                continue

            # LSTM prediction
            lstm_proba = {"hoax": 0.5, "valid": 0.25, "uncertain": 0.25}
            if self._lstm_predictor:
                lstm_proba = self._lstm_predictor.predict(normalized)

            # Evidence retrieval
            evidence = []

            # Google Fact Check
            if self._factcheck_api.api_key:
                fc_results = self._factcheck_api.search(claim.claim_text)
                evidence.extend(fc_results)

            # Local database
            local_results = self._retriever.search(claim.claim_text, top_k=3)
            evidence.extend(local_results)

            # Wikipedia fallback
            if len(evidence) < 2:
                wiki_results = self._wikipedia.search(claim.claim_text)
                evidence.extend(wiki_results)

            # Determine NEI reason
            nei_reason = None
            if not evidence:
                nei_reason = "no_search_results"

            # LLM Evidence Judge
            if evidence:
                judge_result = self._judge.judge(
                    claim.claim_text, evidence, claim.claim_id
                )
                llm_verdict = judge_result.llm_verdict
                llm_confidence = judge_result.llm_confidence
                reasoning = judge_result.reasoning
                evidence_sources = [ev.get("source", "Unknown") for ev in evidence[:3]]
            else:
                llm_verdict = "NotEnoughEvidence"
                llm_confidence = 0.3
                reasoning = "Tidak ada evidence yang ditemukan."
                evidence_sources = []

            # Fusion
            from fusion.confidence_fusion import (
                fuse_claim_verdict, compute_evidence_quality,
            )
            evidence_quality = compute_evidence_quality(evidence)

            fusion_result = fuse_claim_verdict(
                lstm_hoax=lstm_proba.get("hoax", 0.5),
                llm_verdict=llm_verdict,
                llm_confidence=llm_confidence,
                evidence_quality=evidence_quality,
                linguistic_hoax=linguistic_hoax,
                nei_reason=nei_reason,
            )

            claim_results.append(ClaimResult(
                claim_text=claim.claim_text,
                claim_type=claim.claim_type,
                verdict=fusion_result.verdict,
                final_hoax_score=fusion_result.final_hoax_score,
                confidence=fusion_result.confidence,
                mode=fusion_result.mode,
                lstm_hoax_proba=lstm_proba.get("hoax", 0.5),
                llm_verdict=llm_verdict,
                llm_confidence=llm_confidence,
                evidence_sources=evidence_sources,
                reasoning=reasoning,
            ))

        # Step 4: Article aggregation
        from fusion.aggregation import (
            aggregate_article_verdicts, ClaimVerdict,
        )

        claim_verdicts = [
            ClaimVerdict(
                claim_text=cr.claim_text,
                claim_type=cr.claim_type,
                importance=1.0,
                verdict=cr.verdict,
                final_hoax_score=cr.final_hoax_score,
                confidence=cr.confidence,
                mode=cr.mode,
                evidence_sources=cr.evidence_sources,
                reasoning=cr.reasoning,
            )
            for cr in claim_results
        ]

        article_result = aggregate_article_verdicts(claim_verdicts)

        elapsed = (time.time() - start_time) * 1000

        return {
            "verdict": article_result["verdict"],
            "confidence": article_result["confidence"],
            "avg_hoax_score": article_result.get("avg_hoax_score", 0.5),
            "summary": article_result["summary"],
            "claims": claim_results,
            "claim_stats": article_result.get("claim_stats", {}),
            "processing_time_ms": round(elapsed, 1),
        }


# Global pipeline instance
pipeline = FAKTAPipeline()


# ============================================================
# Routes
# ============================================================

@app.get("/", response_model=HealthResponse)
def health_check():
    return HealthResponse(
        status="healthy",
        version="2.0.0",
        components={
            "lstm": "loaded" if pipeline._lstm_predictor else "not_loaded",
            "retriever": "initialized" if pipeline._retriever else "not_initialized",
            "judge": "initialized" if pipeline._judge else "not_initialized",
        },
    )


@app.post("/check", response_model=CheckResponse)
def check_article(request: CheckRequest):
    """
    Check an article/post for hoaxes.
    """
    try:
        result = pipeline.process(request.text, request.title)
        return CheckResponse(**result)
    except Exception as e:
        logger.error(f"Error processing request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest):
    """
    Submit human feedback on a system verdict.
    """
    # Save feedback for analysis
    feedback_dir = Path("data/evaluation")
    feedback_dir.mkdir(parents=True, exist_ok=True)

    feedback_file = feedback_dir / "feedback.jsonl"
    with open(feedback_file, "a", encoding="utf-8") as f:
        import json
        f.write(json.dumps(request.model_dump(), ensure_ascii=False) + "\n")

    return FeedbackResponse(
        success=True,
        message="Feedback recorded. Terima kasih!",
    )


@app.get("/stats")
def get_stats():
    """Get system statistics."""
    return {
        "pipeline_initialized": pipeline._initialized,
        "cache_stats": pipeline._cache.get_stats() if pipeline._cache else {},
        "retriever_stats": pipeline._retriever.get_stats() if pipeline._retriever else {},
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

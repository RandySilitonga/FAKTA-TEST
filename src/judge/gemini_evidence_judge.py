"""
FAKTA - Gemini Evidence Judge Module
LLM reads claim + evidence and produces a verdict: Supported / Refuted / NotEnoughEvidence.
"""

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import hashlib
import re


@dataclass
class JudgeResult:
    """Result from LLM evidence judgment."""
    claim_id: int
    llm_verdict: str  # "Supported", "Refuted", "NotEnoughEvidence"
    llm_confidence: float  # 0.0 to 1.0
    reasoning: str
    evidence_used: List[str]  # which evidence pieces were used

    def to_dict(self) -> Dict:
        return asdict(self)


_judge_cache: Dict[str, JudgeResult] = {}


class GeminiEvidenceJudge:
    """Uses Gemini to judge whether evidence supports or refutes a claim."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash"):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy initialization."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def judge(self, claim_text: str, evidence_list: List[Dict], claim_id: int = 0) -> JudgeResult:
        """
        Judge whether evidence supports or refutes the claim.

        Args:
            claim_text: The claim to verify
            evidence_list: List of evidence dicts with "source", "text", "url"
            claim_id: ID for tracking

        Returns:
            JudgeResult with verdict, confidence, reasoning
        """
        # Check cache
        cache_key = hashlib.md5(f"{claim_text}{json.dumps(evidence_list)}".encode()).hexdigest()
        if cache_key in _judge_cache:
            return _judge_cache[cache_key]

        prompt = self._build_prompt(claim_text, evidence_list)

        try:
            client = self._get_client()
            response = client.generate_content(prompt)
            raw = response.text.strip()
            result = self._parse_response(raw, claim_id, evidence_list)

            _judge_cache[cache_key] = result
            return result

        except Exception as e:
            print(f"[EvidenceJudge] Gemini API error: {e}")
            # Fallback: no evidence = NEI
            if not evidence_list:
                return JudgeResult(
                    claim_id=claim_id,
                    llm_verdict="NotEnoughEvidence",
                    llm_confidence=0.5,
                    reasoning="Tidak ada evidence yang ditemukan.",
                    evidence_used=[],
                )
            # Default: conservative NEI
            return JudgeResult(
                claim_id=claim_id,
                llm_verdict="NotEnoughEvidence",
                llm_confidence=0.3,
                reasoning="Error pada LLM judge, menggunakan fallback NEI.",
                evidence_used=[],
            )

    def _build_prompt(self, claim_text: str, evidence_list: List[Dict]) -> str:
        evidence_str = ""
        for i, ev in enumerate(evidence_list):
            evidence_str += f"""
Evidence {i + 1}:
- Source: {ev.get("source", "Unknown")}
- URL: {ev.get("url", "N/A")}
- Text: {ev.get("text", "")}
"""

        return f"""Kamu adalah asisten fact-checking profesional.

TUGAS: Analisis klaim berikut HANYA berdasarkan evidence yang diberikan.

KLAIM: "{claim_text}"

{evidence_str if evidence_str else "TIDAK ADA EVIDENCE DITEMUKAN."}

ATURAN PENTING:
1. JANGAN gunakan pengetahuan di luar evidence yang diberikan.
2. Jika evidence MENDUKUNG klaim → verdict: "Supported"
3. Jika evidence MEMBANTAH klaim → verdict: "Refuted"
4. Jika evidence TIDAK CUKUP atau tidak relevan → verdict: "NotEnoughEvidence"
5. Jika TIDAK ADA evidence → verdict: "NotEnoughEvidence"
6. Berikan confidence 0.0 sampai 1.0 dan reasoning singkat dalam Bahasa Indonesia.

Output HARUS dalam format JSON:
```json
{{
  "verdict": "Supported" atau "Refuted" atau "NotEnoughEvidence",
  "confidence": 0.85,
  "reasoning": "Penjelasan singkat dalam Bahasa Indonesia.",
  "evidence_used": [1, 2]
}}
```"""

    def _parse_response(self, raw: str, claim_id: int, evidence_list: List[Dict]) -> JudgeResult:
        """Parse LLM response into JudgeResult."""
        json_match = re.search(r'```json\s*(.*?)\s*```', raw, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = raw

        try:
            data = json.loads(json_str)
            verdict = data.get("verdict", "NotEnoughEvidence")
            confidence = float(data.get("confidence", 0.5))
            reasoning = data.get("reasoning", "")
            evidence_used = data.get("evidence_used", [])

            # Validate verdict
            valid_verdicts = ["Supported", "Refuted", "NotEnoughEvidence"]
            if verdict not in valid_verdicts:
                verdict = "NotEnoughEvidence"

            # Clamp confidence
            confidence = max(0.0, min(1.0, confidence))

            # Get evidence text for used indices
            used_texts = []
            for idx in evidence_used:
                if isinstance(idx, int) and 0 <= idx - 1 < len(evidence_list):
                    used_texts.append(evidence_list[idx - 1].get("text", ""))

            return JudgeResult(
                claim_id=claim_id,
                llm_verdict=verdict,
                llm_confidence=confidence,
                reasoning=reasoning,
                evidence_used=used_texts,
            )

        except (json.JSONDecodeError, ValueError) as e:
            print(f"[EvidenceJudge] Failed to parse JSON: {e}")
            return JudgeResult(
                claim_id=claim_id,
                llm_verdict="NotEnoughEvidence",
                llm_confidence=0.3,
                reasoning="Gagal parsing response LLM.",
                evidence_used=[],
            )


if __name__ == "__main__":
    judge = GeminiEvidenceJudge()

    claim = "Matcha menyebabkan gagal ginjal"
    evidence = [
        {
            "source": "Kemenkes RI",
            "url": "https://kemkes.go.id/...",
            "text": "Tidak ada bukti medis bahwa konsumsi matcha normal menyebabkan gagal ginjal.",
        }
    ]

    result = judge.judge(claim, evidence)
    print(f"Verdict: {result.llm_verdict}")
    print(f"Confidence: {result.llm_confidence}")
    print(f"Reasoning: {result.reasoning}")

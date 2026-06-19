"""
FAKTA - Gemini Claim Extraction Module
Extracts factual claims from article text using Gemini LLM.
"""

import json
import os
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import hashlib
import re


@dataclass
class Claim:
    """Represents an extracted factual claim."""
    claim_id: int
    claim_text: str
    claim_type: str  # factual, causal, statistical, attribution, opinion
    entities: List[str]
    importance: float = 1.0  # 1.0 = main claim, 0.5 = side claim

    def to_dict(self) -> Dict:
        return asdict(self)


# Simple cache to avoid repeated API calls for same text
_claim_cache: Dict[str, List[Claim]] = {}


class GeminiClaimExtractor:
    """Extracts factual claims from text using Gemini API."""

    def __init__(self, api_key: Optional[str] = None, model: str = "gemini-2.0-flash-lite"):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        self._client = None

    def _get_client(self):
        """Lazy initialization of Gemini client."""
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._client = genai.GenerativeModel(self.model)
        return self._client

    def extract_claims(self, text: str, max_claims: int = 10) -> List[Claim]:
        """
        Extract factual claims from article text.

        Args:
            text: Full article/post text
            max_claims: Maximum number of claims to extract

        Returns:
            List of Claim objects
        """
        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in _claim_cache:
            return _claim_cache[cache_key]

        prompt = self._build_prompt(text, max_claims)

        try:
            client = self._get_client()
            response = client.generate_content(prompt)
            raw = response.text.strip()

            claims = self._parse_response(raw, text)

            # Cache
            _claim_cache[cache_key] = claims
            return claims

        except Exception as e:
            print(f"[ClaimExtractor] Gemini API error: {e}")
            # Fallback: return sentence-level candidates
            return self._fallback_extraction(text, max_claims)

    def _build_prompt(self, text: str, max_claims: int) -> str:
        return f"""Kamu adalah asisten ekstraksi klaim untuk sistem fact-checking.

Tugas: Ekstrak klaim faktual dari teks berikut yang bisa diverifikasi kebenarannya.

Teks:
{text}

Instruksi:
1. Identifikasi klaim faktual yang bisa dicek kebenarannya.
2. Untuk setiap klaim, tentukan tipe:
   - "factual": pernyataan tentang kejadian/fakta
   - "causal": klaim sebab-akibat (X menyebabkan Y)
   - "statistical": klaim dengan angka/statistik
   - "attribution": klaim yang mengutip sumber tertentu
   - "opinion": pendapat/pernyataan subjektif (TIDAK perlu diverifikasi)
3. Ekstrak entitas kunci (nama orang, organisasi, produk, dll)
4. Berikan skor importance: 1.0 = klaim utama, 0.7 = klaim pendukung, 0.3 = klaim sampingan
5. Maksimal {max_claims} klaim.

Output HARUS dalam format JSON array:
```json
[
  {{
    "claim_id": 1,
    "claim_text": "Klaim di sini",
    "claim_type": "factual",
    "entities": ["entitas1", "entitas2"],
    "importance": 1.0
  }}
]
```

Hanya output JSON, tanpa penjelasan lain."""

    def _parse_response(self, raw: str, original_text: str) -> List[Claim]:
        """Parse Gemini JSON response into Claim objects."""
        # Extract JSON from markdown code blocks
        json_match = re.search(r'```json\s*(.*?)\s*```', raw, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = raw

        try:
            data = json.loads(json_str)
            if not isinstance(data, list):
                data = [data]

            claims = []
            for item in data:
                if isinstance(item, dict) and "claim_text" in item:
                    claims.append(Claim(
                        claim_id=item.get("claim_id", len(claims) + 1),
                        claim_text=item.get("claim_text", ""),
                        claim_type=item.get("claim_type", "factual"),
                        entities=item.get("entities", []),
                        importance=item.get("importance", 1.0),
                    ))

            return claims

        except json.JSONDecodeError:
            print(f"[ClaimExtractor] Failed to parse JSON response, using fallback")
            return self._fallback_extraction(original_text)

    def _fallback_extraction(self, text: str, max_claims: int = 10) -> List[Claim]:
        """
        Rule-based fallback: split into sentences and treat each as a claim.
        Used when LLM fails.
        """
        import re

        # Split on sentence boundaries
        sentences = re.split(r'[.!?]+(?:\s|$)', text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 15]

        claims = []
        for i, sent in enumerate(sentences[:max_claims]):
            # Simple entity extraction (capitalized words)
            entities = re.findall(r'\b[A-Z][a-z]+\b', sent)

            claim_type = "factual"
            if any(w in sent.lower() for w in ["menyebabkan", "menimbulkan", "akibat", "karena"]):
                claim_type = "causal"
            elif re.search(r'\d+%', sent) or re.search(r'\d+\s*(orang|kasus|korban|persen)', sent):
                claim_type = "statistical"
            elif any(w in sent.lower() for w in ["menurut", "kata", "melansir"]):
                claim_type = "attribution"
            elif any(w in sent.lower() for w in ["seharusnya", "sebaiknya", "menurut saya", "saya rasa"]):
                claim_type = "opinion"

            claims.append(Claim(
                claim_id=i + 1,
                claim_text=sent,
                claim_type=claim_type,
                entities=entities[:5],
                importance=1.0 if i == 0 else 0.5,
            ))

        return claims


if __name__ == "__main__":
    sample = """Viral di media sosial! Matcha menyebabkan gagal ginjal dan sudah banyak korban meninggal.
    Menurut dr. Andi dari RS Cipto, konsumsi matcha berlebihan bisa berbahaya.
    Namun BPOM membantah klaim tersebut dan menyatakan matcha aman dikonsumsi."""

    extractor = GeminiClaimExtractor()
    # This will use fallback since no API key
    claims = extractor.extract_claims(sample)
    for c in claims:
        print(f"  [{c.claim_type}] {c.claim_text} (importance: {c.importance})")
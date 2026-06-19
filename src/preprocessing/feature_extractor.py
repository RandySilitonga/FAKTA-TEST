"""
FAKTA - Linguistic Feature Extractor
Extracts stylistic and linguistic features that indicate hoax-like patterns.
"""

import re
from typing import Dict, List
from dataclasses import dataclass, field


# Provocative words commonly used in hoax content
PROVOCATIVE_WORDS = [
    "viral", "heboh", "geger", "sebarkan", "sebarluaskan", "warga",
    "rakyat", "diamdiam", "disembunyikan", "menutupi", "bohong",
    "tipu", "penipuan", "kriminal", "mengerikan", "fatal", "bahaya",
    "waspadalah", "awas", "jangan", "segera", "darurat", "krisis",
    "terbongkar", "terkuak", "ternyata", "fakta", "bukti", "terbukti",
    "mengenaskan", "tragis", "menyedihkan", "parah", "gila", "kaget",
    "shock", "wow", "breaking", "hot", "sensasional",
]

URGENCY_WORDS = [
    "segera", "jangan sampai", "sebelum dihapus", "cepat", "buruan",
    "sebelum terlambat", "hari ini", "sekarang", "urgent", "penting",
    "harus", "wajib", "darurat",
]


@dataclass
class LinguisticFeatures:
    """Container for extracted linguistic features."""
    caps_ratio: float = 0.0
    exclamation_count: int = 0
    question_count: int = 0
    provocative_word_count: int = 0
    urgency_word_count: int = 0
    has_source_mention: bool = False
    has_date_mention: bool = False
    has_url: bool = False
    avg_word_length: float = 0.0
    word_count: int = 0
    sentence_count: int = 0
    ellipsis_count: int = 0
    all_caps_word_count: int = 0
    repeat_char_ratio: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary of numeric features."""
        return {
            "caps_ratio": self.caps_ratio,
            "exclamation_count": float(self.exclamation_count),
            "question_count": float(self.question_count),
            "provocative_word_count": float(self.provocative_word_count),
            "urgency_word_count": float(self.urgency_word_count),
            "has_source_mention": float(self.has_source_mention),
            "has_date_mention": float(self.has_date_mention),
            "has_url": float(self.has_url),
            "avg_word_length": self.avg_word_length,
            "word_count": float(self.word_count),
            "sentence_count": float(self.sentence_count),
            "ellipsis_count": float(self.ellipsis_count),
            "all_caps_word_count": float(self.all_caps_word_count),
            "repeat_char_ratio": self.repeat_char_ratio,
        }

    def hoax_score(self) -> float:
        """
        Compute a simple hoax-like score from features.
        Returns 0.0 (not hoax-like) to 1.0 (very hoax-like).
        """
        score = 0.0

        # High caps ratio is suspicious
        score += min(self.caps_ratio * 2.0, 0.20)

        # Exclamation marks
        score += min(self.exclamation_count * 0.05, 0.15)

        # Provocative words
        score += min(self.provocative_word_count * 0.03, 0.20)

        # Urgency words
        score += min(self.urgency_word_count * 0.05, 0.15)

        # No source mention (lack of sourcing is suspicious)
        if not self.has_source_mention:
            score += 0.10

        # Repeated characters (e.g., "SEBARKAAAAAN")
        score += min(self.repeat_char_ratio * 0.5, 0.10)

        # All caps words
        score += min(self.all_caps_word_count * 0.02, 0.10)

        return min(score, 1.0)


def extract_features(text: str) -> LinguisticFeatures:
    """
    Extract linguistic features from text.

    Args:
        text: Raw or cleaned text

    Returns:
        LinguisticFeatures dataclass
    """
    features = LinguisticFeatures()

    # Caps ratio
    alpha_chars = [c for c in text if c.isalpha()]
    if alpha_chars:
        features.caps_ratio = sum(1 for c in alpha_chars if c.isupper()) / len(alpha_chars)

    # Punctuation counts
    features.exclamation_count = text.count('!')
    features.question_count = text.count('?')
    features.ellipsis_count = len(re.findall(r'\.{3,}', text))

    # Word-level features
    words = text.split()
    features.word_count = len(words)

    if words:
        features.avg_word_length = sum(len(w) for w in words) / len(words)
        features.all_caps_word_count = sum(1 for w in words if w.isupper() and len(w) > 1)

    # Sentences
    sentences = re.split(r'[.!?]+', text)
    features.sentence_count = len([s for s in sentences if s.strip()])

    # Provocative words
    text_lower = text.lower()
    features.provocative_word_count = sum(
        1 for word in PROVOCATIVE_WORDS if word.lower() in text_lower
    )

    # Urgency words
    features.urgency_word_count = sum(
        1 for word in URGENCY_WORDS if word.lower() in text_lower
    )

    # Source mention (names of institutions, "menurut", "kata", etc.)
    source_patterns = [
        r"menurut", r"kata\s+\w+", r"melansir", r"dikutip\s+dari",
        r"berdasarkan", r"sumber\s*(?:dari|:)",
        r"bpom|kemenkes|bmkg|kominfo|who|kpu|bawaslu",
        r"antaramedia|kompas|tempo|cnn|reuters|bbc",
    ]
    features.has_source_mention = any(
        re.search(p, text_lower) for p in source_patterns
    )

    # Date mention
    date_patterns = [
        r"\d{1,2}\s+(?:januari|februari|maret|april|mei|juni|juli|agustus|september|oktober|november|desember)",
        r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}",
        r"(?:hari|kemarin|seminggu|sebulan|tahun)\s+(?:ini|lalu|depan)",
    ]
    features.has_date_mention = any(
        re.search(p, text_lower) for p in date_patterns
    )

    # URL presence
    features.has_url = bool(re.search(r'https?://|www\.', text))

    # Repeat character ratio (e.g., "SEBARKAAAAAN")
    repeat_pattern = re.compile(r'(.)\1{2,}')
    repeat_matches = repeat_pattern.findall(text)
    features.repeat_char_ratio = len(repeat_matches) / max(features.word_count, 1)

    return features


def extract_batch(texts: List[str]) -> List[LinguisticFeatures]:
    """Extract features from a batch of texts."""
    return [extract_features(t) for t in texts]


if __name__ == "__main__":
    test_hoax = "SEBARKAN!!! Matcha menyebabkan GAGAL GINJAL!!! Warga heboh!! Sebarkan sebelum dihapus!!!"
    test_normal = "BMKG mencatat gempa magnitudo 5.2 di Maluku pada tanggal 15 Januari 2025."

    f1 = extract_features(test_hoax)
    f2 = extract_features(test_normal)

    print(f"HOAX-like text:")
    print(f"  caps_ratio: {f1.caps_ratio:.3f}")
    print(f"  provocative_words: {f1.provocative_word_count}")
    print(f"  hoax_score: {f1.hoax_score():.3f}")
    print()
    print(f"Normal text:")
    print(f"  caps_ratio: {f2.caps_ratio:.3f}")
    print(f"  provocative_words: {f2.provocative_word_count}")
    print(f"  hoax_score: {f2.hoax_score():.3f}")

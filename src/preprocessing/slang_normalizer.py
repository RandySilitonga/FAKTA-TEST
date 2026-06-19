"""
FAKTA - Indonesian Slang Normalizer
Maps Indonesian slang/abbreviations to formal Indonesian.
"""

from typing import Dict, Optional
import re


# Comprehensive slang mapping (no duplicates)
SLANG_MAP: Dict[str, str] = {
    # Negation
    "gk": "tidak",
    "ga": "tidak",
    "gak": "tidak",
    "ngga": "tidak",
    "nggak": "tidak",
    "kagak": "tidak",

    # Common abbreviations
    "yg": "yang",
    "dgn": "dengan",
    "krn": "karena",
    "karna": "karena",
    "jgn": "jangan",
    "udh": "sudah",
    "udah": "sudah",
    "klo": "kalau",
    "kalo": "kalau",
    "sm": "sama",
    "dr": "dari",
    "tp": "tapi",
    "bgt": "banget",
    "dpt": "dapat",
    "dlm": "dalam",
    "gmn": "bagaimana",
    "gmna": "bagaimana",
    "kpn": "kapan",
    "kmrn": "kemarin",
    "skrg": "sekarang",
    "tdk": "tidak",
    "utk": "untuk",
    "dg": "dengan",
    "sy": "saya",
    "gw": "saya",
    "gue": "saya",
    "lo": "kamu",
    "lu": "kamu",
    "km": "kamu",
    "mrk": "mereka",
    "bs": "bisa",
    "mau": "mau",
    "mo": "mau",
    "kaga": "tidak",
    "ogah": "tidak mau",
    "emang": "memang",
    "mmg": "memang",
    "cuma": "hanya",
    "cm": "hanya",
    "cuman": "hanya",
    "cmn": "hanya",
    "sih": "",
    "deh": "",
    "dong": "",
    "lah": "",
    "kok": "",
    "kah": "",
    "nya": "",
    "nih": "ini",
    "tu": "itu",
    "gitu": "begitu",
    "gimana": "bagaimana",
    "kenape": "kenapa",
    "ngapain": "sedang apa",
    "nyampe": "sampai",
    "ampe": "sampai",
    "sampe": "sampai",
    "ntar": "nanti",
    "entar": "nanti",
    "nnt": "nanti",
    "blm": "belum",
    "belom": "belum",
    "bln": "bulan",
    "thn": "tahun",
    "hr": "hari",
    "jg": "juga",
    "aja": "saja",
    "baperr": "bawa perasaan",
    "caper": "cari perhatian",
    "cuk": "cukup",
    "cuy": "saudara",
    "gan": "juragan",
    "gercep": "gerak cepat",
    "gokil": "gila",
    "hadeh": "aduh",
    "jayus": "tidak lucu",
    "jomblo": "tidak punya pasangan",
    "kepo": "ingin tahu urusan orang",
    "mager": "malas bergerak",
    "ngab": "sedang",
    "ngakak": "tertawa",
    "njir": "anjir",
    "nobar": "nonton bareng",
    "nongkrong": "berkumpul",
    "otw": "di jalan",
    "pansos": "pencitraan sosial",
    "pepet": "desak",
    "php": "pemberi harapan palsu",
    "rempong": "repot",
    "santuy": "santai",
    "somasi": "ancaman",
    "sumpeh": "sumpah",
    "sumpah": "sumpah",
    "tepar": "sangat lelah",
    "tilang": "bukti pelanggaran",
    "wkwk": "tertawa",
    "wkwkwk": "tertawa",
    "zonk": "kecewa",
}

# Build regex pattern from slang keys (longest first to avoid partial matches)
def _build_pattern(slang_map: Dict[str, str]) -> re.Pattern:
    sorted_keys = sorted(slang_map.keys(), key=len, reverse=True)
    pattern = r'\b(' + '|'.join(re.escape(k) for k in sorted_keys) + r')\b'
    return re.compile(pattern, re.IGNORECASE)

_SLANG_PATTERN = _build_pattern(SLANG_MAP)


def normalize_slang(text: str, custom_map: Optional[Dict[str, str]] = None) -> str:
    """
    Normalize Indonesian slang to formal Indonesian.

    Args:
        text: Input text (should be lowercased before calling)
        custom_map: Optional additional slang mappings

    Returns:
        Text with slang normalized
    """
    combined_map = {**SLANG_MAP}
    if custom_map:
        combined_map.update(custom_map)

    pattern = _build_pattern(combined_map)

    def _replace(match: re.Match) -> str:
        word = match.group(1).lower()
        replacement = combined_map.get(word, word)
        return replacement

    return pattern.sub(_replace, text)


if __name__ == "__main__":
    test = "yg bgt krn jgn udh klo sm dr tp gk ga gak tdk"
    print(f"Raw: {test}")
    print(f"Normalized: {normalize_slang(test)}")

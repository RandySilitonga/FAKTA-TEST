
"""
FAKTA - Text Cleaning Module
Cleans and normalizes Indonesian text before processing.
"""

import re
from typing import Optional


def case_folding(text: str) -> str:
    """Convert to lowercase."""
    return text.lower()


def remove_urls(text: str) -> str:
    """Remove URLs from text."""
    url_pattern = r'https?://\S+|www\.\S+'
    return re.sub(url_pattern, '', text)


def remove_mentions(text: str) -> str:
    """Remove @mentions from text."""
    return re.sub(r'@\w+', '', text)


def remove_hashtags(text: str) -> str:
    """Remove #hashtags from text."""
    return re.sub(r'#\w+', '', text)


def remove_emojis(text: str) -> str:
    """Remove emojis from text."""
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map
        "\U0001F1E0-\U0001F1FF"  # flags
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "\U0001f926-\U0001f937"
        "\U00010000-\U0010ffff"
        "♀-♂"
        "☀-⭕"
        "‍"
        "⏏"
        "⏩"
        "⏰"
        "⏳"
        "▀-◿"
        "️"
        "❤"
        "❤️"
        "]+",
        flags=re.UNICODE,
    )
    return emoji_pattern.sub('', text)


def normalize_whitespace(text: str) -> str:
    """Normalize multiple spaces to single space."""
    return re.sub(r'\s+', ' ', text).strip()


def remove_special_chars(text: str, keep_punctuation: bool = True) -> str:
    """Remove special characters, optionally keeping basic punctuation."""
    if keep_punctuation:
        return re.sub(r'[^a-zA-Z0-9\s.,!?;:\'\"()-]', ' ', text)
    return re.sub(r'[^a-zA-Z0-9\s]', ' ', text)


def clean_text(text: str, remove_emoji: bool = True) -> str:
    """
    Full cleaning pipeline.

    Steps:
    1. Case folding
    2. Remove URLs, mentions, hashtags
    3. Remove emojis (optional)
    4. Remove excessive special chars
    5. Normalize whitespace

    Args:
        text: Raw input text
        remove_emoji: Whether to remove emojis

    Returns:
        Cleaned text
    """
    text = case_folding(text)
    text = remove_urls(text)
    text = remove_mentions(text)
    text = remove_hashtags(text)

    if remove_emoji:
        text = remove_emojis(text)

    text = remove_special_chars(text, keep_punctuation=True)
    text = normalize_whitespace(text)

    return text


if __name__ == "__main__":
    # Quick test
    sample = "VIRAL!!! 😱 Matcha menyebabkan gagal ginjal!! Cek di https://example.com @teman #hoaks sebarkan!"
    print(f"Raw: {sample}")
    print(f"Cleaned: {clean_text(sample)}")

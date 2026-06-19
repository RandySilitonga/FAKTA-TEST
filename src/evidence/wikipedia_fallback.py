"""
FAKTA - Wikipedia API Fallback
Used as Tier 4 source for general knowledge verification.
"""

from typing import List, Dict, Optional


class WikipediaFallback:
    """
    Wikipedia API fallback for general knowledge.
    NOT a primary verifier — only background information.
    """

    def __init__(self, language: str = "id"):
        self.language = language
        self._wiki = None

    def _get_wiki(self):
        """Lazy initialization."""
        if self._wiki is None:
            try:
                import wikipediaapi
                self._wiki = wikipediaapi.Wikipedia(
                    language=self.language,
                    extract_format=wikipediaapi.ExtractFormat.WIKITEXT,
                    user_agent="FAKTA fact-checking system (academic)",
                )
            except ImportError:
                print("[Wikipedia] wikipedia-api not installed, skipping")
                self._wiki = None
        return self._wiki

    def search(self, claim_text: str, max_results: int = 2) -> List[Dict]:
        """
        Search Wikipedia for background information related to the claim.

        Args:
            claim_text: Claim text
            max_results: Maximum results

        Returns:
            List of Wikipedia article snippets
        """
        wiki = self._get_wiki()
        if wiki is None:
            return []

        results = []

        # Try exact title match first
        title = claim_text[:100]
        page = wiki.page(title)

        if page.exists():
            results.append({
                "source": f"Wikipedia ({self.language})",
                "title": page.title,
                "text": page.summary[:500],
                "url": page.fullurl,
                "source_tier": 4,
                "provider": "wikipedia",
                "relevance_score": 0.5,
                "source_credibility": 0.4,
                "recency_score": 0.3,  # Wikipedia doesn't have precise dates
            })

        return results[:max_results]


if __name__ == "__main__":
    wiki = WikipediaFallback()
    results = wiki.search("Matcha")
    for r in results:
        print(f"[{r['source']}] {r['title']}: {r['text'][:100]}...")

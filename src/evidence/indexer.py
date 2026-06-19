"""
FAKTA - Evidence Database Indexer
Ingests scraped fact-check data into ChromaDB + BM25 index.
Run this periodically to update the evidence database.
"""

import os
import hashlib
import json
from pathlib import Path
from typing import List, Dict, Optional


class EvidenceIndexer:
    """
    Indexes fact-check articles into the local evidence database.
    Run periodically to keep evidence database fresh.
    """

    def __init__(self, chroma_path: str = "data/evidence/chroma_db"):
        from retriever import HybridRetriever
        self.retriever = HybridRetriever(chroma_path)

    def index_articles(self, articles: List[Dict]):
        """
        Index a list of fact-check articles.

        Each article dict should have:
        - title: Article title
        - text: Full article/debunk text
        - claim: The claim being debunked
        - source: Source name
        - source_tier: Credibility tier (1-4)
        - url: Article URL
        - date: Publication date (YYYY-MM-DD)
        - category: Category (kesehatan, bencana, etc.)
        """
        indexed = 0
        skipped = 0

        for article in articles:
            doc_id = hashlib.md5(article.get("url", article.get("text", "")).encode()).hexdigest()

            # Combine text for embedding
            text = f"{article.get('title', '')} {article.get('claim', '')} {article.get('text', '')}"

            metadata = {
                "id": doc_id,
                "source": article.get("source", "Unknown"),
                "source_tier": article.get("source_tier", 3),
                "url": article.get("url", ""),
                "title": article.get("title", ""),
                "date_published": article.get("date", ""),
                "category": article.get("category", "general"),
            }

            self.retriever.add_document(doc_id, text, metadata)
            indexed += 1

        print(f"Indexed {indexed} articles, skipped {skipped}")
        print(f"Database stats: {self.retriever.get_stats()}")

    def index_from_json(self, json_path: str):
        """Index articles from a JSON file."""
        with open(json_path) as f:
            articles = json.load(f)
        self.index_articles(articles)

    def index_from_csv(self, csv_path: str):
        """Index articles from a CSV file."""
        import pandas as pd
        df = pd.read_csv(csv_path)
        articles = df.to_dict("records")
        self.index_articles(articles)


if __name__ == "__main__":
    indexer = EvidenceIndexer()

    # Example: index from data file
    data_file = "data/processed/fact_checks.json"
    if os.path.exists(data_file):
        indexer.index_from_json(data_file)
    else:
        print(f"No data file found at {data_file}")
        print("Run data collection first, then re-run indexer.")

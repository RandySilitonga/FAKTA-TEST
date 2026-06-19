"""
FAKTA - Data Collection Pipeline
Scrapes and normalizes Indonesian hoax/non-hoax datasets for LSTM training.

Sources:
- TurnBackHoax (MAFINDO)
- CekFakta (Tempo)
- ISHOX (Kaggle)
- Kominfo Hoax Bulletins
"""

import os
import re
import time
import json
import hashlib
import requests
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

import pandas as pd
from bs4 import BeautifulSoup


# ============================================================
# TurnBackHoax Scraper
# ============================================================

class TurnBackHoaxScraper:
    """
    Scrapes TurnBackHoax.id for hoax fact-check articles.
    Respects rate limiting (1 req / 2 seconds).
    """

    BASE_URL = "https://turnbackhoax.id"
    RATE_LIMIT = 2.0  # seconds between requests

    def __init__(self, output_dir: str = "data/raw/turnbackhoax"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._last_request = 0

    def _wait(self):
        """Enforce rate limiting."""
        elapsed = time.time() - self._last_request
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request = time.time()

    def scrape_page(self, page: int = 1) -> List[Dict]:
        """Scrape a single page of articles."""
        self._wait()
        url = f"{self.BASE_URL}/page/{page}/"

        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "FAKTA Academic Research Bot (contact: research@fakta.id)"
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")
            articles = []

            # TurnBackHoax uses WordPress theme
            for article in soup.find_all("article"):
                title_el = article.find("h2", class_="entry-title")
                if not title_el:
                    continue

                title = title_el.get_text(strip=True)
                link_el = title_el.find("a")
                url = link_el["href"] if link_el else ""

                excerpt_el = article.find("div", class_="entry-excerpt")
                excerpt = excerpt_el.get_text(strip=True) if excerpt_el else ""

                date_el = article.find("time")
                date = date_el.get("datetime", "") if date_el else ""

                if title and url:
                    articles.append({
                        "title": title,
                        "url": url,
                        "excerpt": excerpt,
                        "date": date[:10] if date else "",
                        "source": "TurnBackHoax",
                        "source_tier": 3,
                    })

            return articles

        except Exception as e:
            print(f"[TurnBackHoax] Error scraping page {page}: {e}")
            return []

    def scrape_article_detail(self, url: str) -> Optional[Dict]:
        """Scrape full article content from URL."""
        self._wait()

        try:
            response = requests.get(url, timeout=15, headers={
                "User-Agent": "FAKTA Academic Research Bot"
            })
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Get content
            content_el = soup.find("div", class_="entry-content")
            content = content_el.get_text("\n", strip=True) if content_el else ""

            # Get category
            categories = []
            for cat in soup.find_all("a", rel="category"):
                categories.append(cat.get_text(strip=True))

            return {
                "content": content,
                "categories": categories,
                "full_text": content[:2000],  # Limit for training
            }

        except Exception as e:
            print(f"[TurnBackHoax] Error fetching {url}: {e}")
            return None

    def scrape(self, max_pages: int = 50, include_details: bool = False) -> List[Dict]:
        """
        Scrape multiple pages.

        Args:
            max_pages: Maximum number of pages to scrape
            include_details: Whether to fetch full article content

        Returns:
            List of article dicts
        """
        all_articles = []

        for page in range(1, max_pages + 1):
            print(f"Scraping page {page}/{max_pages}...")
            articles = self.scrape_page(page)

            if not articles:
                print(f"No more articles found at page {page}")
                break

            if include_details:
                for i, article in enumerate(articles):
                    print(f"  Fetching detail {i+1}/{len(articles)}: {article['title'][:50]}...")
                    detail = self.scrape_article_detail(article["url"])
                    if detail:
                        article.update(detail)

            all_articles.extend(articles)
            print(f"  Collected {len(articles)} articles from page {page}")

        # Save raw
        output_path = self.output_dir / "raw_articles.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(all_articles, f, ensure_ascii=False, indent=2)

        print(f"\nTotal articles collected: {len(all_articles)}")
        print(f"Saved to {output_path}")

        return all_articles


# ============================================================
# CekFakta Scraper
# ============================================================

class CekFaktaScraper:
    """
    Scrapes cekfakta.com (Tempo) for fact-check articles.
    """

    BASE_URL = "https://cekfakta.com"
    RATE_LIMIT = 2.0

    def __init__(self, output_dir: str = "data/raw/cekfakta"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._last_request = 0

    def _wait(self):
        elapsed = time.time() - self._last_request
        if elapsed < self.RATE_LIMIT:
            time.sleep(self.RATE_LIMIT - elapsed)
        self._last_request = time.time()

    def scrape(self, max_pages: int = 30) -> List[Dict]:
        """Scrape cekfakta articles."""
        # Placeholder implementation
        # cekfakta.com structure may vary
        print("[CekFakta] Scraper ready. Implement based on current site structure.")
        return []


# ============================================================
# Dataset Normalization
# ============================================================

def normalize_turnbackhoax(raw_articles: List[Dict]) -> pd.DataFrame:
    """
    Normalize TurnBackHoax raw data to training format.

    Output columns: text, claim, label, source, date, url
    """
    records = []

    for article in raw_articles:
        text = article.get("full_text") or article.get("content") or article.get("excerpt", "")
        claim = article.get("title", "")

        # All TurnBackHoax articles are debunked hoaks
        label = "hoax"

        records.append({
            "text": text,
            "claim": claim,
            "label": label,
            "source": "TurnBackHoax",
            "date": article.get("date", ""),
            "url": article.get("url", ""),
            "category": ", ".join(article.get("categories", [])),
        })

    df = pd.DataFrame(records)
    df = df.drop_duplicates(subset=["claim"])
    df = df.dropna(subset=["text"])
    df = df[df["text"].str.len() > 20]

    return df


def normalize_ishox(csv_path: str) -> pd.DataFrame:
    """
    Normalize ISHOX dataset from Kaggle.
    Expected format varies by version.
    """
    df = pd.read_csv(csv_path)

    # Map common column names
    if "text" not in df.columns:
        for col in ["tweet", "content", "article"]:
            if col in df.columns:
                df = df.rename(columns={col: "text"})
                break

    if "label" not in df.columns:
        for col in ["hoax", "class", "is_hoax"]:
            if col in df.columns:
                df = df.rename(columns={col: "label"})
                break

    if "text" in df.columns and "label" in df.columns:
        df["label"] = df["label"].astype(str).str.lower()
        df["label"] = df["label"].map({
            "hoax": "hoax", "true": "valid", "false": "hoax",
            "1": "hoax", "0": "valid", "hoaks": "hoax",
            "valid": "valid", "tidak hoax": "valid",
        }).fillna(df["label"])

        df["source"] = "ISHOX"
        return df[["text", "label", "source"]]

    return pd.DataFrame()


def combine_datasets(datasets: List[pd.DataFrame], output_path: str = "data/training/combined.csv"):
    """
    Combine multiple datasets and split into train/val/test.

    Args:
        datasets: List of normalized DataFrames
        output_path: Output path for combined CSV
    """
    from sklearn.model_selection import train_test_split

    combined = pd.concat(datasets, ignore_index=True)

    # Deduplicate
    combined = combined.drop_duplicates(subset=["text"])

    # Remove rows with empty text or unknown labels
    combined = combined.dropna(subset=["text", "label"])
    combined = combined[combined["label"].isin(["hoax", "valid", "uncertain"])]

    print(f"Combined dataset: {len(combined)} samples")
    print(f"Label distribution:\n{combined['label'].value_counts()}")

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    combined.to_csv(output_path, index=False, encoding="utf-8")
    print(f"Saved to {output_path}")

    return combined


# ============================================================
# Main
# ============================================================

def main():
    """Run full data collection pipeline."""
    print("=" * 60)
    print("FAKTA Data Collection Pipeline")
    print("=" * 60)

    # Step 1: Scrape TurnBackHoax
    print("\n[1/3] Scraping TurnBackHoax...")
    tbh_scraper = TurnBackHoaxScraper()
    tbh_articles = tbh_scraper.scrape(max_pages=50, include_details=False)

    # Step 2: Normalize
    print("\n[2/3] Normalizing datasets...")
    tbh_df = normalize_turnbackhoax(tbh_articles)

    # Step 3: Combine
    print("\n[3/3] Combining datasets...")
    datasets = [tbh_df]
    combined = combine_datasets(datasets)

    print(f"\nDone! Total: {len(combined)} samples")


if __name__ == "__main__":
    main()

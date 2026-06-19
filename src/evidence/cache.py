"""
FAKTA - Evidence Cache and Rate Limiter
SQLite-based cache for evidence search results + rate limiting for API calls.
"""

import os
import json
import time
import sqlite3
from typing import List, Dict, Optional
from hashlib import sha256
from datetime import datetime, timedelta


class EvidenceCache:
    """
    SQLite-based cache for evidence search results.
    Cache key = hash of (source + claim_text).
    TTL configurable per source.
    """

    def __init__(self, db_path: str = "data/evidence/cache.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._init_table()

    def _init_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS evidence_cache (
                cache_key TEXT PRIMARY KEY,
                claim_text TEXT,
                results_json TEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ttl_hours INTEGER DEFAULT 168
            )
        """)
        self.conn.commit()

    def get(self, claim_text: str, source: str) -> Optional[List[Dict]]:
        """Get cached results if not expired."""
        key = sha256(f"{source}:{claim_text}".encode()).hexdigest()

        row = self.conn.execute(
            "SELECT results_json, created_at, ttl_hours FROM evidence_cache WHERE cache_key = ?",
            (key,),
        ).fetchone()

        if row:
            results_json, created_at, ttl_hours = row
            created = datetime.fromisoformat(created_at)
            if datetime.now() - created < timedelta(hours=ttl_hours):
                return json.loads(results_json)
            else:
                self.conn.execute("DELETE FROM evidence_cache WHERE cache_key = ?", (key,))
                self.conn.commit()

        return None

    def set(self, claim_text: str, source: str, results: List[Dict], ttl_hours: int = 168):
        """Cache evidence results."""
        key = sha256(f"{source}:{claim_text}".encode()).hexdigest()
        self.conn.execute(
            """INSERT OR REPLACE INTO evidence_cache
               (cache_key, claim_text, results_json, source, ttl_hours)
               VALUES (?, ?, ?, ?, ?)""",
            (key, claim_text, json.dumps(results), source, ttl_hours),
        )
        self.conn.commit()

    def clear_expired(self):
        """Remove expired entries."""
        self.conn.execute("""
            DELETE FROM evidence_cache
            WHERE datetime(created_at, '+' || ttl_hours || ' hours') < datetime('now')
        """)
        self.conn.commit()

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        total = self.conn.execute("SELECT COUNT(*) FROM evidence_cache").fetchone()[0]
        return {"total_entries": total}

    def close(self):
        self.conn.close()


class RateLimiter:
    """
    Simple sliding window rate limiter.
    """

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window = window_seconds
        self.requests: List[float] = []

    def wait_if_needed(self):
        """Block until a request slot is available."""
        now = time.time()
        self.requests = [t for t in self.requests if now - t < self.window]

        if len(self.requests) >= self.max_requests:
            wait_time = self.window - (now - self.requests[0])
            if wait_time > 0:
                time.sleep(wait_time)

        self.requests.append(time.time())


# Pre-configured limiters
google_factcheck_limiter = RateLimiter(max_requests=90, window_seconds=60)
gemini_limiter = RateLimiter(max_requests=14, window_seconds=60)


if __name__ == "__main__":
    cache = EvidenceCache()

    # Test cache
    cache.set("test claim", "google_factcheck", [{"source": "Test", "text": "Result"}])
    result = cache.get("test claim", "google_factcheck")
    print(f"Cached: {result}")

    print(f"Stats: {cache.get_stats()}")
    cache.close()

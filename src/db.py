"""
OpenDealCheck — Listing Database
SQLite-backed dedup and tracking for seen listings.
"""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

from src.config import DB_PATH


def _ensure_db():
    """Create tables if they don't exist."""
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS listings (
                listing_id TEXT PRIMARY KEY,
                property_url TEXT,
                formatted_address TEXT,
                city TEXT,
                state TEXT,
                zip_code TEXT,
                beds INTEGER,
                full_baths INTEGER,
                half_baths INTEGER,
                sqft REAL,
                lot_sqft REAL,
                list_price REAL,
                year_built INTEGER,
                days_on_mls INTEGER,
                estimated_value REAL,
                assessed_value REAL,
                tax REAL,
                latitude REAL,
                longitude REAL,
                first_seen TEXT DEFAULT (datetime('now')),
                analyzed INTEGER DEFAULT 0,
                report_path TEXT
            )
        """)


@contextmanager
def _connect():
    """Context manager for SQLite connections."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialize the database (idempotent)."""
    _ensure_db()


def is_new_listing(listing_id: str) -> bool:
    """Check if we've seen this listing before."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM listings WHERE listing_id = ?", (listing_id,)
        ).fetchone()
        return row is None


def save_listing(row: dict):
    """Insert a new listing record."""
    with _connect() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO listings
            (listing_id, property_url, formatted_address, city, state, zip_code,
             beds, full_baths, half_baths, sqft, lot_sqft, list_price,
             year_built, days_on_mls, estimated_value, assessed_value, tax,
             latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row.get("listing_id", row.get("id", "")),
            row.get("property_url", row.get("url", "")),
            row.get("formatted_address", row.get("address", "")),
            row.get("city", ""),
            row.get("state", ""),
            row.get("zip_code", row.get("zip", "")),
            row.get("beds", 0),
            row.get("full_baths", row.get("baths", 0)),
            row.get("half_baths", 0),
            row.get("sqft", 0),
            row.get("lot_sqft", 0),
            row.get("list_price", row.get("price", 0)),
            row.get("year_built", 0),
            row.get("days_on_mls", 0),
            row.get("estimated_value", 0),
            row.get("assessed_value", 0),
            row.get("tax", 0),
            row.get("latitude", 0),
            row.get("longitude", 0),
        ))


def mark_analyzed(listing_id: str, report_path: str):
    """Mark a listing as analyzed and store report path."""
    with _connect() as conn:
        conn.execute(
            "UPDATE listings SET analyzed = 1, report_path = ? WHERE listing_id = ?",
            (report_path, listing_id),
        )


def get_recent_listings(zip_code: str = None, days: int = 30) -> list[dict]:
    """Get recent listings, optionally filtered by zip code."""
    with _connect() as conn:
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        if zip_code:
            rows = conn.execute(
                "SELECT * FROM listings WHERE zip_code = ? AND first_seen >= ? ORDER BY first_seen DESC",
                (zip_code, cutoff),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM listings WHERE first_seen >= ? ORDER BY first_seen DESC",
                (cutoff,),
            ).fetchall()
        return [dict(r) for r in rows]


def get_stats() -> dict:
    """Quick stats for logging."""
    with _connect() as conn:
        total = conn.execute("SELECT COUNT(*) FROM listings").fetchone()[0]
        analyzed = conn.execute("SELECT COUNT(*) FROM listings WHERE analyzed = 1").fetchone()[0]
        return {"total": total, "analyzed": analyzed, "pending": total - analyzed}

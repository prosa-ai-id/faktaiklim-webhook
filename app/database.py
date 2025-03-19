import datetime
import json
import sqlite3
from typing import Any, Dict, List, Optional

from app.config import settings


def get_db_connection():
    """Create a connection to the SQLite database"""
    conn = sqlite3.connect(settings.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    # Return dictionary-like rows
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database tables if they don't exist"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Create the articles table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS article_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            search_date TIMESTAMP NOT NULL,
            search_query TEXT NOT NULL,
            status TEXT NOT NULL,
            hoax_probability REAL,
            topic TEXT,
            response_json TEXT
        )
        """)

        conn.commit()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Error initializing database: {e}")
        # Fail immediately if DB init fails
        raise
    finally:
        conn.close()


def log_article_search(
    user_id: str,
    search_query: str,
    status: str,
    hoax_probability: Optional[float] = None,
    topic: Optional[str] = None,
    response_json: Optional[Dict] = None,
):
    """Log an article search to the database"""
    conn = get_db_connection()
    try:
        # Get current time in WIB (GMT+7)
        wib_tz = datetime.timezone(datetime.timedelta(hours=7))
        current_time = datetime.datetime.now(wib_tz)

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO article_searches 
            (user_id, search_date, search_query, status, hoax_probability, topic, response_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                current_time.strftime("%Y-%m-%d %H:%M:%S"),
                search_query,
                status,
                hoax_probability,
                topic,
                json.dumps(response_json) if response_json else None,
            ),
        )
        conn.commit()
    except Exception as e:
        print(f"Error logging article search: {e}")
    finally:
        conn.close()


def get_article_search_history(start_date: str, end_date: str) -> List[Dict]:
    """
    Get article search history within a date range

    Args:
        start_date: Start date in format YYYY-MM-DD
        end_date: End date in format YYYY-MM-DD

    Returns:
        List of search history records
    """
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Add time to make the end_date inclusive
        end_date_with_time = f"{end_date} 23:59:59"

        cursor.execute(
            """
            SELECT * FROM article_searches
            WHERE search_date BETWEEN ? AND ?
            ORDER BY search_date DESC
            """,
            (start_date, end_date_with_time),
        )

        # Convert rows to dictionaries
        results = []
        for row in cursor.fetchall():
            result = dict(row)
            # Parse JSON string back to dict if not None
            if result["response_json"]:
                result["response_json"] = json.loads(result["response_json"])
            results.append(result)

        return results
    except Exception as e:
        print(f"Error getting article search history: {e}")
        return []
    finally:
        conn.close()

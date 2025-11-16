#!/usr/bin/env python3
"""
Script to inject test RSS feeds directly into the database.
This script connects to PostgreSQL and adds sample feeds for testing.

Usage: python3 inject_sample_data.py
"""

import os
import sys
from datetime import datetime, timezone

# Database connection
try:
    import psycopg2
    from psycopg2 import sql
except ImportError:
    print("❌ Error: psycopg2 not installed")
    print("   Install with: pip3 install psycopg2-binary")
    sys.exit(1)


# Test RSS feeds
TEST_FEEDS = [
    {
        "url": "https://feeds.arstechnica.com/arstechnica/index",
        "title": "Ars Technica",
        "description": "Technology news and analysis",
    },
    {
        "url": "https://www.theverge.com/rss/index.xml",
        "title": "The Verge",
        "description": "Technology, science, art, and culture",
    },
]


def get_db_connection():
    """Get PostgreSQL database connection from environment."""
    db_url = os.getenv("DATABASE_URL", "postgresql://curio:curio@localhost:5432/curio")

    # Parse the DATABASE_URL
    # Format: postgresql://user:password@host:port/database
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "")

        if "@" in db_url:
            user_pass, host_db = db_url.split("@")
            user, password = user_pass.split(":")
            host_port, database = host_db.split("/")

            if ":" in host_port:
                host, port = host_port.split(":")
            else:
                host = host_port
                port = "5432"
        else:
            print("❌ Invalid DATABASE_URL format")
            sys.exit(1)
    else:
        print("❌ DATABASE_URL must start with postgresql://")
        sys.exit(1)

    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        return conn
    except psycopg2.OperationalError as e:
        print(f"❌ Cannot connect to database: {e}")
        print(f"   Connection string: postgresql://{user}:***@{host}:{port}/{database}")
        sys.exit(1)


def inject_test_feeds():
    """Inject test RSS feeds into the database."""
    print("🔌 Connecting to database...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Get the first user (or any user)
        cursor.execute("SELECT id, email FROM users LIMIT 1")
        user = cursor.fetchone()

        if not user:
            print("❌ No users found in database.")
            print("   Please login to the application first to create a user.")
            return

        user_id, user_email = user
        print(f"✓ Found user: {user_email} (ID: {user_id})")
        print()

        added_count = 0

        for feed_data in TEST_FEEDS:
            # Check if feed already exists
            cursor.execute(
                "SELECT id FROM feeds WHERE url = %s AND user_id = %s",
                (feed_data["url"], user_id)
            )
            existing = cursor.fetchone()

            if existing:
                print(f"⊘ Feed already exists: {feed_data['title']}")
                continue

            # Insert new feed
            now = datetime.now(timezone.utc)
            cursor.execute(
                """
                INSERT INTO feeds (user_id, url, title, description, is_active, created_at, updated_at, fetch_interval)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    user_id,
                    feed_data["url"],
                    feed_data["title"],
                    feed_data["description"],
                    True,  # is_active
                    now,
                    now,
                    60  # fetch_interval in minutes
                )
            )

            feed_id = cursor.fetchone()[0]
            conn.commit()

            print(f"✓ Added feed: {feed_data['title']} (ID: {feed_id})")
            print(f"  URL: {feed_data['url']}")
            added_count += 1

        print()
        print(f"✓ Successfully added {added_count} test feed(s)")

        if added_count > 0:
            print()
            print("Next steps:")
            print("1. Open the application: http://localhost:3000")
            print("2. Go to Settings page")
            print("3. Click 'Fetch Feeds' to download articles")
            print("4. Click 'Process Articles' to analyze with AI")
            print("5. View articles on the home page")

    except Exception as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        raise

    finally:
        cursor.close()
        conn.close()
        print()
        print("✓ Database connection closed")


if __name__ == "__main__":
    print("=" * 60)
    print("  RSS Feed Data Injection Script")
    print("=" * 60)
    print()

    inject_test_feeds()

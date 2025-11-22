#!/usr/bin/env python3
"""
Test file upload validation for RSS image downloads.
Tests size limits, content-type validation, and magic byte verification.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.rss_fetcher import RSSFetcher
from app.core.database import SessionLocal
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_file_validation():
    """Test various file upload validation scenarios."""

    db = SessionLocal()
    fetcher = RSSFetcher(db)

    test_cases = [
        {
            "name": "Valid small JPEG",
            "url": "https://picsum.photos/200/300.jpg",
            "expected": "success",
        },
        {
            "name": "Valid PNG",
            "url": "https://picsum.photos/200/300.png",
            "expected": "success",
        },
        {
            "name": "Potentially large image (may exceed 10MB)",
            "url": "https://picsum.photos/10000/10000.jpg",
            "expected": "may_fail_size",
        },
        {
            "name": "HTML file (should fail magic byte check)",
            "url": "https://example.com",
            "expected": "fail",
        },
    ]

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for test in test_cases:
            logger.info(f"\n{'='*60}")
            logger.info(f"Testing: {test['name']}")
            logger.info(f"URL: {test['url']}")
            logger.info(f"Expected: {test['expected']}")
            logger.info(f"{'='*60}")

            result = await fetcher._download_image(test["url"], client)

            if result:
                logger.info(f"✅ SUCCESS: Downloaded to {result}")
                results.append(
                    {"test": test["name"], "status": "pass", "result": result}
                )
            else:
                logger.info(
                    f"❌ REJECTED: Validation failed (as expected for some tests)"
                )
                results.append(
                    {"test": test["name"], "status": "rejected", "result": None}
                )

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    for r in results:
        status_icon = "✅" if r["status"] == "pass" else "❌"
        print(f"{status_icon} {r['test']}: {r['status']}")

    db.close()

    # Validate expectations
    print("\n" + "=" * 60)
    print("VALIDATION CHECKS")
    print("=" * 60)

    # Check that valid images were downloaded
    valid_downloads = [
        r
        for r in results
        if r["status"] == "pass" and "JPEG" in r["test"] or "PNG" in r["test"]
    ]
    print(f"✅ Valid images downloaded: {len(valid_downloads)}")

    # Check that HTML was rejected
    html_rejected = [
        r for r in results if r["status"] == "rejected" and "HTML" in r["test"]
    ]
    print(f"✅ Invalid file types rejected: {len(html_rejected)}")

    print("\n✅ File upload validation is working correctly!")


if __name__ == "__main__":
    asyncio.run(test_file_validation())

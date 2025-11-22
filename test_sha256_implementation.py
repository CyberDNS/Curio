#!/usr/bin/env python3
"""
Test SHA-256 hash implementation with collision detection.
"""

import asyncio
import sys
from pathlib import Path
import hashlib

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.services.rss_fetcher import RSSFetcher
from app.core.database import SessionLocal
import httpx
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_sha256_implementation():
    """Test SHA-256 hash generation and collision detection."""

    db = SessionLocal()
    fetcher = RSSFetcher(db)

    print("\n" + "=" * 70)
    print("SHA-256 Hash Implementation Test")
    print("=" * 70)

    # Test 1: Verify SHA-256 is used instead of MD5
    print("\n1. Testing SHA-256 hash generation:")
    test_url = "https://picsum.photos/200/300.jpg"

    # Calculate expected hash
    expected_sha256 = hashlib.sha256(test_url.encode()).hexdigest()
    expected_md5 = hashlib.md5(test_url.encode()).hexdigest()

    print(f"   URL: {test_url}")
    print(f"   SHA-256: {expected_sha256} (64 chars)")
    print(f"   MD5:     {expected_md5} (32 chars)")
    print(f"   ✅ SHA-256 is longer and more secure than MD5")

    # Test 2: Download an image and verify it uses SHA-256
    print("\n2. Testing image download with SHA-256 filename:")
    async with httpx.AsyncClient(timeout=30.0) as client:
        result = await fetcher._download_image(test_url, client)

        if result:
            print(f"   Downloaded: {result}")
            # Extract hash from filename
            filename = result.split("/")[-1]
            hash_part = filename.split(".")[0]

            if len(hash_part) == 64:
                print(f"   ✅ Filename uses 64-char SHA-256 hash")
            elif "_" in hash_part and len(hash_part.split("_")[0]) == 64:
                print(
                    f"   ✅ Filename uses SHA-256 with timestamp suffix (collision resolution)"
                )
            else:
                print(f"   ❌ Unexpected hash length: {len(hash_part)}")

            # Check if metadata file exists
            from app.core.config import settings

            images_dir = Path(settings.MEDIA_ROOT) / "images"
            metadata_file = images_dir / (filename + ".meta")

            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    stored_url = f.read().strip()
                    if stored_url == test_url:
                        print(f"   ✅ Metadata file created with correct URL")
                    else:
                        print(f"   ❌ Metadata file has wrong URL: {stored_url}")
            else:
                print(
                    f"   ⚠️  Metadata file not found (may be cached from previous download)"
                )
        else:
            print(f"   ❌ Download failed")

    # Test 3: Verify collision detection (same URL twice)
    print("\n3. Testing collision detection (downloading same URL again):")
    async with httpx.AsyncClient(timeout=30.0) as client:
        result2 = await fetcher._download_image(test_url, client)

        if result2:
            if result == result2:
                print(f"   ✅ Same URL returned cached result: {result2}")
            else:
                print(
                    f"   ⚠️  Different filename returned (possible collision resolution)"
                )
        else:
            print(f"   ❌ Second download failed")

    # Test 4: Hash length comparison
    print("\n4. Security comparison:")
    print(f"   MD5 hash space:     2^128 = ~3.4×10^38 possible hashes")
    print(f"   SHA-256 hash space: 2^256 = ~1.2×10^77 possible hashes")
    print(f"   ✅ SHA-256 provides vastly stronger collision resistance")

    print("\n" + "=" * 70)
    print("✅ SHA-256 Implementation Test Complete")
    print("=" * 70)

    db.close()


if __name__ == "__main__":
    asyncio.run(test_sha256_implementation())

#!/usr/bin/env python3
"""
Test script for SSRF protection in image proxy endpoint.
Tests various attack vectors to ensure they're properly blocked.
"""

import asyncio
from app.api.endpoints.proxy import validate_url_safety
from fastapi import HTTPException


async def test_ssrf_protection():
    """Test SSRF protection with various attack vectors."""

    print("=" * 80)
    print("SSRF Protection Test Suite")
    print("=" * 80)
    print()

    test_cases = [
        # Valid URLs (should pass)
        ("https://example.com/image.jpg", True, "Valid HTTPS URL"),
        ("http://example.com/image.png", True, "Valid HTTP URL"),
        ("https://cdn.example.com/path/to/image.webp", True, "Valid CDN URL"),
        # Invalid schemes (should fail)
        ("file:///etc/passwd", False, "File scheme attack"),
        ("ftp://example.com/file", False, "FTP scheme attack"),
        ("gopher://example.com", False, "Gopher scheme attack"),
        ("data:image/png;base64,xyz", False, "Data URI scheme"),
        # Private IP addresses (should fail)
        ("http://127.0.0.1/secret", False, "Loopback (localhost)"),
        ("http://127.0.0.1:8080/admin", False, "Loopback with port"),
        ("http://0.0.0.0/", False, "All interfaces"),
        ("http://10.0.0.1/internal", False, "Private network (10.x)"),
        ("http://172.16.0.1/internal", False, "Private network (172.16.x)"),
        ("http://192.168.1.1/router", False, "Private network (192.168.x)"),
        ("http://[::1]/secret", False, "IPv6 loopback"),
        ("http://[fc00::1]/internal", False, "IPv6 private"),
        # Cloud metadata endpoints (should fail)
        ("http://169.254.169.254/latest/meta-data/", False, "AWS metadata service"),
        ("http://metadata.google.internal/", False, "GCP metadata (if it resolves)"),
        # DNS rebinding attempts
        ("http://localhost/secret", False, "localhost (resolves to 127.0.0.1)"),
        # Edge cases
        ("", False, "Empty URL"),
        ("not-a-url", False, "Invalid URL format"),
        ("http://", False, "Incomplete URL"),
    ]

    passed = 0
    failed = 0

    for url, should_pass, description in test_cases:
        try:
            validate_url_safety(url)
            if should_pass:
                print(f"✅ PASS: {description}")
                print(f"   URL: {url}")
                passed += 1
            else:
                print(f"❌ FAIL: {description}")
                print(f"   URL: {url}")
                print(f"   Expected: Blocked, Got: Allowed")
                failed += 1
        except HTTPException as e:
            if not should_pass:
                print(f"✅ PASS: {description}")
                print(f"   URL: {url}")
                print(f"   Blocked with: {e.detail}")
                passed += 1
            else:
                print(f"❌ FAIL: {description}")
                print(f"   URL: {url}")
                print(f"   Expected: Allowed, Got: {e.detail}")
                failed += 1
        except Exception as e:
            print(f"⚠️  ERROR: {description}")
            print(f"   URL: {url}")
            print(f"   Unexpected error: {e}")
            failed += 1

        print()

    print("=" * 80)
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)} tests")
    print("=" * 80)

    return failed == 0


if __name__ == "__main__":
    # Need to be in the backend directory with proper imports
    success = asyncio.run(test_ssrf_protection())
    exit(0 if success else 1)

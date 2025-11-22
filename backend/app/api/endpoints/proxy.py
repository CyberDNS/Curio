from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
import httpx
import logging
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter()
logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)

# Maximum image size (5MB)
MAX_IMAGE_SIZE = 5 * 1024 * 1024

# Blocked IP ranges (RFC 1918 private networks, loopback, link-local, cloud metadata)
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),  # Current network (only valid as source)
    ipaddress.ip_network("10.0.0.0/8"),  # Private network (RFC 1918)
    ipaddress.ip_network("127.0.0.0/8"),  # Loopback
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local / AWS metadata
    ipaddress.ip_network("172.16.0.0/12"),  # Private network (RFC 1918)
    ipaddress.ip_network("192.168.0.0/16"),  # Private network (RFC 1918)
    ipaddress.ip_network("224.0.0.0/4"),  # Multicast
    ipaddress.ip_network("240.0.0.0/4"),  # Reserved
    ipaddress.ip_network("::1/128"),  # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),  # IPv6 private
    ipaddress.ip_network("fe80::/10"),  # IPv6 link-local
    ipaddress.ip_network("ff00::/8"),  # IPv6 multicast
]

# Allowed image content types
ALLOWED_IMAGE_TYPES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/svg+xml",
    "image/avif",
]


def validate_url_safety(url: str) -> None:
    """
    Validate URL to prevent SSRF attacks.

    Raises HTTPException if URL is not safe.
    """
    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        logger.warning(f"Invalid URL format: {url}")
        raise HTTPException(status_code=400, detail="Invalid URL format")

    # Check scheme (only http/https allowed)
    if parsed.scheme not in ["http", "https"]:
        logger.warning(f"Blocked non-http(s) scheme: {parsed.scheme}")
        raise HTTPException(
            status_code=400, detail="Only HTTP and HTTPS URLs are allowed"
        )

    # Check for hostname
    if not parsed.hostname:
        logger.warning(f"URL missing hostname: {url}")
        raise HTTPException(status_code=400, detail="URL must have a valid hostname")

    # Resolve hostname to IP address
    try:
        ip_addresses = socket.getaddrinfo(parsed.hostname, None)
    except socket.gaierror as e:
        logger.warning(f"Failed to resolve hostname {parsed.hostname}: {e}")
        raise HTTPException(status_code=400, detail="Could not resolve hostname")

    # Check all resolved IPs against blocked networks
    for ip_info in ip_addresses:
        ip_str = ip_info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)

            # Check against blocked networks
            for network in BLOCKED_IP_NETWORKS:
                if ip_obj in network:
                    logger.warning(
                        f"Blocked SSRF attempt: {url} resolves to {ip_str} "
                        f"which is in blocked network {network}"
                    )
                    raise HTTPException(
                        status_code=403,
                        detail="Access to private/internal networks is not allowed",
                    )
        except ValueError:
            logger.warning(f"Invalid IP address from DNS resolution: {ip_str}")
            raise HTTPException(status_code=400, detail="Invalid IP address resolved")


@router.get("/image")
@limiter.limit("60/minute")
async def proxy_image(request: Request, url: str):
    """
    Proxy an image URL to bypass CORS and referrer restrictions.

    Security features:
    - URL validation (only http/https)
    - DNS resolution validation
    - Private IP/internal network blocking (prevents SSRF)
    - Cloud metadata endpoint blocking
    - Content-Type validation
    - File size limits (5MB max)
    - Streaming with size checks

    This endpoint fetches the image server-side and streams it to the client.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    # Validate URL for SSRF protection
    validate_url_safety(url)

    try:
        # Configure client with strict limits
        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
            max_redirects=5,  # Limit redirects
        ) as client:
            # Fetch the image with headers that mimic a browser request
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }

            # Stream the response to check size
            async with client.stream("GET", url, headers=headers) as response:
                response.raise_for_status()

                # Validate content type
                content_type = response.headers.get("content-type", "").lower()
                if not any(
                    allowed_type in content_type for allowed_type in ALLOWED_IMAGE_TYPES
                ):
                    logger.warning(
                        f"Blocked non-image content type: {content_type} for URL: {url}"
                    )
                    raise HTTPException(
                        status_code=400, detail="URL does not point to a valid image"
                    )

                # Check content length if available
                content_length = response.headers.get("content-length")
                if content_length and int(content_length) > MAX_IMAGE_SIZE:
                    logger.warning(
                        f"Image too large: {content_length} bytes for URL: {url}"
                    )
                    raise HTTPException(
                        status_code=413,
                        detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE // (1024*1024)}MB",
                    )

                # Read and validate size during streaming
                content = b""
                async for chunk in response.aiter_bytes():
                    content += chunk
                    if len(content) > MAX_IMAGE_SIZE:
                        logger.warning(
                            f"Image exceeded size limit during download: {url}"
                        )
                        raise HTTPException(
                            status_code=413,
                            detail=f"Image exceeds maximum size of {MAX_IMAGE_SIZE // (1024*1024)}MB",
                        )

                # Return the image
                return StreamingResponse(
                    iter([content]),
                    media_type=content_type,
                    headers={
                        "Cache-Control": "public, max-age=86400",  # Cache for 24 hours
                        "Content-Length": str(len(content)),
                    },
                )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching image: {e.response.status_code}")
        raise HTTPException(
            status_code=e.response.status_code, detail="Failed to fetch image"
        )
    except httpx.TimeoutException:
        logger.error(f"Timeout fetching image: {url}")
        raise HTTPException(status_code=504, detail="Image request timed out")
    except httpx.TooManyRedirects:
        logger.error(f"Too many redirects for image: {url}")
        raise HTTPException(status_code=400, detail="Too many redirects")
    except HTTPException:
        # Re-raise our own exceptions
        raise
    except Exception as e:
        logger.error(f"Error proxying image: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to process image")

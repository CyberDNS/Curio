from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/image")
async def proxy_image(url: str):
    """
    Proxy an image URL to bypass CORS and referrer restrictions.
    This endpoint fetches the image server-side and streams it to the client.
    """
    if not url:
        raise HTTPException(status_code=400, detail="URL parameter is required")

    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            # Fetch the image with headers that mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.instagram.com/',
            }

            response = await client.get(url, headers=headers)
            response.raise_for_status()

            # Get content type from the response
            content_type = response.headers.get('content-type', 'image/jpeg')

            # Stream the image back to the client
            return StreamingResponse(
                iter([response.content]),
                media_type=content_type,
                headers={
                    'Cache-Control': 'public, max-age=86400',  # Cache for 24 hours
                }
            )

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching image {url}: {e.response.status_code}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Failed to fetch image: {str(e)}")
    except Exception as e:
        logger.error(f"Error proxying image {url}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to proxy image: {str(e)}")

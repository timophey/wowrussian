from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field
import re
import logging
from fastapi.responses import JSONResponse

from app.core.database import get_db
from app.services.fz168_client import FZ168Client
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/single", tags=["single"])


class SingleCheckRequest(BaseModel):
    """Request model for single URL analysis."""
    url: HttpUrl = Field(..., description="URL of the page to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com/article"
            }
        }


def is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
        r'localhost|'  # localhost
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


@router.post("/check")
async def check_single(
    request: Request,
    data: SingleCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Analyze a single URL via 168fz microservice.
    
    This endpoint bypasses the scheduler and directly proxies the request
    to the 168fz service for immediate analysis.
    
    Args:
        data: Request containing the URL to analyze
        
    Returns:
        Analysis results from 168fz service
        
    Raises:
        HTTPException: If URL is invalid or 168fz service is unavailable
    """
    url = str(data.url)
    
    # Additional validation
    if not is_valid_url(url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format. Please provide a valid URL starting with http:// or https://"
        )
    
    # Initialize 168fz client
    fz168_client = FZ168Client(
        base_url=settings.fz168_url,
        timeout=settings.fz168_timeout,
        retry_attempts=settings.fz168_retry_attempts
    )
    
    try:
        # Proxy the request to 168fz - it already returns {"success": true, "data": results}
        result = await fz168_client.check_url(url)
        response = JSONResponse(content=result)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"Error during single URL analysis: {e}")
        
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze URL via 168fz service: {str(e)}"
        )

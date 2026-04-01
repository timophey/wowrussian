from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field
import re
import logging
from fastapi.responses import JSONResponse, StreamingResponse
import io

from app.core.database import get_db
from app.services.fz168_client import FZ168Client
from app.services.excel_exporter import ExcelExporter
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


class ExportRequest(BaseModel):
    """Request model for XLSX export."""
    analysis_data: dict = Field(..., description="Analysis results data (same structure as fz168 response)")
    selected_statuses: Optional[List[str]] = Field(None, description="List of statuses to include. If empty, all statuses are included")
    page_url: Optional[str] = Field(None, description="URL of the analyzed page")
    language: Optional[str] = Field("ru", description="Language code for headers (ru or en)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "analysis_data": {"statistics": {}, "summary": {}, "all_words": []},
                "selected_statuses": ["prohibited", "foreign"],
                "page_url": "https://example.com/article",
                "language": "ru"
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


@router.post("/export-xlsx")
async def export_xlsx(
    request: Request,
    data: ExportRequest
):
    """
    Export analysis results to XLSX format.
    
    Creates an Excel file with:
    - Frozen header row: localized column names
    - Data rows filtered by selected statuses
    - Status cells styled with colors matching the UI
    - Auto-filter for easy filtering
    - Page URL in first column as hyperlink
    
    Args:
        data: ExportRequest containing analysis data and filters
        
    Returns:
        StreamingResponse with XLSX file
    """
    try:
        analysis_data = data.analysis_data
        page_url = data.page_url
        language = data.language or "ru"
        
        # Use the ExcelExporter service
        excel_bytes = ExcelExporter.export_analysis(
            analysis_data=analysis_data,
            selected_statuses=data.selected_statuses,
            page_url=page_url,
            language=language
        )
        
        # Create filename with timestamp
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"analysis_export_{timestamp}.xlsx"
        
        return StreamingResponse(
            io.BytesIO(excel_bytes),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.error(f"Error generating XLSX export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate XLSX export: {str(e)}"
        )


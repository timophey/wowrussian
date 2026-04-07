from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, HttpUrl, Field
import re
import logging
import tempfile
from pathlib import Path
from fastapi.responses import JSONResponse, Response

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


class TextCheckRequest(BaseModel):
    """Request model for text analysis."""
    text: str = Field(..., description="Text to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Sample text for analysis"
            }
        }


@router.post("/check-text")
async def check_text(
    request: Request,
    data: TextCheckRequest,
    db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Analyze text directly via 168fz microservice.
    
    Args:
        data: Request containing the text to analyze
        
    Returns:
        Analysis results from 168fz service
    """
    text = data.text.strip()
    
    if not text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Text cannot be empty"
        )
    
    # Initialize 168fz client
    fz168_client = FZ168Client(
        base_url=settings.fz168_url,
        timeout=settings.fz168_timeout,
        retry_attempts=settings.fz168_retry_attempts
    )
    
    try:
        # Proxy the request to 168fz
        result = await fz168_client.check_text(text)
        response = JSONResponse(content=result)
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        return response
    except Exception as e:
        logger.error(f"Error during text analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze text via 168fz service: {str(e)}"
        )


@router.post("/check-file")
async def check_file(
    file: UploadFile = File(...),
    db: Annotated[AsyncSession, Depends(get_db)] = None
):
    """
    Analyze file content via 168fz microservice.
    
    Supported formats: TXT, HTML, MD
    Max file size: 2MB
    
    Args:
        file: Uploaded file to analyze
        
    Returns:
        Analysis results from 168fz service
    """
    # Check file extension
    allowed_extensions = {'.txt', '.html', '.htm', '.md'}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ''
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format. Supported: {', '.join(allowed_extensions)}"
        )
    
    # Read file content
    content = await file.read()
    
    # Check file size (2MB limit)
    max_size = 2 * 1024 * 1024  # 2MB
    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File size exceeds 2MB limit"
        )
    
    # Initialize 168fz client
    fz168_client = FZ168Client(
        base_url=settings.fz168_url,
        timeout=settings.fz168_timeout,
        retry_attempts=settings.fz168_retry_attempts
    )
    
    try:
        # Save to temp file and send to 168fz
        with tempfile.NamedTemporaryFile(mode='wb', suffix=file_ext, delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        
        try:
            # Proxy the file to 168fz
            result = await fz168_client.check_file(tmp_path, file.filename)
            response = JSONResponse(content=result)
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            return response
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during file analysis: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze file via 168fz service: {str(e)}"
        )


@router.get("/config")
async def get_config():
    """
    Get frontend configuration including tab order.
    
    Returns:
        Configuration object with tab_order array
    """
    tab_order_str = settings.tab_order
    tab_order = [tab.strip() for tab in tab_order_str.split(',') if tab.strip()]
    
    # Validate tab order values
    valid_tabs = {'text', 'url', 'site', 'file'}
    validated_tabs = [tab for tab in tab_order if tab in valid_tabs]
    
    # Add any missing valid tabs with defaults
    for tab in valid_tabs:
        if tab not in validated_tabs:
            validated_tabs.append(tab)
    
    return JSONResponse(content={
        "tab_order": validated_tabs
    })


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
        
        return Response(
            content=excel_bytes,
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


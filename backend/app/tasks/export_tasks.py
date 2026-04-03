import asyncio
import io
import json
import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from celery import current_task

from app.tasks.celery_app import celery_app
from app.core.database import create_session_factory
from app.core.config import settings
from app.models.export_job import ExportJob, ExportJobStatus
from app.models.project import Project
from app.models.page import Page
from app.utils.db import safe_scalar


logger = logging.getLogger(__name__)


async def publish_export_update(job_id: int, event: str, data: dict, project_id: int = None):
    """Publish export job update to Redis channel(s)."""
    import redis.asyncio as redis
    async with redis.from_url(settings.redis_url) as redis_client:
        # Always publish to job-specific channel
        await redis_client.publish(
            f"export_job:{job_id}:updates",
            json.dumps({"event": event, "data": data, "job_id": job_id})
        )
        # Also publish to project channel if project_id is provided (for WebSocket integration)
        if project_id:
            await redis_client.publish(
                f"project:{project_id}:updates",
                json.dumps({"event": f"export_{event}", "data": data, "job_id": job_id})
            )


@celery_app.task(bind=True, name="export_project_xlsx")
def export_project_xlsx(self, job_id: int):
    """Generate XLSX export for a project asynchronously."""
    asyncio.run(_export_project_xlsx_async(job_id, self.request.id))


async def _export_project_xlsx_async(job_id: int, celery_task_id: str):
    """Async implementation of project XLSX export."""
    from app.services.excel_exporter import ExcelExporter
    from app.services.file_storage import FileStorage
    AsyncSessionLocal = create_session_factory()
    async with AsyncSessionLocal() as db:
        try:
            # Get the export job
            job = await safe_scalar(db, select(ExportJob).where(ExportJob.id == job_id))
            if not job:
                logger.error(f"Export job {job_id} not found")
                return

            # Update task ID and status
            job.celery_task_id = celery_task_id
            job.status = ExportJobStatus.PROCESSING
            job.progress = 0
            await db.commit()

            # Publish update
            await publish_export_update(job_id, "progress", {"progress": 0, "status": "processing"}, job.project_id)

            # Get project
            project = await safe_scalar(db, select(Project).where(Project.id == job.project_id))
            if not project:
                raise ValueError(f"Project {job.project_id} not found")

            # Fetch all pages with fz168_raw_response
            result = await db.execute(
                select(Page).where(
                    Page.project_id == job.project_id,
                    Page.fz168_raw_response.isnot(None)
                )
            )
            pages = result.scalars().all()

            if not pages:
                job.status = ExportJobStatus.FAILED
                job.error_message = "No analyzed pages found for this project"
                await db.commit()
                await publish_export_update(job_id, "failed", {"error": job.error_message}, job.project_id)
                return

            # Set total words count for progress tracking
            total_words = 0
            for page in pages:
                page_data = page.fz168_raw_response
                if isinstance(page_data, dict):
                    analysis_data = page_data.get('data', page_data)
                else:
                    analysis_data = page_data
                words = analysis_data.get('all_words', [])
                total_words += len(words)

            job.total_words = total_words
            job.processed_words = 0
            await db.commit()

            logger.info(f"Export job {job_id}: Starting export with {total_words} words from {len(pages)} pages")

            # Aggregate all words from all pages
            all_words_aggregated = []
            processed_words_count = 0

            for idx, page in enumerate(pages):
                # Check for cancellation
                await db.refresh(job)
                if job.cancelled:
                    logger.info(f"Export job {job_id}: Cancelled during word aggregation")
                    job.status = ExportJobStatus.FAILED
                    job.error_message = "Export job was cancelled by user"
                    await db.commit()
                    await publish_export_update(job_id, "cancelled", {"message": "Export cancelled"}, job.project_id)
                    return

                # Update progress - we're processing pages
                page_progress = int((idx / len(pages)) * 50)  # First 50% for page aggregation
                job.progress = page_progress
                await db.commit()
                await publish_export_update(job_id, "progress", {"progress": page_progress, "status": "processing"}, job.project_id)

                page_data = page.fz168_raw_response
                if isinstance(page_data, dict):
                    analysis_data = page_data.get('data', page_data)
                else:
                    analysis_data = page_data

                words = analysis_data.get('all_words', [])
                for word in words:
                    all_words_aggregated.append({
                        **word,
                        'page_url': page.url
                    })
                    processed_words_count += 1

                    # Update word-level progress every 100 words
                    if processed_words_count % 100 == 0:
                        word_progress = 50 + int((processed_words_count / total_words) * 30)  # 50-80%
                        job.progress = min(word_progress, 80)
                        job.processed_words = processed_words_count
                        await db.commit()
                        await publish_export_update(job_id, "progress", {"progress": job.progress, "status": "processing"}, job.project_id)

            analysis_data = {
                'all_words': all_words_aggregated
            }

            # Generate Excel file (30% of progress remaining)
            job.progress = 80
            await db.commit()
            await publish_export_update(job_id, "progress", {"progress": 80, "status": "generating_excel"}, job.project_id)

            # Check for cancellation before expensive Excel generation
            await db.refresh(job)
            if job.cancelled:
                logger.info(f"Export job {job_id}: Cancelled before Excel generation")
                job.status = ExportJobStatus.FAILED
                job.error_message = "Export job was cancelled by user"
                await db.commit()
                await publish_export_update(job_id, "cancelled", {"message": "Export cancelled"}, job.project_id)
                return

            logger.info(f"Export job {job_id}: Generating Excel file with {len(all_words_aggregated)} words")
            logger.info(f"Export job {job_id}: Calling ExcelExporter directly (Celery worker provides concurrency)")
            try:
                # Call ExcelExporter directly (no threading needed - Celery worker already runs in separate process)
                # This avoids asyncio.to_thread() deadlock issues with large result objects
                excel_bytes = ExcelExporter.export_analysis(
                    analysis_data=analysis_data,
                    selected_statuses=None,
                    page_url=None,
                    language=job.language or "ru"
                )
                logger.info(f"Export job {job_id}: ExcelExporter returned successfully, bytes length: {len(excel_bytes)}")
            except Exception as e:
                logger.error(f"Export job {job_id}: Excel generation failed: {e}", exc_info=True)
                raise

            # Validate that the generated file is a valid ZIP/XLSX
            logger.info(f"Export job {job_id}: Starting ZIP validation")
            import zipfile
            import io
            try:
                with zipfile.ZipFile(io.BytesIO(excel_bytes), 'r') as z:
                    # Test the zip integrity by reading its file list
                    file_list = z.namelist()
                    logger.info(f"Export job {job_id}: ZIP validation passed, {len(file_list)} files in archive")
            except zipfile.BadZipFile as e:
                logger.error(f"Generated Excel file is corrupt: {e}")
                raise

            # Check for cancellation after Excel generation but before saving
            logger.info(f"Export job {job_id}: About to refresh job to check cancellation")
            await db.refresh(job)
            logger.info(f"Export job {job_id}: Refreshed job, cancelled={job.cancelled}")
            if job.cancelled:
                logger.info(f"Export job {job_id}: Cancelled after Excel generation, before saving")
                job.status = ExportJobStatus.FAILED
                job.error_message = "Export job was cancelled by user"
                await db.commit()
                await publish_export_update(job_id, "cancelled", {"message": "Export cancelled"}, job.project_id)
                return

            # Save file to storage (90%)
            logger.info(f"Export job {job_id}: Setting progress to 90%")
            job.progress = 90
            logger.info(f"Export job {job_id}: About to commit 90% progress to DB")
            await db.commit()
            logger.info(f"Export job {job_id}: Committed 90% progress, about to publish to Redis (project {job.project_id})")
            await publish_export_update(job_id, "progress", {"progress": 90, "status": "saving_file"}, job.project_id)
            logger.info(f"Export job {job_id}: Published 90% progress to Redis")

            try:
                logger.info(f"Export job {job_id}: Starting file save to storage")
                storage = FileStorage(settings.storage_path)
                
                # Generate filename with domain name and timezone-aware datetime
                # Format: project_words_{domain_name}_{datetime}.xlsx
                domain_name = project.domain
                # Sanitize domain name for filename (replace special characters)
                safe_domain = domain_name.replace('/', '_').replace(':', '_').replace('?', '_')
                
                # Get timezone-aware datetime using client's timezone
                client_timezone = job.timezone or "UTC"
                try:
                    tz = ZoneInfo(client_timezone)
                except ZoneInfoNotFoundError:
                    logger.warning(f"Unknown timezone: {client_timezone}, falling back to UTC")
                    tz = ZoneInfo("UTC")
                
                local_datetime = datetime.now(tz)
                timestamp = local_datetime.strftime("%Y%m%d_%H%M%S")
                filename = f"project_words_{safe_domain}_{timestamp}.xlsx"
                
                file_path = storage.save_excel(
                    user_id=job.user_id,
                    project_id=job.project_id,
                    filename=filename,
                    excel_bytes=excel_bytes
                )
                logger.info(f"Export job {job_id}: Saved Excel file to: {file_path}")
            except Exception as e:
                logger.error(f"Export job {job_id}: Failed to save file to storage: {e}", exc_info=True)
                raise Exception(f"Failed to save file to storage: {e}")

            # Update job as completed (100%)
            logger.info(f"Export job {job_id}: Setting job to completed 100%")
            job.file_path = file_path
            job.file_size = len(excel_bytes)
            job.status = ExportJobStatus.COMPLETED
            job.progress = 100
            logger.info(f"Export job {job_id}: About to commit completed status to DB")
            await db.commit()
            logger.info(f"Export job {job_id}: Committed completed status, about to publish 100% to Redis (project {job.project_id})")

            await publish_export_update(job_id, "completed", {
                "progress": 100,
                "file_path": file_path,
                "file_size": len(excel_bytes),
                "filename": filename
            }, job.project_id)

            logger.info(f"Export job {job_id}: Published completed event, job finished successfully")

        except Exception as e:
            logger.error(f"Export job {job_id} failed: {e}", exc_info=True)
            try:
                job = await safe_scalar(db, select(ExportJob).where(ExportJob.id == job_id))
                if job:
                    job.status = ExportJobStatus.FAILED
                    job.error_message = str(e)
                    await db.commit()
                    await publish_export_update(job_id, "failed", {"error": str(e)}, job.project_id)
            except Exception as inner_e:
                logger.error(f"Failed to update job {job_id} status: {inner_e}")

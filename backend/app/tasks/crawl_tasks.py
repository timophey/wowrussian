import asyncio
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
import redis.asyncio as redis
from celery import current_task

from app.tasks.celery_app import celery_app
from app.core.database import engine, AsyncSessionLocal
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.foreign_word import ForeignWord
from app.models.crawl_queue import CrawlQueue, QueueStatus
from app.models.user import User
from app.services.crawler import Crawler
from app.services.parser import HTMLParser
from app.services.analyzer import WordAnalyzer
from app.services.file_storage import FileStorage
from app.utils.db import safe_scalar


async def publish_update(project_id: int, event: str, data: dict):
    """Publish update to Redis channel."""
    redis_client = redis.from_url(settings.redis_url)
    try:
        await redis_client.publish(
            f"project:{project_id}:updates",
            json.dumps({"event": event, "data": data})
        )
    finally:
        await redis_client.close()


@celery_app.task(bind=True, name="crawl_project")
def crawl_project(self, project_id: int):
    """Main task to crawl a project."""
    asyncio.run(_crawl_project_async(project_id, self.request.id))


async def _analyze_page_in_session(db: AsyncSession, page: Page, project: Project):
    """
    Analyze a page using the provided database session.
    This avoids creating a new session/connection to prevent concurrency issues.
    """
    # Read HTML from file
    storage = FileStorage(settings.storage_path)
    try:
        html_content = storage.get_file_content(page.html_file_path)
    except FileNotFoundError:
        # HTML file missing - mark page as failed
        page.status = PageStatus.FAILED
        await db.commit()
        await publish_update(project.project_id, "error", {"message": f"HTML file not found for page {page.id}"})
        return
    
    # Parse HTML
    parser = HTMLParser()
    text_content = parser.extract_text(html_content)
    
    # Save text to file
    text_path = storage.save_text(
        user_id=project.user_id,
        project_id=page.project_id,
        page_id=page.id,
        text_content=text_content
    )
    page.text_file_path = text_path
    
    # Count words
    words = text_content.split()
    page.words_count = len(words)
    
    # Analyze foreign words
    analyzer = WordAnalyzer()
    analysis = analyzer.analyze(text_content)
    page.foreign_words_count = analysis['foreign_words']
    
    # Delete existing foreign words for this page to avoid duplicates on restart
    await db.execute(
        delete(ForeignWord).where(ForeignWord.page_id == page.id)
    )
    
    # Save foreign words
    for word, count in analysis['foreign_word_frequency'].items():
        fw = ForeignWord(
            page_id=page.id,
            word=word,
            count=count,
            language_guess='en'  # TODO: Better language detection
        )
        db.add(fw)
    
    # Update page status
    page.status = PageStatus.ANALYZED
    await db.commit()
    
    # Publish update
    await publish_update(
        page.project_id,
        "page_analyzed",
        {
            "page_id": page.id,
            "url": page.url,
            "words_count": page.words_count,
            "foreign_words_count": page.foreign_words_count
        }
    )
    
    # Check if project is complete
    await _check_project_completion(page.project_id, db)


async def _crawl_project_async(project_id: int, task_id: str):
    """Async implementation of crawl_project."""
    async with AsyncSessionLocal() as db:
        try:
            # Get project
            project = await safe_scalar(db, select(Project).where(Project.id == project_id))
            if not project:
                return
            
            # Update project status
            project.status = ProjectStatus.CRAWLING
            await db.commit()
            
            # Initialize crawler
            async with Crawler(project.base_url) as crawler:
                # Process queue until empty or stopped
                max_pages = 1000  # Safety limit
                processed_count = 0
                
                while processed_count < max_pages:
                    # Check if project was stopped
                    project = await safe_scalar(db, select(Project).where(Project.id == project_id))
                    if project and project.status == ProjectStatus.STOPPED:
                        await publish_update(project_id, "stopped", {"message": "Project stopped"})
                        return
                    
                    # Get next pending URL from queue
                    queue_item = await safe_scalar(
                        db,
                        select(CrawlQueue).where(
                            CrawlQueue.project_id == project_id,
                            CrawlQueue.status == QueueStatus.PENDING
                        ).order_by(CrawlQueue.created_at).limit(1)
                    )
                    
                    if not queue_item:
                        # No more pending URLs
                        break
                    
                    # Mark as processing
                    queue_item.status = QueueStatus.PROCESSING
                    await db.commit()
                    
                    # Crawl the specific URL
                    page_data = await crawler.crawl_page(queue_item.url)
                    
                    if page_data:
                        # Create page record
                        page = Page(
                            project_id=project_id,
                            url=page_data['url'],
                            status=PageStatus.CRAWLING
                        )
                        db.add(page)
                        await db.commit()
                        await db.refresh(page)
                        
                        # Save HTML to file
                        storage = FileStorage(settings.storage_path)
                        html_path = storage.save_html(
                            user_id=project.user_id,
                            project_id=project_id,
                            page_id=page.id,
                            html_content=page_data['html']
                        )
                        page.html_file_path = html_path
                        page.status = PageStatus.PARSED
                        await db.commit()
                        
                        # Publish update that page was crawled (best effort)
                        try:
                            await publish_update(
                                project_id,
                                "page_crawled",
                                {"page_id": page.id, "url": page.url}
                            )
                        except Exception as e:
                            print(f"Failed to publish page_crawled event: {e}")
                        
                        # Analyze page immediately using the same database session
                        print(f"[DEBUG] Starting analysis for page {page.id} (project {project_id})", flush=True)
                        try:
                            await _analyze_page_in_session(db, page, project)
                            print(f"[DEBUG] Page {page.id} analyzed successfully, status set to ANALYZED", flush=True)
                        except Exception as e:
                            print(f"[ERROR] Analysis failed for page {page.id}: {e}", flush=True)
                            # Mark page as FAILED
                            page.status = PageStatus.FAILED
                            await db.commit()
                            await publish_update(project_id, "error", {"message": f"Analysis failed for page {page.id}: {str(e)}"})
                        
                        # Add discovered links to queue
                        for link in page_data.get('links', []):
                            # Check if link already exists in pages or queue
                            existing_page = await safe_scalar(
                                db,
                                select(Page).where(
                                    Page.project_id == project_id,
                                    Page.url == link
                                )
                            )
                            if existing_page:
                                continue
                            existing_queue = await safe_scalar(
                                db,
                                select(CrawlQueue).where(
                                    CrawlQueue.project_id == project_id,
                                    CrawlQueue.url == link
                                )
                            )
                            if not existing_queue:
                                new_queue = CrawlQueue(
                                    project_id=project_id,
                                    url=link,
                                    status=QueueStatus.PENDING
                                )
                                db.add(new_queue)
                        await db.commit()
                        
                        processed_count += 1
                    
                    # Mark queue item as completed
                    queue_item.status = QueueStatus.COMPLETED
                    await db.commit()
            
            # Check if all pages are processed
            await _check_project_completion(project_id, db)
            
        except Exception as e:
            await publish_update(project_id, "error", {"message": str(e)})
            raise


@celery_app.task(bind=True, name="parse_and_analyze_page")
def parse_and_analyze_page(self, page_id: int):
    """Task to parse HTML and analyze page."""
    asyncio.run(_parse_and_analyze_page_async(page_id))


async def _parse_and_analyze_page_async(page_id: int):
    """Async implementation of parse_and_analyze_page."""
    import sys
    db = AsyncSessionLocal()
    try:
        # First, check if page exists
        page = await safe_scalar(db, select(Page).where(Page.id == page_id))
        print(f"[DEBUG] _parse_and_analyze_page_async called for page_id={page_id}, page found: {page is not None}, page status: {page.status if page else 'N/A'}", flush=True)
        if not page:
            print(f"[WARN] Page {page_id} not found in analysis function", flush=True)
            return
        
        project_id = page.project_id
        
        # Get project
        project = await safe_scalar(db, select(Project).where(Project.id == page.project_id))
        if not project:
            return
        
        # Read HTML from file
        storage = FileStorage(settings.storage_path)
        try:
            html_content = storage.get_file_content(page.html_file_path)
        except FileNotFoundError:
            # HTML file missing - mark page as failed
            page.status = PageStatus.FAILED
            await db.commit()
            await publish_update(project_id, "error", {"message": f"HTML file not found for page {page_id}"})
            return
        
        # Parse HTML
        parser = HTMLParser()
        text_content = parser.extract_text(html_content)
        
        # Save text to file
        text_path = storage.save_text(
            user_id=project.user_id,
            project_id=page.project_id,
            page_id=page.id,
            text_content=text_content
        )
        page.text_file_path = text_path
        
        # Count words
        words = text_content.split()
        page.words_count = len(words)
        
        # Analyze foreign words
        analyzer = WordAnalyzer()
        analysis = analyzer.analyze(text_content)
        page.foreign_words_count = analysis['foreign_words']
        
        # Delete existing foreign words for this page to avoid duplicates on restart
        await db.execute(
            delete(ForeignWord).where(ForeignWord.page_id == page.id)
        )
        
        # Save foreign words
        for word, count in analysis['foreign_word_frequency'].items():
            fw = ForeignWord(
                page_id=page.id,
                word=word,
                count=count,
                language_guess='en'  # TODO: Better language detection
            )
            db.add(fw)
        
        # Update page status
        page.status = PageStatus.ANALYZED
        await db.commit()
        
        print(f"[DEBUG] Page {page_id} analyzed successfully, status set to ANALYZED", flush=True)
        
        # Publish update
        await publish_update(
            page.project_id,
            "page_analyzed",
            {
                "page_id": page.id,
                "url": page.url,
                "words_count": page.words_count,
                "foreign_words_count": page.foreign_words_count
            }
        )
        
        # Check if project is complete
        await _check_project_completion(page.project_id, db)
        
    except Exception as e:
        # On any error, mark page as failed and publish error
        try:
            page = await safe_scalar(db, select(Page).where(Page.id == page_id))
            if page:
                page.status = PageStatus.FAILED
                await db.commit()
                await publish_update(page.project_id, "error", {"message": str(e)})
        except Exception as inner_e:
            # If even this fails, try to publish a generic error
            print(f"Error marking page as failed: {inner_e}")
            try:
                await publish_update(project_id if 'project_id' in locals() else 0, "error", {"message": f"Failed to mark page as failed: {str(e)}"})
            except:
                pass
        raise
    finally:
        # Ensure database session is always closed
        await db.close()


async def _delete_page_completely(db: AsyncSession, page: Page, storage: FileStorage):
    """Delete a page and all its associated data and files."""
    # Delete foreign words first (though cascade should handle this)
    await db.execute(
        delete(ForeignWord).where(ForeignWord.page_id == page.id)
    )
    
    # Delete files from storage
    try:
        if page.html_file_path:
            storage.delete_file(page.html_file_path)
    except Exception as e:
        print(f"Error deleting HTML file {page.html_file_path}: {e}")
    
    try:
        if page.text_file_path:
            storage.delete_file(page.text_file_path)
    except Exception as e:
        print(f"Error deleting text file {page.text_file_path}: {e}")
    
    # Delete the page record
    await db.delete(page)


async def _check_project_completion(project_id: int, db: AsyncSession):
    """Check if all pages are processed and update project status."""
    # Count total pages
    total_pages = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(Page.project_id == project_id)
    )
    
    # Count analyzed pages
    analyzed_pages = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.status == PageStatus.ANALYZED
        )
    )
    
    # Count failed pages
    failed_pages = await safe_scalar(
        db,
        select(func.count()).select_from(Page).where(
            Page.project_id == project_id,
            Page.status == PageStatus.FAILED
        )
    )
    
    if total_pages > 0 and (analyzed_pages + failed_pages) >= total_pages:
        # All pages processed
        project = await safe_scalar(db, select(Project).where(Project.id == project_id))
        if project:
            if failed_pages > 0:
                project.status = ProjectStatus.FAILED
            else:
                project.status = ProjectStatus.COMPLETED
            await db.commit()
            
            # Publish completion event
            await publish_update(
                project_id,
                "project_completed",
                {"status": project.status.value}
            )
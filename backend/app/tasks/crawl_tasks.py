import asyncio
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
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


async def publish_update(project_id: int, event: str, data: dict):
    """Publish update to Redis channel."""
    redis_client = redis.from_url(settings.redis_url)
    try:
        await redis_client.publish(
            f"project:{project_id}:updates",
            {"event": event, "data": data}
        )
    finally:
        await redis_client.close()


@celery_app.task(bind=True, name="crawl_project")
def crawl_project(self, project_id: int):
    """Main task to crawl a project."""
    asyncio.run(_crawl_project_async(project_id, self.request.id))


async def _crawl_project_async(project_id: int, task_id: str):
    """Async implementation of crawl_project."""
    async with AsyncSessionLocal() as db:
        try:
            # Get project
            project = await db.get(Project, project_id)
            if not project:
                return
            
            # Update project status
            project.status = ProjectStatus.CRAWLING
            await db.commit()
            
            # Get all pending URLs from queue
            result = await db.execute(
                select(CrawlQueue).where(
                    CrawlQueue.project_id == project_id,
                    CrawlQueue.status == QueueStatus.PENDING
                ).order_by(CrawlQueue.created_at)
            )
            queue_items = result.scalars().all()
            
            if not queue_items:
                await publish_update(project_id, "error", {"message": "No URLs in queue"})
                return
            
            # Initialize crawler
            async with Crawler(project.base_url) as crawler:
                # Process each URL in queue
                for queue_item in queue_items:
                    # Check if project was stopped
                    project = await db.get(Project, project_id)
                    if project.status == ProjectStatus.STOPPED:
                        await publish_update(project_id, "stopped", {"message": "Project stopped"})
                        return
                    
                    # Update queue item status
                    queue_item.status = QueueStatus.PROCESSING
                    await db.commit()
                    
                    # Crawl the page
                    page_data = await crawler.crawl(max_pages=1)
                    
                    if page_data:
                        page_info = page_data[0]
                        
                        # Create page record
                        page = Page(
                            project_id=project_id,
                            url=page_info['url'],
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
                            html_content=page_info['html']
                        )
                        page.html_file_path = html_path
                        
                        # Update page status to parsed
                        page.status = PageStatus.PARSED
                        await db.commit()
                        
                        # Publish update
                        await publish_update(
                            project_id,
                            "page_crawled",
                            {"page_id": page.id, "url": page.url}
                        )
                        
                        # Trigger parse and analyze tasks
                        parse_and_analyze_page.delay(page.id)
                    
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
    async with AsyncSessionLocal() as db:
        try:
            page = await db.get(Page, page_id)
            if not page:
                return
            
            # Get project
            project = await db.get(Project, page.project_id)
            if not project:
                return
            
            # Read HTML from file
            storage = FileStorage(settings.storage_path)
            try:
                html_content = storage.get_file_content(page.html_file_path)
            except FileNotFoundError:
                page.status = PageStatus.FAILED
                await db.commit()
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
            
        except Exception as e:
            # Update page status to failed
            page = await db.get(Page, page_id)
            if page:
                page.status = PageStatus.FAILED
                await db.commit()
            await publish_update(page.project_id, "error", {"message": str(e)})
            raise


async def _check_project_completion(project_id: int, db: AsyncSession):
    """Check if all pages are processed and update project status."""
    # Count total pages
    total_pages = await db.scalar(
        select(Page).where(Page.project_id == project_id)
    )
    
    # Count analyzed pages
    analyzed_pages = await db.scalar(
        select(Page).where(
            Page.project_id == project_id,
            Page.status == PageStatus.ANALYZED
        )
    )
    
    # Count failed pages
    failed_pages = await db.scalar(
        select(Page).where(
            Page.project_id == project_id,
            Page.status == PageStatus.FAILED
        )
    )
    
    if total_pages > 0 and (analyzed_pages + failed_pages) >= total_pages:
        # All pages processed
        project = await db.get(Project, project_id)
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
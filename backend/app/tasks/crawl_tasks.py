import asyncio
import json
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
import redis.asyncio as redis
from celery import current_task

from app.tasks.celery_app import celery_app
from app.core.database import create_session_factory
from app.core.config import settings
from app.models.project import Project, ProjectStatus
from app.models.page import Page, PageStatus
from app.models.foreign_word import ForeignWord
from app.models.russian_word import RussianWord
from app.models.crawl_queue import CrawlQueue, QueueStatus
from app.models.user import User
from app.services.crawler import Crawler
from app.services.parser import HTMLParser
from app.services.word_analyzer_interface import HybridWordAnalyzer
from app.services.file_storage import FileStorage
from app.utils.db import safe_scalar


async def publish_update(project_id: int, event: str, data: dict):
    """Publish update to Redis channel."""
    async with redis.from_url(settings.redis_url) as redis_client:
        await redis_client.publish(
            f"project:{project_id}:updates",
            json.dumps({"event": event, "data": data})
        )


async def publish_stats_update(project_id: int, db: AsyncSession):
    """Compute and publish current project stats to avoid separate GET request."""
    # Count pages by status
    status_counts_result = await db.execute(
        select(Page.status, func.count(Page.id))
        .where(Page.project_id == project_id)
        .group_by(Page.status)
    )
    status_dist = {status.value: count for status, count in status_counts_result.all()}
    total_pages = sum(status_dist.values())
    
    # Count foreign words
    total_foreign_words = await safe_scalar(
        db,
        select(func.sum(Page.foreign_words_count)).where(Page.project_id == project_id)
    ) or 0
    
    # Count unique foreign words
    unique_foreign_words = await safe_scalar(
        db,
        select(func.count(func.distinct(ForeignWord.word)))
        .select_from(ForeignWord)
        .join(Page)
        .where(Page.project_id == project_id)
    ) or 0
    
    # Count queue items
    pending_queue = await safe_scalar(
        db,
        select(func.count()).select_from(CrawlQueue).where(
            CrawlQueue.project_id == project_id,
            CrawlQueue.status == QueueStatus.PENDING
        )
    ) or 0
    
    processing_queue = await safe_scalar(
        db,
        select(func.count()).select_from(CrawlQueue).where(
            CrawlQueue.project_id == project_id,
            CrawlQueue.status == QueueStatus.PROCESSING
        )
    ) or 0
    
    # Get top foreign words
    top_words_result = await db.execute(
        select(ForeignWord.word, func.sum(ForeignWord.count).label("total_count"))
        .join(Page)
        .where(Page.project_id == project_id)
        .group_by(ForeignWord.word)
        .order_by(func.sum(ForeignWord.count).desc())
        .limit(20)
    )
    top_foreign_words = [
        {"word": word, "count": count}
        for word, count in top_words_result.all()
    ]
    
    # Calculate totals
    total_words = await safe_scalar(
        db,
        select(func.sum(Page.words_count)).where(Page.project_id == project_id)
    ) or 0
    
    foreign_percentage = (total_foreign_words / total_words * 100) if total_words > 0 else 0
    avg_words = total_words / total_pages if total_pages > 0 else 0
    avg_foreign = total_foreign_words / total_pages if total_pages > 0 else 0
    
    # Compute violations and risk level from pages with fz168_summary
    risk_level_distribution = {"high": 0, "medium": 0, "low": 0}
    total_violations = 0
    
    pages_result = await db.execute(
        select(Page.fz168_summary).where(
            Page.project_id == project_id,
            Page.fz168_summary.isnot(None)
        )
    )
    for (summary,) in pages_result.all():
        if summary and isinstance(summary, dict):
            risk_level = summary.get('risk_level', 'low')
            if risk_level in risk_level_distribution:
                risk_level_distribution[risk_level] += 1
            total_violations += summary.get('violation_count', 0)
    
    stats = {
        "project_id": project_id,
        "total_pages": total_pages,
        "status_distribution": status_dist,
        "total_words": total_words,
        "total_foreign_words": total_foreign_words,
        "unique_foreign_words": unique_foreign_words,
        "foreign_percentage": foreign_percentage,
        "average_words_per_page": round(avg_words, 2),
        "average_foreign_per_page": round(avg_foreign, 2),
        "top_foreign_words": top_foreign_words,
        "queue_pending": pending_queue,
        "queue_processing": processing_queue,
        "risk_level_distribution": risk_level_distribution,
        "total_violations": total_violations
    }
    
    await publish_update(project_id, "stats_update", stats)


async def is_project_stopped(project_id: int) -> bool:
    """Check if project has been marked as stopped (via Redis for fast access)."""
    try:
        async with redis.from_url(settings.redis_url) as redis_client:
            stop_flag = await redis_client.get(f"project:{project_id}:stop")
            return stop_flag is not None
    except Exception:
        # Fallback to database check if Redis fails
        return False


async def set_project_stop_flag(project_id: int):
    """Set stop flag in Redis for immediate effect."""
    try:
        async with redis.from_url(settings.redis_url) as redis_client:
            await redis_client.set(f"project:{project_id}:stop", "1", ex=3600)  # Expire after 1 hour
    except Exception as e:
        print(f"Failed to set stop flag in Redis: {e}")


async def clear_project_stop_flag(project_id: int):
    """Clear stop flag in Redis."""
    try:
        async with redis.from_url(settings.redis_url) as redis_client:
            await redis_client.delete(f"project:{project_id}:stop")
    except Exception as e:
        print(f"Failed to clear stop flag in Redis: {e}")


@celery_app.task(bind=True, name="crawl_project")
def crawl_project(self, project_id: int):
    """Main task to crawl a project."""
    asyncio.run(_crawl_project_async(project_id, self.request.id))


async def _analyze_page_in_session(db: AsyncSession, page: Page, project: Project):
    """
    Analyze a page using the provided database session.
    This avoids creating a new session/connection to prevent concurrency issues.
    """
    # Check if project was stopped before starting analysis
    if await is_project_stopped(page.project_id):
        page.status = PageStatus.FAILED
        await db.commit()
        await publish_update(page.project_id, "stopped", {"message": f"Analysis stopped for page {page.id}"})
        return
    
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
    
    # Check again before expensive analysis
    if await is_project_stopped(page.project_id):
        page.status = PageStatus.FAILED
        await db.commit()
        await publish_update(page.project_id, "stopped", {"message": f"Analysis stopped for page {page.id}"})
        return
    
    # Load project whitelist words
    from app.models.whitelist_word import WhitelistWord
    whitelist_result = await db.execute(
        select(WhitelistWord).where(WhitelistWord.project_id == page.project_id)
    )
    whitelist_words = [wl.word for wl in whitelist_result.scalars().all()]
    
    # DEBUG: Log whitelist words
    import sys
    print(f"[DEBUG] Page {page.id} whitelist words loaded: {whitelist_words}", file=sys.stderr)
    
    # Analyze foreign words using hybrid analyzer (168fz with fallback)
    print(f"\n\n*** ANALYZING PAGE {page.id} with text length {len(text_content)}, whitelist words: {len(whitelist_words)} ***\n", file=sys.stderr)
    analyzer = HybridWordAnalyzer()
    analysis = await analyzer.analyze(text_content, allowed_words=whitelist_words if whitelist_words else None)
    page.foreign_words_count = analysis['foreign_words']
    
    # Save 168fz metadata if available (when 168fz was used)
    if 'fz168_metadata' in analysis:
        page.fz168_statistics = analysis['fz168_metadata']['statistics']
        page.fz168_summary = analysis['fz168_metadata']['summary']
        page.fz168_checks = analysis['fz168_metadata']['checks']
        page.fz168_dictionaries = analysis['fz168_metadata']['dictionaries']
    
    # Save complete raw 168fz response if available
    if 'fz168_raw_response' in analysis:
        page.fz168_raw_response = analysis['fz168_raw_response']
    
    # Delete existing foreign words for this page to avoid duplicates on restart
    await db.execute(
        delete(ForeignWord).where(ForeignWord.page_id == page.id)
    )
    
    # Create mappings from detected_words
    language_map = {}
    source_map = {}
    for detected in analysis['detected_words']:
        if detected['is_foreign']:
            language_map[detected['word']] = detected.get('language_guess')
            source_map[detected['word']] = detected.get('source')
    
    # DEBUG: Log mapping info
    import sys
    print(f"[DEBUG] detected_words count: {len(analysis['detected_words'])}, foreign count: {sum(1 for d in analysis['detected_words'] if d['is_foreign'])}", file=sys.stderr)
    print(f"[DEBUG] source_map sample: {dict(list(source_map.items())[:5])}", file=sys.stderr)
    print(f"[DEBUG] foreign_word_frequency sample: {dict(list(analysis['foreign_word_frequency'].items())[:5])}", file=sys.stderr)
    
    # Save foreign words with proper language detection and source
    for word, count in analysis['foreign_word_frequency'].items():
        fw = ForeignWord(
            page_id=page.id,
            word=word,
            count=count,
            language_guess=language_map.get(word),
            source=source_map.get(word)
        )
        db.add(fw)
    
    # Delete existing russian words for this page to avoid duplicates on restart
    await db.execute(
        delete(RussianWord).where(RussianWord.page_id == page.id)
    )
    
    # Save russian words with source information
    for word, count in analysis['russian_word_frequency'].items():
        # Find source from detected_words (already built source_map for foreign, need to build for russian)
        source = None
        for detected in analysis['detected_words']:
            if detected['word'] == word and not detected['is_foreign']:
                source = detected.get('source')
                break
        rw = RussianWord(
            page_id=page.id,
            word=word,
            count=count,
            source=source
        )
        db.add(rw)
    
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
            "foreign_words_count": page.foreign_words_count,
            "fz168_summary": page.fz168_summary,
            "fz168_statistics": page.fz168_statistics,
            "fz168_checks": page.fz168_checks,
            "fz168_dictionaries": page.fz168_dictionaries,
            "fz168_raw_response": page.fz168_raw_response
        }
    )
    
    # Publish stats update
    await publish_stats_update(page.project_id, db)
    
    # Check if project is complete
    await _check_project_completion(page.project_id, db)


async def _crawl_project_async(project_id: int, task_id: str):
    """Async implementation of crawl_project."""
    AsyncSessionLocal = create_session_factory()
    
    # Clear any previous stop flag when starting
    await clear_project_stop_flag(project_id)
    
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
                    # Check if project was stopped (using Redis for fast access)
                    if await is_project_stopped(project_id):
                        await publish_update(project_id, "stopped", {"message": "Project stopped"})
                        # Publish stats before returning
                        await publish_stats_update(project_id, db)
                        # Update DB status as well
                        project = await safe_scalar(db, select(Project).where(Project.id == project_id))
                        if project:
                            project.status = ProjectStatus.STOPPED
                            await db.commit()
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
                            # Publish stats update after page crawled
                            await publish_stats_update(project_id, db)
                        except Exception as e:
                            print(f"Failed to publish page_crawled event: {e}")
                        
                        # Analyze page immediately using the same database session
                        print(f"[DEBUG] Starting analysis for page {page.id} (project {project_id})", flush=True)
                        try:
                            await _analyze_page_in_session(db, page, project)
                            print(f"[DEBUG] Page {page.id} analyzed successfully, status set to ANALYZED", flush=True)
                        except Exception as e:
                            print(f"[ERROR] Analysis failed for page {page.id}: {e}", flush=True)
                            # Rollback the session to clear the broken transaction state
                            await db.rollback()
                            # Refresh the page object to ensure it's in a valid state
                            await db.refresh(page)
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
            
            # Publish final stats when crawling is complete
            await publish_stats_update(project_id, db)
            
        except Exception as e:
            await publish_update(project_id, "error", {"message": str(e)})
            raise
        finally:
            # Clear stop flag when task completes
            await clear_project_stop_flag(project_id)


@celery_app.task(bind=True, name="parse_and_analyze_page")
def parse_and_analyze_page(self, page_id: int):
    """Task to parse HTML and analyze page."""
    asyncio.run(_parse_and_analyze_page_async(page_id))


async def _parse_and_analyze_page_async(page_id: int):
    """Async implementation of parse_and_analyze_page."""
    import sys
    AsyncSessionLocal = create_session_factory()
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
        
        # Load project whitelist words
        from app.models.whitelist_word import WhitelistWord
        whitelist_result = await db.execute(
            select(WhitelistWord).where(WhitelistWord.project_id == page.project_id)
        )
        whitelist_words = [wl.word for wl in whitelist_result.scalars().all()]
        
        # Analyze foreign words using hybrid analyzer (168fz with fallback)
        analyzer = HybridWordAnalyzer()
        analysis = await analyzer.analyze(text_content, allowed_words=whitelist_words if whitelist_words else None)
        page.foreign_words_count = analysis['foreign_words']
        
        # Save 168fz metadata if available (when 168fz was used)
        if 'fz168_metadata' in analysis:
            page.fz168_statistics = analysis['fz168_metadata']['statistics']
            page.fz168_summary = analysis['fz168_metadata']['summary']
            page.fz168_checks = analysis['fz168_metadata']['checks']
            page.fz168_dictionaries = analysis['fz168_metadata']['dictionaries']
        
        # Save complete raw 168fz response if available
        if 'fz168_raw_response' in analysis:
            page.fz168_raw_response = analysis['fz168_raw_response']
        
        # Delete existing foreign words for this page to avoid duplicates on restart
        await db.execute(
            delete(ForeignWord).where(ForeignWord.page_id == page.id)
        )
        
        # Create mappings from detected_words
        language_map = {}
        source_map = {}
        for detected in analysis['detected_words']:
            if detected['is_foreign']:
                language_map[detected['word']] = detected.get('language_guess')
                source_map[detected['word']] = detected.get('source')
        
        # Save foreign words with proper language detection and source
        for word, count in analysis['foreign_word_frequency'].items():
            fw = ForeignWord(
                page_id=page.id,
                word=word,
                count=count,
                language_guess=language_map.get(word),
                source=source_map.get(word)
            )
            db.add(fw)
        
        # Delete existing russian words for this page to avoid duplicates on restart
        await db.execute(
            delete(RussianWord).where(RussianWord.page_id == page.id)
        )
        
        # Save russian words with source information
        for word, count in analysis['russian_word_frequency'].items():
            # Find source from detected_words
            source = None
            for detected in analysis['detected_words']:
                if detected['word'] == word and not detected['is_foreign']:
                    source = detected.get('source')
                    break
            rw = RussianWord(
                page_id=page.id,
                word=word,
                count=count,
                source=source
            )
            db.add(rw)
        
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
        # On any errors, mark page as failed and publish error
        await db.rollback()  # Clear any broken transaction state
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
    """Check if all pages are processed and crawl queue is empty."""
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
    
    # Count pending and processing queue items
    pending_queue_items = await safe_scalar(
        db,
        select(func.count()).select_from(CrawlQueue).where(
            CrawlQueue.project_id == project_id,
            CrawlQueue.status.in_([QueueStatus.PENDING, QueueStatus.PROCESSING])
        )
    )
    
    # Only complete if all pages are processed AND no items in queue
    if total_pages > 0 and (analyzed_pages + failed_pages) >= total_pages and (pending_queue_items or 0) == 0:
        # All pages processed and queue is empty
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
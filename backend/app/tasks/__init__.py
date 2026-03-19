# Tasks package initialization
from app.tasks.celery_app import celery_app as celery
from app.tasks.crawl_tasks import crawl_project, parse_and_analyze_page

__all__ = ['celery', 'crawl_project', 'parse_and_analyze_page']
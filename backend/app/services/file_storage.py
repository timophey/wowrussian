import os
from pathlib import Path
from typing import Optional
from fastapi import HTTPException


class FileStorage:
    """File storage service for storing HTML and text files."""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_user_dir(self, user_id: int) -> Path:
        """Get user directory."""
        user_dir = self.base_path / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir
    
    def _get_project_dir(self, user_id: int, project_id: int) -> Path:
        """Get project directory."""
        project_dir = self._get_user_dir(user_id) / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    def _get_html_dir(self, user_id: int, project_id: int) -> Path:
        """Get HTML directory."""
        html_dir = self._get_project_dir(user_id, project_id) / "html"
        html_dir.mkdir(parents=True, exist_ok=True)
        return html_dir
    
    def _get_text_dir(self, user_id: int, project_id: int) -> Path:
        """Get text directory."""
        text_dir = self._get_project_dir(user_id, project_id) / "text"
        text_dir.mkdir(parents=True, exist_ok=True)
        return text_dir
    
    def save_html(self, user_id: int, project_id: int, page_id: int, html_content: str) -> str:
        """Save HTML content to file. Returns relative path."""
        html_dir = self._get_html_dir(user_id, project_id)
        file_path = html_dir / f"{page_id}.html"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        # Return relative path from base storage
        return str(file_path.relative_to(self.base_path))
    
    def save_text(self, user_id: int, project_id: int, page_id: int, text_content: str) -> str:
        """Save text content to file. Returns relative path."""
        text_dir = self._get_text_dir(user_id, project_id)
        file_path = text_dir / f"{page_id}.txt"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(text_content)
        
        # Return relative path from base storage
        return str(file_path.relative_to(self.base_path))
    
    def get_file_path(self, relative_path: str) -> Path:
        """Get absolute file path from relative path."""
        file_path = self.base_path / relative_path
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return file_path
    
    def get_file_content(self, relative_path: str) -> str:
        """Read file content."""
        file_path = self.get_file_path(relative_path)
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def delete_project_files(self, user_id: int, project_id: int) -> None:
        """Delete all files for a project."""
        project_dir = self._get_project_dir(user_id, project_id)
        if project_dir.exists():
            import shutil
            shutil.rmtree(project_dir)
    
    def delete_page_files(self, user_id: int, project_id: int, page_id: int) -> None:
        """Delete files for a specific page."""
        html_file = self._get_html_dir(user_id, project_id) / f"{page_id}.html"
        text_file = self._get_text_dir(user_id, project_id) / f"{page_id}.txt"
        
        if html_file.exists():
            html_file.unlink()
        if text_file.exists():
            text_file.unlink()
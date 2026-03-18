import os
import tempfile
import pytest
from app.services.file_storage import FileStorage


def test_file_storage_initialization():
    """Test FileStorage can be initialized."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)
        assert storage.base_path.exists()
        assert storage.base_path == tmpdir


def test_save_and_read_html():
    """Test saving and reading HTML content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)
        html_content = "<html><body>Test</body></html>"
        
        path = storage.save_html(user_id=1, project_id=1, page_id=1, html_content=html_content)
        assert path is not None
        
        # Read back
        read_content = storage.get_file_content(path)
        assert read_content == html_content


def test_save_and_read_text():
    """Test saving and reading text content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)
        text_content = "Hello World\nTest"
        
        path = storage.save_text(user_id=1, project_id=1, page_id=1, text_content=text_content)
        assert path is not None
        
        # Read back
        read_content = storage.get_file_content(path)
        assert read_content == text_content


def test_delete_project_files():
    """Test deleting project files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)
        
        # Create some files
        storage.save_html(1, 1, 1, "<html>test</html>")
        storage.save_text(1, 1, 1, "test text")
        
        # Verify files exist
        project_dir = os.path.join(tmpdir, "1", "1")
        assert os.path.exists(project_dir)
        
        # Delete
        storage.delete_project_files(1, 1)
        
        # Verify deleted
        assert not os.path.exists(project_dir)


def test_file_not_found():
    """Test FileNotFoundError is raised for missing files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = FileStorage(tmpdir)
        
        with pytest.raises(FileNotFoundError):
            storage.get_file_content("nonexistent/file.html")
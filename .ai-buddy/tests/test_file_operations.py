"""Tests for the file operations module."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from pydantic import ValidationError

from file_operations import (
    FileOperation,
    FileCommand,
    FileOperationResponse,
    FileOperationResult,
    FileOperationExecutor,
    detect_file_operation_request,
)


class TestFileOperationModels:
    """Test Pydantic models for file operations."""

    @pytest.mark.unit
    def test_file_operation_enum(self):
        """Test FileOperation enum values."""
        assert FileOperation.CREATE == "create"
        assert FileOperation.UPDATE == "update"
        assert FileOperation.DELETE == "delete"

    @pytest.mark.unit
    def test_file_command_valid(self):
        """Test creating valid FileCommand."""
        cmd = FileCommand(
            operation=FileOperation.CREATE,
            path="src/new_file.py",
            content="print('hello')",
            description="Create a new Python file",
            overwrite=False,
        )

        assert cmd.operation == FileOperation.CREATE
        assert cmd.path == "src/new_file.py"
        assert cmd.content == "print('hello')"
        assert cmd.overwrite is False

    @pytest.mark.unit
    def test_file_command_validation(self):
        """Test FileCommand validation."""
        # Missing required fields
        with pytest.raises(ValidationError):
            FileCommand()  # Missing operation, path, description

        # Invalid operation
        with pytest.raises(ValidationError):
            FileCommand(operation="invalid_op", path="test.py", description="Test")

        # Valid command without content (for delete operations)
        cmd = FileCommand(
            operation=FileOperation.DELETE,
            path="test.py",
            description="Delete test file",
        )
        assert cmd.operation == FileOperation.DELETE
        assert cmd.content is None

    @pytest.mark.unit
    def test_file_operation_response(self):
        """Test FileOperationResponse model."""
        response = FileOperationResponse(
            summary="Created configuration files",
            files=[  # Note: actual field is 'files', not 'operations'
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="config.json",
                    content='{"key": "value"}',
                    description="Configuration file",
                )
            ],
            warnings=["File will be created in project root"],
        )

        assert response.summary == "Created configuration files"
        assert len(response.files) == 1  # Note: 'files' not 'operations'
        assert len(response.warnings) == 1

    @pytest.mark.unit
    def test_file_operation_result(self):
        """Test FileOperationResult model."""
        result = FileOperationResult(
            success=True,
            files_created=["file1.py", "file2.py"],
            files_updated=["config.json"],
            files_deleted=["old.txt"],
            errors=["Could not create file3.py: Permission denied"],
            operations_performed=[  # Note: this is a List[dict], not int
                {"operation": "create", "path": "file1.py", "success": True},
                {"operation": "create", "path": "file2.py", "success": True},
                {"operation": "update", "path": "config.json", "success": True},
            ],
        )

        assert result.success is True
        assert len(result.files_created) == 2
        assert len(result.files_updated) == 1
        assert len(result.files_deleted) == 1
        assert len(result.errors) == 1
        assert len(result.operations_performed) == 3


class TestFileOperationDetection:
    """Test file operation detection."""

    @pytest.mark.unit
    def test_detect_file_operation_request_positive(self):
        """Test detecting file operation requests."""
        positive_queries = [
            "Create a new test file",
            "Please create config.json with these settings",
            "Update the README.md file",
            "Can you update the documentation?",
            "Delete the old backup files",
            "Make a new Python script",
            "Generate a configuration file",
            "Write a test for this function",
            "Add a new module called utils.py",
        ]

        for query in positive_queries:
            assert detect_file_operation_request(query), f"Should detect: {query}"

    @pytest.mark.unit
    def test_detect_file_operation_request_negative(self):
        """Test not detecting non-file operation requests."""
        negative_queries = [
            "What does this function do?",
            "Explain how authentication works",
            "Why is my code failing?",
            "How do I use this API?",
            "Tell me about Python decorators",
            "Debug this error message",
        ]

        for query in negative_queries:
            assert not detect_file_operation_request(
                query
            ), f"Should not detect: {query}"


# Path validation is handled internally by FileOperationExecutor


class TestFileOperationExecutor:
    """Test FileOperationExecutor functionality."""

    @pytest.mark.unit
    def test_executor_initialization(self, temp_dir):
        """Test executor initialization."""
        executor = FileOperationExecutor(str(temp_dir))

        assert executor.project_root == temp_dir
        assert isinstance(executor.project_root, Path)

    @pytest.mark.unit
    def test_create_file_success(self, temp_dir):
        """Test successful file creation."""
        executor = FileOperationExecutor(str(temp_dir))

        operations = FileOperationResponse(
            summary="Create test file",
            files=[  # Use 'files' not 'operations'
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="test_file.py",
                    content="def hello():\n    print('Hello')",
                    description="Test file",
                )
            ],
        )

        result = executor.execute_operations(operations)

        # Verify result
        assert len(result.files_created) == 1
        assert "test_file.py" in result.files_created
        assert len(result.errors) == 0
        assert len(result.operations_performed) == 1

        # Verify file exists
        created_file = temp_dir / "test_file.py"
        assert created_file.exists()
        assert created_file.read_text() == "def hello():\n    print('Hello')"

    @pytest.mark.unit
    def test_create_file_already_exists(self, temp_dir):
        """Test creating file that already exists."""
        executor = FileOperationExecutor(str(temp_dir))

        # Create existing file
        existing = temp_dir / "existing.txt"
        existing.write_text("Original content")

        operations = FileOperationResponse(
            summary="Create file",
            files=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="existing.txt",
                    content="New content",
                    description="Test",
                    overwrite=False,
                )
            ],
        )

        result = executor.execute_operations(operations)

        # Should have error
        assert len(result.errors) == 1
        assert "already exists" in result.errors[0]
        assert len(result.files_created) == 0

        # Original content unchanged
        assert existing.read_text() == "Original content"

    @pytest.mark.unit
    def test_create_file_with_overwrite(self, temp_dir):
        """Test creating file with overwrite flag."""
        executor = FileOperationExecutor(str(temp_dir))

        # Create existing file
        existing = temp_dir / "existing.txt"
        existing.write_text("Original content")

        operations = FileOperationResponse(
            summary="Create file",
            files=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="existing.txt",
                    content="New content",
                    description="Test",
                    overwrite=True,
                )
            ],
        )

        result = executor.execute_operations(operations)

        # Should succeed
        assert len(result.files_created) == 1
        assert len(result.errors) == 0

        # Content should be updated
        assert existing.read_text() == "New content"

    @pytest.mark.unit
    def test_create_nested_directories(self, temp_dir):
        """Test creating file in nested directories."""
        executor = FileOperationExecutor(str(temp_dir))

        operations = FileOperationResponse(
            summary="Create nested file",
            files=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="src/components/ui/button.py",
                    content="class Button: pass",
                    description="Button component",
                )
            ],
        )

        result = executor.execute_operations(operations)

        # Should succeed and create directories
        assert len(result.files_created) == 1
        assert (temp_dir / "src" / "components" / "ui").exists()
        assert (temp_dir / "src" / "components" / "ui" / "button.py").exists()

    @pytest.mark.unit
    def test_update_file_success(self, temp_dir):
        """Test successful file update."""
        executor = FileOperationExecutor(str(temp_dir))

        # Create file to update
        target = temp_dir / "update_me.txt"
        target.write_text("Original content")

        operations = FileOperationResponse(
            summary="Update file",
            files=[
                FileCommand(
                    operation=FileOperation.UPDATE,
                    path="update_me.txt",
                    content="Updated content",
                    description="Update test",
                )
            ],
        )

        result = executor.execute_operations(operations)

        assert len(result.files_updated) == 1
        assert "update_me.txt" in result.files_updated
        assert target.read_text() == "Updated content"

    @pytest.mark.unit
    def test_update_nonexistent_file(self, temp_dir):
        """Test updating file that doesn't exist."""
        executor = FileOperationExecutor(str(temp_dir))

        operations = FileOperationResponse(
            summary="Update file",
            files=[
                FileCommand(
                    operation=FileOperation.UPDATE,
                    path="nonexistent.txt",
                    content="Content",
                    description="Update test",
                )
            ],
        )

        result = executor.execute_operations(operations)

        assert len(result.errors) == 1
        assert "does not exist" in result.errors[0]

    @pytest.mark.unit
    def test_delete_file_success(self, temp_dir):
        """Test successful file deletion."""
        executor = FileOperationExecutor(str(temp_dir))

        # Create file to delete
        target = temp_dir / "delete_me.txt"
        target.write_text("Delete this")

        operations = FileOperationResponse(
            summary="Delete file",
            files=[
                FileCommand(
                    operation=FileOperation.DELETE,
                    path="delete_me.txt",
                    description="Delete test",
                )
            ],
        )

        result = executor.execute_operations(operations)

        assert len(result.files_deleted) == 1
        assert "delete_me.txt" in result.files_deleted
        assert not target.exists()

    @pytest.mark.unit
    def test_delete_nonexistent_file(self, temp_dir):
        """Test deleting file that doesn't exist."""
        executor = FileOperationExecutor(str(temp_dir))

        operations = FileOperationResponse(
            summary="Delete file",
            files=[
                FileCommand(
                    operation=FileOperation.DELETE,
                    path="nonexistent.txt",
                    description="Delete test",
                )
            ],
        )

        result = executor.execute_operations(operations)

        # Should not error - deletion is idempotent
        assert len(result.errors) == 0
        assert len(result.files_deleted) == 0

    @pytest.mark.unit
    def test_multiple_operations(self, temp_dir):
        """Test executing multiple operations."""
        executor = FileOperationExecutor(str(temp_dir))

        # Prepare
        (temp_dir / "existing.txt").write_text("Existing")
        (temp_dir / "to_delete.txt").write_text("Delete me")

        operations = FileOperationResponse(
            summary="Multiple operations",
            files=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="new_file.py",
                    content="print('new')",
                    description="Create new",
                ),
                FileCommand(
                    operation=FileOperation.UPDATE,
                    path="existing.txt",
                    content="Updated",
                    description="Update existing",
                ),
                FileCommand(
                    operation=FileOperation.DELETE,
                    path="to_delete.txt",
                    description="Delete file",
                ),
            ],
        )

        result = executor.execute_operations(operations)

        assert len(result.files_created) == 1
        assert len(result.files_updated) == 1
        assert len(result.files_deleted) == 1
        assert len(result.operations_performed) == 3
        assert len(result.errors) == 0

    @pytest.mark.unit
    def test_unsafe_path_rejection(self, temp_dir):
        """Test that unsafe paths are rejected."""
        from pydantic import ValidationError

        # Unsafe paths should be rejected at the Pydantic validation level
        with pytest.raises(ValidationError) as exc_info:
            FileCommand(
                operation=FileOperation.CREATE,
                path="../../../etc/passwd",
                content="malicious",
                description="Bad operation",
            )

        assert "Invalid path" in str(exc_info.value)

    @pytest.mark.unit
    def test_permission_error_handling(self, temp_dir, monkeypatch):
        """Test handling permission errors."""
        executor = FileOperationExecutor(str(temp_dir))

        # Mock to raise permission error
        def mock_write_text(*args):
            raise PermissionError("No permission")

        monkeypatch.setattr(Path, "write_text", mock_write_text)

        operations = FileOperationResponse(
            summary="Create file",
            files=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="test.txt",
                    content="content",
                    description="Test",
                )
            ],
        )

        result = executor.execute_operations(operations)

        assert len(result.errors) == 1
        assert "No permission" in result.errors[0]

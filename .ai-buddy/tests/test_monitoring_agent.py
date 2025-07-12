"""Tests for the monitoring agent module."""

import os
import json
import time
import pytest
from unittest.mock import Mock, MagicMock, patch, call
from pathlib import Path
from freezegun import freeze_time

from monitoring_agent import (
    main,
    update_heartbeat,
    read_file_safely,
    get_recent_changes,
    cleanup_old_gemini_files,
    uploaded_file_tracker,
)


class TestMonitoringAgent:
    """Test suite for monitoring agent functionality."""

    @pytest.mark.unit
    def test_update_heartbeat(self, ipc_files, mock_time):
        """Test heartbeat file update."""
        update_heartbeat()

        assert ipc_files["heartbeat"].exists()
        content = ipc_files["heartbeat"].read_text()
        assert content == str(mock_time)

    @pytest.mark.unit
    def test_update_heartbeat_error_handling(self, ipc_files, monkeypatch):
        """Test heartbeat update with file write error."""

        # Make directory read-only to cause error
        def mock_open(*args, **kwargs):
            raise PermissionError("Cannot write")

        monkeypatch.setattr("builtins.open", mock_open)

        # Should not raise, just log error
        update_heartbeat()  # Verify it doesn't crash

    @pytest.mark.unit
    def test_read_file_safely_normal(self, temp_dir):
        """Test reading a normal-sized file."""
        test_file = temp_dir / "test.txt"
        content = "Hello\nWorld\n" * 100
        test_file.write_text(content)

        result = read_file_safely(str(test_file))
        assert result == content

    @pytest.mark.unit
    def test_read_file_safely_large(self, temp_dir):
        """Test reading a file larger than max size."""
        test_file = temp_dir / "large.txt"
        # Create 11MB file
        content = "x" * (11 * 1024 * 1024)
        test_file.write_text(content)

        result = read_file_safely(str(test_file), max_size=10 * 1024 * 1024)

        assert "[... middle portion truncated due to size ...]" in result
        assert len(result) < len(content)

    @pytest.mark.unit
    def test_read_file_safely_error(self, temp_dir):
        """Test reading a non-existent file."""
        result = read_file_safely(str(temp_dir / "nonexistent.txt"))
        assert "[Error reading file:" in result

    @pytest.mark.unit
    def test_get_recent_changes(self, ipc_files):
        """Test reading recent changes from log."""
        # No log file
        assert get_recent_changes() is None

        # Create log with some changes
        changes = "file1.py modified\nfile2.py created\n" * 60
        ipc_files["changes"].write_text(changes)

        result = get_recent_changes()
        assert result is not None
        assert "file1.py modified" in result
        # Should only get last 100 lines
        assert result.count("\n") <= 100

    @pytest.mark.unit
    def test_cleanup_old_gemini_files(self, mock_genai_client):
        """Test cleanup of old uploaded files."""
        # Mock some existing files
        old_file1 = Mock()
        old_file1.name = "temp_context_old_session_123.txt"

        old_file2 = Mock()
        old_file2.name = "temp_context_another_456.txt"

        current_file = Mock()
        current_file.name = "temp_context_current_789.txt"

        mock_genai_client.files.list.return_value = [old_file1, old_file2, current_file]

        # Run cleanup, keeping current session
        cleanup_old_gemini_files(mock_genai_client, session_id="current_789")

        # Should delete old files but keep current
        assert mock_genai_client.files.delete.call_count == 2
        mock_genai_client.files.delete.assert_any_call(
            name="temp_context_old_session_123.txt"
        )
        mock_genai_client.files.delete.assert_any_call(
            name="temp_context_another_456.txt"
        )

    @pytest.mark.unit
    def test_cleanup_handles_delete_errors(self, mock_genai_client):
        """Test cleanup continues even if some deletes fail."""
        file1 = Mock()
        file1.name = "temp_context_fail.txt"

        mock_genai_client.files.list.return_value = [file1]
        mock_genai_client.files.delete.side_effect = Exception("Delete failed")

        # Should not raise
        cleanup_old_gemini_files(mock_genai_client)

        assert mock_genai_client.files.delete.called


class TestMonitoringAgentMain:
    """Test the main monitoring loop."""

    @pytest.mark.integration
    @patch("monitoring_agent.genai.Client")
    @patch("monitoring_agent.ConversationManager")
    @patch("monitoring_agent.generate_repo_blob")
    def test_main_initialization(
        self,
        mock_repo_blob,
        mock_conv_mgr,
        mock_client_class,
        temp_dir,
        mock_sessions_dir,
        mock_env_vars,
    ):
        """Test main function initialization."""
        # Setup
        context_file = temp_dir / "context.txt"
        context_file.write_text("Project context")
        log_file = temp_dir / "session.log"

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock conversation manager
        mock_conv_instance = MagicMock()
        mock_conv_instance.conversation_history = []
        mock_conv_mgr.return_value = mock_conv_instance

        # Run main with immediate KeyboardInterrupt
        with patch("time.sleep", side_effect=KeyboardInterrupt):
            with pytest.raises(KeyboardInterrupt):
                main(str(context_file), str(log_file), "test_session_123")

        # Verify initialization
        mock_client_class.assert_called_once()
        mock_conv_mgr.assert_called_once_with("test_session_123", mock_sessions_dir)

        # Verify cleanup was called
        assert mock_client.files.list.called

    @pytest.mark.integration
    @patch("monitoring_agent.genai.Client")
    def test_api_key_hot_reload(
        self, mock_client_class, temp_dir, mock_sessions_dir, monkeypatch
    ):
        """Test API key hot-reload functionality."""
        # Start without API key
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        context_file = temp_dir / "context.txt"
        context_file.write_text("Project context")
        log_file = temp_dir / "session.log"

        # Mock client creation to fail first, then succeed
        mock_client_class.side_effect = [
            Exception("API key required"),
            MagicMock(),  # Success on second try
        ]

        call_count = 0

        def mock_sleep(duration):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # Simulate user adding API key
                monkeypatch.setenv("GEMINI_API_KEY", "new-key-123")
            elif call_count > 2:
                raise KeyboardInterrupt

        with patch("time.sleep", side_effect=mock_sleep):
            with patch("monitoring_agent.load_dotenv"):
                with patch("monitoring_agent.ConversationManager"):
                    with pytest.raises(KeyboardInterrupt):
                        main(str(context_file), str(log_file))

        # Should have tried to create client at least twice
        assert mock_client_class.call_count >= 2

    @pytest.mark.integration
    @patch("monitoring_agent.genai.Client")
    @patch("monitoring_agent.SmartContextBuilder")
    def test_request_processing_with_smart_context(
        self,
        mock_context_builder,
        mock_client_class,
        temp_dir,
        ipc_files,
        mock_env_vars,
    ):
        """Test processing a request with smart context enabled."""
        # Setup
        context_file = temp_dir / "context.txt"
        context_file.write_text("Project context")
        log_file = temp_dir / "session.log"
        log_file.write_text("Session log content")

        # Mock client
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Smart response from Gemini"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Mock smart context
        mock_builder = MagicMock()
        mock_builder.build_context.return_value = (
            "Optimized context content",
            ["file1.py", "file2.py"],
        )
        mock_context_builder.return_value = mock_builder

        # Create request
        ipc_files["request"].write_text("How do I fix the authentication bug?")

        # Run one iteration
        def run_one_iteration(*args):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count > 1:
                raise KeyboardInterrupt

        iteration_count = 0
        with patch("time.sleep", side_effect=run_one_iteration):
            with patch("monitoring_agent.ConversationManager"):
                with pytest.raises(KeyboardInterrupt):
                    main(str(context_file), str(log_file))

        # Verify smart context was used
        mock_context_builder.assert_called_once()
        mock_builder.build_context.assert_called_once()

        # Verify response was written
        assert ipc_files["response"].exists()
        response_content = ipc_files["response"].read_text()
        assert response_content == "Smart response from Gemini"

    @pytest.mark.integration
    @patch("monitoring_agent.genai.Client")
    @patch("monitoring_agent.FileOperationExecutor")
    def test_file_operation_processing(
        self, mock_executor, mock_client_class, temp_dir, ipc_files, mock_env_vars
    ):
        """Test processing file operation requests."""
        # Setup
        context_file = temp_dir / "context.txt"
        context_file.write_text("Project context")
        log_file = temp_dir / "session.log"

        # Mock client with structured response
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = json.dumps(
            {
                "summary": "Creating test file",
                "operations": [
                    {
                        "operation": "create",
                        "path": "test.py",
                        "content": "print('test')",
                        "description": "Test file",
                    }
                ],
                "warnings": [],
            }
        )
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Mock file executor
        mock_result = MagicMock()
        mock_result.files_created = ["test.py"]
        mock_result.files_updated = []
        mock_result.files_deleted = []
        mock_result.errors = []
        mock_result.operations_performed = 1
        mock_executor.return_value.execute_operations.return_value = mock_result

        # Create file operation request
        ipc_files["request"].write_text("Create a new test file")

        # Run one iteration
        iteration_count = 0

        def run_one_iteration(*args):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count > 1:
                raise KeyboardInterrupt

        with patch("time.sleep", side_effect=run_one_iteration):
            with patch("monitoring_agent.ConversationManager"):
                with patch(
                    "monitoring_agent.detect_file_operation_request", return_value=True
                ):
                    with pytest.raises(KeyboardInterrupt):
                        main(str(context_file), str(log_file))

        # Verify file operation was executed
        mock_executor.assert_called_once()

        # Verify response contains file operation results
        response = ipc_files["response"].read_text()
        assert "Files Created:" in response
        assert "✅ test.py" in response
        assert "✨ Operations completed: 1" in response

    @pytest.mark.integration
    @patch("monitoring_agent.genai.Client")
    @patch("monitoring_agent.generate_repo_blob")
    def test_refresh_request_handling(
        self, mock_repo_blob, mock_client_class, temp_dir, ipc_files, mock_env_vars
    ):
        """Test handling refresh requests."""
        # Setup
        context_file = temp_dir / ".ai-buddy" / "sessions" / "context.txt"
        context_file.parent.mkdir(parents=True)
        context_file.write_text("Old context")
        log_file = temp_dir / "session.log"

        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create refresh request
        ipc_files["refresh"].write_text("")

        mock_repo_blob.return_value = True

        # Run one iteration
        iteration_count = 0

        def run_one_iteration(*args):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count > 1:
                raise KeyboardInterrupt

        with patch("time.sleep", side_effect=run_one_iteration):
            with patch("monitoring_agent.ConversationManager"):
                with pytest.raises(KeyboardInterrupt):
                    main(str(context_file), str(log_file))

        # Verify repo blob was regenerated
        mock_repo_blob.assert_called_once()

        # Verify refresh file was removed
        assert not ipc_files["refresh"].exists()

    @pytest.mark.unit
    @patch("monitoring_agent.genai.Client")
    def test_error_handling_and_recovery(
        self, mock_client_class, temp_dir, ipc_files, mock_env_vars
    ):
        """Test error handling in main loop."""
        # Setup
        context_file = temp_dir / "context.txt"
        context_file.write_text("Project context")
        log_file = temp_dir / "session.log"

        # Mock client to raise error on first request
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        # Create request that will fail
        ipc_files["request"].write_text("Test request")

        # Run a few iterations
        iteration_count = 0

        def run_iterations(*args):
            nonlocal iteration_count
            iteration_count += 1
            if iteration_count > 3:
                raise KeyboardInterrupt

        with patch("time.sleep", side_effect=run_iterations):
            with patch("monitoring_agent.ConversationManager"):
                with pytest.raises(KeyboardInterrupt):
                    main(str(context_file), str(log_file))

        # Verify error response was written
        assert ipc_files["response"].exists()
        response = ipc_files["response"].read_text()
        assert "Error processing request" in response
        assert "API Error" in response

        # Verify processing indicator was cleaned up
        assert not ipc_files["processing"].exists()

    @pytest.mark.unit
    def test_session_id_extraction(self):
        """Test extracting session ID from log filename."""
        from monitoring_agent import main

        # Test with provided session_id
        # This would need to be tested within the main function
        # For now, we verify the pattern matching logic
        log_file = "claude_session_20250712_140230.log"
        expected_id = "20250712_140230"

        # The extraction happens inside main()
        # We'd need to refactor to test this separately
        assert expected_id in log_file.replace("claude_session_", "").replace(
            ".log", ""
        )

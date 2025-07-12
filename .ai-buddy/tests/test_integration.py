"""Integration tests for AI Buddy system."""

import os
import json
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import threading

from monitoring_agent import main as monitor_main
from conversation_manager import ConversationManager
from file_operations import FileOperationResponse, FileCommand, FileOperation
from session_manager import SessionManager
from smart_context import SmartContextBuilder


class TestSystemIntegration:
    """Test the integration of multiple AI Buddy components."""

    @pytest.mark.integration
    def test_full_conversation_flow(self, temp_dir, mock_genai_client):
        """Test a complete conversation flow from request to response."""
        # Setup
        sessions_dir = temp_dir / "sessions"
        sessions_dir.mkdir()

        # Create session
        session_mgr = SessionManager(str(sessions_dir))
        session_id = session_mgr.create_session(str(temp_dir))

        # Initialize conversation manager
        conv_mgr = ConversationManager(session_id, str(sessions_dir))

        # Simulate user request
        request_file = sessions_dir / "buddy_request.tmp"
        request_file.write_text("How do I implement authentication?")

        # Mock monitoring agent processing
        mock_response = "To implement authentication, you need to..."
        mock_genai_client.models.generate_content.return_value.text = mock_response

        # Process request (simplified)
        response_file = sessions_dir / "buddy_response.tmp"
        response_file.write_text(mock_response)

        # Add to conversation
        conv_mgr.add_exchange(request_file.read_text(), response_file.read_text())

        # Verify
        assert len(conv_mgr.conversation_history) == 1
        assert (
            conv_mgr.conversation_history[0]["user"]
            == "How do I implement authentication?"
        )
        assert conv_mgr.conversation_history[0]["assistant"] == mock_response

        # End session
        session_mgr.end_session(session_id)
        assert session_mgr.get_session(session_id).status == "completed"

    @pytest.mark.integration
    def test_file_operation_flow(self, temp_dir, mock_genai_client):
        """Test file operation request processing."""
        # Setup project
        project_root = temp_dir / "project"
        project_root.mkdir()

        # Mock Gemini response with file operations
        file_ops = FileOperationResponse(
            summary="Creating authentication module",
            operations=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="auth.py",
                    content="class Auth:\n    pass",
                    description="Authentication module",
                )
            ],
        )

        mock_genai_client.models.generate_content.return_value.text = (
            file_ops.model_dump_json()
        )

        # Process file operations
        from file_operations import FileOperationExecutor

        executor = FileOperationExecutor(str(project_root))
        result = executor.execute_operations(file_ops)

        # Verify
        assert len(result.files_created) == 1
        assert "auth.py" in result.files_created
        assert (project_root / "auth.py").exists()
        assert (project_root / "auth.py").read_text() == "class Auth:\n    pass"

    @pytest.mark.integration
    def test_smart_context_integration(self, mock_project_root):
        """Test smart context building with real files."""
        # Create varied project files
        files = {
            "auth.py": "def authenticate(): pass",
            "test_auth.py": "def test_auth(): pass",
            "utils.py": "def helper(): pass",
            "config.json": '{"auth": true}',
            "README.md": "# Project\nAuthentication system",
        }

        for name, content in files.items():
            (mock_project_root / name).write_text(content)

        # Build context for auth query
        builder = SmartContextBuilder(str(mock_project_root))
        context, included_files = builder.build_context(
            "Fix the authentication bug",
            session_log="Error in auth",
            conversation_history="Previous discussion about auth",
        )

        # Verify relevant files were included
        assert any("auth.py" in f for f in included_files)
        assert "def authenticate():" in context
        assert "### RELEVANT PROJECT FILES ###" in context

    @pytest.mark.integration
    @pytest.mark.slow
    def test_monitoring_agent_lifecycle(self, temp_dir, mock_genai_client, monkeypatch):
        """Test monitoring agent startup and shutdown."""
        # Setup
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("POLLING_INTERVAL", "0.1")

        sessions_dir = temp_dir / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setenv("SESSIONS_DIR", str(sessions_dir))

        context_file = temp_dir / "context.txt"
        context_file.write_text("Project context")
        log_file = temp_dir / "session.log"

        # Start monitoring in thread
        stop_event = threading.Event()

        def run_monitor():
            try:
                with patch("time.sleep") as mock_sleep:
                    # Make sleep check stop event
                    def sleep_with_stop(duration):
                        if stop_event.is_set():
                            raise KeyboardInterrupt
                        time.sleep(min(duration, 0.01))

                    mock_sleep.side_effect = sleep_with_stop

                    with patch(
                        "monitoring_agent.genai.Client", return_value=mock_genai_client
                    ):
                        main(str(context_file), str(log_file))
            except KeyboardInterrupt:
                pass

        monitor_thread = threading.Thread(target=run_monitor)
        monitor_thread.start()

        # Wait for startup
        time.sleep(0.1)

        # Verify heartbeat
        heartbeat_file = sessions_dir / "buddy_heartbeat.tmp"
        assert heartbeat_file.exists()

        # Stop monitor
        stop_event.set()
        monitor_thread.join(timeout=2)

        # Verify cleanup
        assert not (sessions_dir / "buddy_processing.tmp").exists()

    @pytest.mark.integration
    def test_session_persistence_across_restarts(self, temp_dir):
        """Test that sessions persist across system restarts."""
        sessions_dir = temp_dir / "sessions"
        sessions_dir.mkdir()

        # First run - create sessions
        mgr1 = SessionManager(str(sessions_dir))
        session1 = mgr1.create_session("/project1")
        session2 = mgr1.create_session("/project2")

        # Add conversation to one session
        conv1 = ConversationManager(session1, str(sessions_dir))
        conv1.add_exchange("Question 1", "Answer 1")

        # End one session
        mgr1.end_session(session1)

        # Simulate restart - new instances
        mgr2 = SessionManager(str(sessions_dir))

        # Verify sessions persist
        assert len(mgr2.sessions) == 2
        assert mgr2.get_session(session1).status == "completed"
        assert mgr2.get_session(session2).status == "active"

        # Verify conversation persists
        conv2 = ConversationManager(session1, str(sessions_dir))
        assert len(conv2.conversation_history) == 1
        assert conv2.conversation_history[0]["user"] == "Question 1"

    @pytest.mark.integration
    def test_error_recovery(self, temp_dir, mock_genai_client):
        """Test system recovery from various errors."""
        sessions_dir = temp_dir / "sessions"
        sessions_dir.mkdir()

        # Test 1: API error recovery
        mock_genai_client.models.generate_content.side_effect = Exception("API Error")

        request_file = sessions_dir / "buddy_request.tmp"
        request_file.write_text("Test request")

        # System should write error response
        # (In real system, monitoring agent would handle this)
        response_file = sessions_dir / "buddy_response.tmp"
        response_file.write_text("⚠️ Error processing request: API Error")

        assert "Error" in response_file.read_text()

        # Test 2: Corrupted conversation file recovery
        conv_file = sessions_dir / "conversation_test.json"
        conv_file.write_text("{invalid json")

        # Should initialize with empty history
        conv_mgr = ConversationManager("test", str(sessions_dir))
        assert conv_mgr.conversation_history == []

        # Test 3: File operation error recovery
        from file_operations import FileOperationExecutor

        executor = FileOperationExecutor("/invalid/path")

        ops = FileOperationResponse(
            summary="Test",
            operations=[
                FileCommand(
                    operation=FileOperation.CREATE,
                    path="test.txt",
                    content="test",
                    description="test",
                )
            ],
        )

        result = executor.execute_operations(ops)
        assert len(result.errors) > 0

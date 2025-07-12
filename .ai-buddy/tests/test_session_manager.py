"""Tests for the session manager module."""

import json
import os
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from freezegun import freeze_time

from session_manager import SessionManager


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.mark.unit
    def test_initialization_no_index(self, mock_sessions_dir):
        """Test initializing SessionManager without existing index."""
        manager = SessionManager(str(mock_sessions_dir))

        assert manager.sessions_dir == str(mock_sessions_dir)
        assert manager.index_file == os.path.join(
            str(mock_sessions_dir), "session_index.json"
        )
        assert manager.sessions_index == {"sessions": []}

    @pytest.mark.unit
    def test_initialization_with_index(self, mock_sessions_dir):
        """Test initializing SessionManager with existing index."""
        # Create existing index
        index_data = {
            "sessions": [
                {
                    "id": "session1",
                    "created": "2025-01-12T10:00:00",
                    "project_root": "/project1",
                    "status": "active",
                },
                {
                    "id": "session2",
                    "created": "2025-01-12T11:00:00",
                    "project_root": "/project2",
                    "status": "active",
                },
            ]
        }

        index_file = mock_sessions_dir / "session_index.json"
        index_file.write_text(json.dumps(index_data, indent=2))

        manager = SessionManager(str(mock_sessions_dir))

        assert len(manager.sessions_index["sessions"]) == 2
        assert manager.sessions_index["sessions"][0]["id"] == "session1"
        assert manager.sessions_index["sessions"][0]["status"] == "active"
        assert manager.sessions_index["sessions"][1]["project_root"] == "/project2"

    @pytest.mark.unit
    def test_load_index_corrupted(self, mock_sessions_dir):
        """Test loading corrupted index file."""
        index_file = mock_sessions_dir / "session_index.json"
        index_file.write_text("{invalid json")

        manager = SessionManager(str(mock_sessions_dir))

        # Should initialize with empty sessions
        assert manager.sessions_index == {"sessions": []}

    @pytest.mark.unit
    def test_create_session(self, mock_sessions_dir):
        """Test creating a new session."""
        manager = SessionManager(str(mock_sessions_dir))

        session_id = "test_session_123"
        session = manager.create_session(session_id, "/home/user/myproject")

        # Verify session data
        assert session["id"] == session_id
        assert session["project_root"] == "/home/user/myproject"
        assert session["status"] == "active"
        assert "created" in session
        assert "context_file" in session
        assert "log_file" in session
        assert "conversation_file" in session
        assert "last_accessed" in session

        # Verify session was added to index
        assert len(manager.sessions_index["sessions"]) == 1
        assert manager.sessions_index["sessions"][0]["id"] == session_id

        # Verify index was saved
        index_file = Path(mock_sessions_dir) / "session_index.json"
        assert index_file.exists()

    @pytest.mark.unit
    def test_get_session_exists(self, mock_sessions_dir):
        """Test getting an existing session."""
        manager = SessionManager(str(mock_sessions_dir))

        # Create a session
        session_id = "test_session"
        manager.create_session(session_id, "/test/project")

        # Get the session
        session = manager.get_session(session_id)

        assert session is not None
        assert session["id"] == session_id
        assert session["project_root"] == "/test/project"

    @pytest.mark.unit
    def test_get_session_not_exists(self, mock_sessions_dir):
        """Test getting a non-existent session."""
        manager = SessionManager(str(mock_sessions_dir))

        session = manager.get_session("nonexistent_session")

        assert session is None

    @pytest.mark.unit
    def test_update_session_access(self, mock_sessions_dir):
        """Test updating session access time."""
        manager = SessionManager(str(mock_sessions_dir))

        # Create a session
        with freeze_time("2025-01-12 10:00:00"):
            session_id = "test_session"
            manager.create_session(session_id, "/test/project")

        # Update access time later
        with freeze_time("2025-01-12 11:00:00"):
            manager.update_session_access(session_id)

        # Verify last_accessed was updated
        session = manager.get_session(session_id)
        assert session["last_accessed"] == "2025-01-12T11:00:00"

    @pytest.mark.unit
    def test_update_session_access_nonexistent(self, mock_sessions_dir):
        """Test updating access time for non-existent session."""
        manager = SessionManager(str(mock_sessions_dir))

        # Should not error when updating non-existent session
        manager.update_session_access("nonexistent")

        # Index should remain empty
        assert len(manager.sessions_index["sessions"]) == 0

    @pytest.mark.unit
    def test_list_recent_sessions_empty(self, mock_sessions_dir):
        """Test listing sessions when none exist."""
        manager = SessionManager(str(mock_sessions_dir))

        sessions = manager.list_recent_sessions()

        assert sessions == []

    @pytest.mark.unit
    def test_list_recent_sessions_multiple(self, mock_sessions_dir):
        """Test listing multiple sessions."""
        manager = SessionManager(str(mock_sessions_dir))

        # Create sessions with different times
        with freeze_time("2025-01-12 09:00:00"):
            manager.create_session("session1", "/project1")

        with freeze_time("2025-01-12 10:00:00"):
            manager.create_session("session2", "/project2")

        with freeze_time("2025-01-12 08:00:00"):
            manager.create_session("session3", "/project3")

        sessions = manager.list_recent_sessions()

        # Should be sorted by last_accessed (newest first)
        assert len(sessions) == 3
        assert sessions[0]["id"] == "session2"  # 10:00
        assert sessions[1]["id"] == "session1"  # 09:00
        assert sessions[2]["id"] == "session3"  # 08:00

    @pytest.mark.unit
    def test_list_recent_sessions_with_limit(self, mock_sessions_dir):
        """Test listing sessions with limit."""
        manager = SessionManager(str(mock_sessions_dir))

        # Create 5 sessions
        for i in range(5):
            manager.create_session(f"session{i}", f"/project{i}")

        # List with limit
        sessions = manager.list_recent_sessions(limit=3)

        assert len(sessions) == 3

    @pytest.mark.unit
    def test_format_session_list_empty(self, mock_sessions_dir):
        """Test formatting empty session list."""
        manager = SessionManager(str(mock_sessions_dir))

        formatted = manager.format_session_list()

        assert formatted == "No previous sessions found."

    @pytest.mark.unit
    def test_format_session_list_with_sessions(self, mock_sessions_dir):
        """Test formatting session list with sessions."""
        manager = SessionManager(str(mock_sessions_dir))

        # Create test sessions
        with freeze_time("2025-01-12 10:30:45"):
            manager.create_session("session1", "/home/user/myproject")

        formatted = manager.format_session_list()

        # Should contain session info
        assert "Available Sessions:" in formatted
        assert "session1" in formatted
        assert "2025-01-12 10:30" in formatted  # Formatted timestamp
        assert "myproject" in formatted  # Project basename
        assert "Has conversation:" in formatted

    @pytest.mark.unit
    def test_save_index_error_handling(self, mock_sessions_dir, monkeypatch):
        """Test error handling when saving index fails."""
        manager = SessionManager(str(mock_sessions_dir))

        # Make save fail
        def mock_open(*args, **kwargs):
            raise PermissionError("Cannot write")

        monkeypatch.setattr("builtins.open", mock_open)

        # Should not raise when creating session (only prints warning)
        session = manager.create_session("test", "/test")

        # Session should still be created in memory
        assert session["id"] == "test"
        assert len(manager.sessions_index["sessions"]) == 1

    @pytest.mark.unit
    def test_concurrent_session_creation(self, mock_sessions_dir):
        """Test creating sessions with same timestamp."""
        manager = SessionManager(str(mock_sessions_dir))

        with freeze_time("2025-01-12 10:00:00"):
            session1 = manager.create_session("session1", "/project1")
            session2 = manager.create_session("session2", "/project2")

        # Both should be created successfully
        assert session1["id"] == "session1"
        assert session2["id"] == "session2"
        assert len(manager.sessions_index["sessions"]) == 2

    @pytest.mark.unit
    def test_session_persistence(self, mock_sessions_dir):
        """Test that sessions persist across manager instances."""
        # First manager
        manager1 = SessionManager(str(mock_sessions_dir))
        session_id = "persistent_session"
        manager1.create_session(session_id, "/test/project")

        # Second manager
        manager2 = SessionManager(str(mock_sessions_dir))

        # Should load previous session
        session = manager2.get_session(session_id)
        assert session is not None
        assert session["id"] == session_id
        assert session["project_root"] == "/test/project"

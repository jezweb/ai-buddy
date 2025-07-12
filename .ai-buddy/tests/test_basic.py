"""Basic smoke tests to verify the test framework."""

import pytest


class TestBasic:
    """Basic tests to verify the test framework is working."""

    @pytest.mark.unit
    def test_simple_assertion(self):
        """Test that basic assertions work."""
        assert True
        assert 1 + 1 == 2
        assert "hello" in "hello world"

    @pytest.mark.unit
    def test_imports_work(self):
        """Test that we can import our modules."""
        from conversation_manager import ConversationManager
        from session_manager import SessionManager
        from file_operations import FileOperation

        # Verify enums work
        assert FileOperation.CREATE == "create"
        assert FileOperation.UPDATE == "update"
        assert FileOperation.DELETE == "delete"

    @pytest.mark.unit
    def test_temp_dir_fixture(self, temp_dir):
        """Test that temp_dir fixture works."""
        assert temp_dir.exists()
        assert temp_dir.is_dir()

        # Can create files in temp dir
        test_file = temp_dir / "test.txt"
        test_file.write_text("test content")
        assert test_file.exists()
        assert test_file.read_text() == "test content"

    @pytest.mark.unit
    def test_mock_genai_client(self, mock_genai_client):
        """Test that mock genai client works."""
        # Should be able to call methods
        response = mock_genai_client.models.generate_content("test prompt")
        assert response.text == "This is a test response from Gemini."

        # Should be able to mock file operations
        uploaded_file = mock_genai_client.files.upload("test_file.txt")
        assert uploaded_file.name == "test_file_123"

    @pytest.mark.integration
    def test_session_creation_basic(self, mock_sessions_dir):
        """Test basic session creation integration."""
        from session_manager import SessionManager

        manager = SessionManager(str(mock_sessions_dir))
        session = manager.create_session("test_session", "/test/project")

        assert session["id"] == "test_session"
        assert session["project_root"] == "/test/project"
        assert session["status"] == "active"

    @pytest.mark.integration
    def test_conversation_basic(self, mock_sessions_dir):
        """Test basic conversation functionality."""
        from conversation_manager import ConversationManager

        manager = ConversationManager("test_session", str(mock_sessions_dir))
        manager.add_exchange("Test question", "Test answer")

        assert len(manager.conversation_history) == 1
        assert manager.conversation_history[0]["question"] == "Test question"
        assert manager.conversation_history[0]["response"] == "Test answer"

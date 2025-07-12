"""Tests for the conversation manager module."""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from conversation_manager import ConversationManager


class TestConversationManager:
    """Test suite for conversation management functionality."""

    @pytest.mark.unit
    def test_initialization_no_existing_history(self, mock_sessions_dir):
        """Test initializing conversation manager without existing history."""
        session_id = "test_session_123"

        manager = ConversationManager(session_id, str(mock_sessions_dir))

        assert manager.session_id == session_id
        assert manager.sessions_dir == str(mock_sessions_dir)
        assert manager.conversation_history == []
        assert manager.conversation_file == str(
            mock_sessions_dir / f"conversation_{session_id}.json"
        )

    @pytest.mark.unit
    def test_initialization_with_existing_history(
        self, mock_sessions_dir, sample_conversation
    ):
        """Test initializing conversation manager with existing history."""
        session_id = "test_session_123"

        # Create existing conversation file with proper structure
        conv_file = mock_sessions_dir / f"conversation_{session_id}.json"
        data = {"session_id": session_id, "conversations": sample_conversation}
        conv_file.write_text(json.dumps(data, indent=2))

        manager = ConversationManager(session_id, str(mock_sessions_dir))

        assert len(manager.conversation_history) == 2
        assert (
            manager.conversation_history[0]["question"]
            == "How do I implement error handling?"
        )

    @pytest.mark.unit
    def test_load_conversation_corrupted_file(self, mock_sessions_dir, capsys):
        """Test loading conversation from corrupted JSON file."""
        session_id = "test_session_123"

        # Create corrupted JSON file
        conv_file = mock_sessions_dir / f"conversation_{session_id}.json"
        conv_file.write_text("{invalid json content")

        manager = ConversationManager(session_id, str(mock_sessions_dir))

        # Should initialize with empty history
        assert manager.conversation_history == []

        # Should print warning
        captured = capsys.readouterr()
        assert "Could not load conversation history" in captured.out

    @pytest.mark.unit
    def test_add_exchange(self, mock_sessions_dir):
        """Test adding a new exchange to conversation."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        user_msg = "What is Python?"
        assistant_msg = "Python is a high-level programming language."

        manager.add_exchange(user_msg, assistant_msg)

        assert len(manager.conversation_history) == 1
        exchange = manager.conversation_history[0]

        assert exchange["question"] == user_msg
        assert exchange["response"] == assistant_msg
        assert "timestamp" in exchange

        # Verify timestamp format
        timestamp = datetime.fromisoformat(exchange["timestamp"])
        assert isinstance(timestamp, datetime)

    @pytest.mark.unit
    def test_save_conversation(self, mock_sessions_dir):
        """Test saving conversation to file."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Add some exchanges
        manager.add_exchange("Question 1", "Answer 1")
        manager.add_exchange("Question 2", "Answer 2")

        # Verify file was created and contains data
        conv_file = Path(manager.conversation_file)
        assert conv_file.exists()

        # Load and verify content
        saved_data = json.loads(conv_file.read_text())
        assert len(saved_data["conversations"]) == 2
        assert saved_data["conversations"][0]["question"] == "Question 1"
        assert saved_data["conversations"][1]["response"] == "Answer 2"

    @pytest.mark.unit
    def test_save_conversation_error_handling(self, mock_sessions_dir, monkeypatch):
        """Test error handling when saving conversation fails."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Make the save operation fail
        def mock_open_error(*args, **kwargs):
            raise PermissionError("Cannot write file")

        with patch("builtins.open", mock_open_error):
            # Should not raise exception
            manager.add_exchange("Test", "Response")

        # Exchange should still be in memory
        assert len(manager.conversation_history) == 1

    @pytest.mark.unit
    def test_get_recent_context_empty(self, mock_sessions_dir):
        """Test getting recent context with no history."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        context = manager.get_recent_context()

        assert context == "No previous conversation in this session."

    @pytest.mark.unit
    def test_get_recent_context_few_exchanges(self, mock_sessions_dir):
        """Test getting recent context with few exchanges."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Add a few exchanges
        manager.add_exchange("Q1", "A1")
        manager.add_exchange("Q2", "A2")

        context = manager.get_recent_context(num_exchanges=5)

        # Should include all exchanges
        assert "Q: Q1" in context
        assert "A: A1" in context
        assert "Q: Q2" in context
        assert "A: A2" in context
        assert context.count("Exchange") == 2  # Two exchanges

    @pytest.mark.unit
    def test_get_recent_context_many_exchanges(self, mock_sessions_dir):
        """Test getting recent context with more exchanges than limit."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Add many exchanges
        for i in range(10):
            manager.add_exchange(f"Question {i}", f"Answer {i}")

        context = manager.get_recent_context(num_exchanges=3)

        # Should only include last 3 exchanges
        assert "Question 7" in context
        assert "Question 8" in context
        assert "Question 9" in context

        # Should not include earlier exchanges
        assert "Question 0" not in context
        assert "Question 6" not in context

        # Should have exactly 3 exchanges
        assert context.count("Exchange") == 3

    @pytest.mark.unit
    def test_get_recent_context_with_long_messages(self, mock_sessions_dir):
        """Test getting recent context with long messages."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Add exchange with very long messages
        long_question = "X" * 1000
        long_answer = "Y" * 1000

        manager.add_exchange(long_question, long_answer)

        context = manager.get_recent_context()

        # Verify truncation
        assert "..." in context
        assert len(context) < len(long_question) + len(long_answer)

        # Should still have structure
        assert "Q:" in context
        assert "A:" in context

    @pytest.mark.unit
    def test_conversation_persistence_across_instances(self, mock_sessions_dir):
        """Test that conversation persists across manager instances."""
        session_id = "persistent_session"

        # First manager instance
        manager1 = ConversationManager(session_id, str(mock_sessions_dir))
        manager1.add_exchange("First question", "First answer")

        # Second manager instance with same session
        manager2 = ConversationManager(session_id, str(mock_sessions_dir))

        # Should load existing conversation
        assert len(manager2.conversation_history) == 1
        assert manager2.conversation_history[0]["question"] == "First question"

        # Add more to second instance
        manager2.add_exchange("Second question", "Second answer")

        # Third instance should see all exchanges
        manager3 = ConversationManager(session_id, str(mock_sessions_dir))
        assert len(manager3.conversation_history) == 2

    @pytest.mark.unit
    def test_timestamp_ordering(self, mock_sessions_dir):
        """Test that exchanges maintain chronological order."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Add exchanges with small delays
        import time

        manager.add_exchange("Q1", "A1")
        time.sleep(0.01)  # Small delay
        manager.add_exchange("Q2", "A2")
        time.sleep(0.01)
        manager.add_exchange("Q3", "A3")

        # Verify timestamps are in order
        timestamps = [
            datetime.fromisoformat(ex["timestamp"])
            for ex in manager.conversation_history
        ]

        assert timestamps[0] < timestamps[1]
        assert timestamps[1] < timestamps[2]

    @pytest.mark.unit
    def test_unicode_handling(self, mock_sessions_dir):
        """Test handling of unicode characters in conversations."""
        manager = ConversationManager("test_session", str(mock_sessions_dir))

        # Add exchanges with unicode
        unicode_q = "What does 🐍 mean?"
        unicode_a = "The 🐍 emoji represents Python! Also: café, naïve, 中文"

        manager.add_exchange(unicode_q, unicode_a)

        # Reload and verify
        manager2 = ConversationManager("test_session", str(mock_sessions_dir))
        assert manager2.conversation_history[0]["question"] == unicode_q
        assert manager2.conversation_history[0]["response"] == unicode_a

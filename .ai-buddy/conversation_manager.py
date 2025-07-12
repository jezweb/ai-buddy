# conversation_manager.py
import json
import os
from datetime import datetime
from typing import List, Dict


class ConversationManager:
    """Manages conversation history for AI Buddy sessions."""

    def __init__(self, session_id: str, sessions_dir: str):
        self.session_id = session_id
        self.sessions_dir = sessions_dir
        self.conversation_file = os.path.join(
            sessions_dir, f"conversation_{session_id}.json"
        )
        self.conversation_history: List[Dict] = []
        self._load_conversation()

    def _load_conversation(self):
        """Load existing conversation from file if it exists."""
        if os.path.exists(self.conversation_file):
            try:
                with open(self.conversation_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.conversation_history = data.get("conversations", [])
            except Exception as e:
                print(f"Warning: Could not load conversation history: {e}")
                self.conversation_history = []

    def save_conversation(self):
        """Save conversation history to file."""
        try:
            data = {
                "session_id": self.session_id,
                "last_updated": datetime.now().isoformat(),
                "conversations": self.conversation_history,
            }

            os.makedirs(self.sessions_dir, exist_ok=True)
            with open(self.conversation_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save conversation history: {e}")

    def add_exchange(self, question: str, response: str):
        """Add a question-response exchange to the history."""
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "question": question,
            "response": response,
        }
        self.conversation_history.append(exchange)
        self.save_conversation()

    def get_recent_context(self, num_exchanges: int = 3) -> str:
        """Get recent conversation context for inclusion in prompts."""
        if not self.conversation_history:
            return "No previous conversation in this session."

        recent = self.conversation_history[-num_exchanges:]
        context_parts = []

        for i, exchange in enumerate(recent, 1):
            context_parts.append(f"Exchange {i}:")
            context_parts.append(f"Q: {exchange['question']}")
            context_parts.append(
                f"A: {exchange['response'][:500]}..."
            )  # Truncate long responses
            context_parts.append("")

        return "\n".join(context_parts)

    def get_full_history(self) -> List[Dict]:
        """Get the full conversation history."""
        return self.conversation_history

    def format_history_display(self) -> str:
        """Format conversation history for display."""
        if not self.conversation_history:
            return "No conversation history yet."

        formatted = []
        for i, exchange in enumerate(self.conversation_history, 1):
            timestamp = datetime.fromisoformat(exchange["timestamp"]).strftime(
                "%H:%M:%S"
            )
            formatted.append(f"\n{timestamp} - Question {i}:")
            formatted.append(f"Q: {exchange['question']}")
            formatted.append(f"A: {exchange['response'][:200]}...")
            formatted.append("-" * 60)

        return "\n".join(formatted)

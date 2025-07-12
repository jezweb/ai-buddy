# session_manager.py
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class SessionManager:
    """Manages AI Buddy sessions for persistence and resumption."""
    
    def __init__(self, sessions_dir: str):
        self.sessions_dir = sessions_dir
        self.index_file = os.path.join(sessions_dir, "session_index.json")
        self.sessions_index: Dict = self._load_index()
    
    def _load_index(self) -> Dict:
        """Load the session index from file."""
        if os.path.exists(self.index_file):
            try:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"sessions": []}
        return {"sessions": []}
    
    def _save_index(self):
        """Save the session index to file."""
        try:
            os.makedirs(self.sessions_dir, exist_ok=True)
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions_index, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save session index: {e}")
    
    def create_session(self, session_id: str, project_root: str) -> Dict:
        """Create a new session entry."""
        session = {
            "id": session_id,
            "created": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "project_root": project_root,
            "context_file": f"project_context_{session_id}.txt",
            "log_file": f"claude_session_{session_id}.log",
            "conversation_file": f"conversation_{session_id}.json",
            "status": "active"
        }
        
        # Add to index
        self.sessions_index["sessions"].append(session)
        self._save_index()
        
        return session
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        """Get a specific session by ID."""
        for session in self.sessions_index["sessions"]:
            if session["id"] == session_id:
                return session
        return None
    
    def update_session_access(self, session_id: str):
        """Update the last accessed time for a session."""
        for session in self.sessions_index["sessions"]:
            if session["id"] == session_id:
                session["last_accessed"] = datetime.now().isoformat()
                self._save_index()
                break
    
    def list_recent_sessions(self, limit: int = 10) -> List[Dict]:
        """List recent sessions sorted by last access time."""
        sessions = self.sessions_index["sessions"]
        # Sort by last_accessed descending
        sorted_sessions = sorted(
            sessions, 
            key=lambda x: x.get("last_accessed", x.get("created", "")),
            reverse=True
        )
        return sorted_sessions[:limit]
    
    def format_session_list(self) -> str:
        """Format session list for display."""
        sessions = self.list_recent_sessions()
        if not sessions:
            return "No previous sessions found."
        
        lines = ["Available Sessions:", "=" * 60]
        
        for i, session in enumerate(sessions, 1):
            session_id = session["id"]
            created = datetime.fromisoformat(session["created"]).strftime("%Y-%m-%d %H:%M")
            project = os.path.basename(session.get("project_root", "Unknown"))
            
            # Check if conversation exists
            conv_file = os.path.join(self.sessions_dir, session.get("conversation_file", ""))
            has_conversation = os.path.exists(conv_file)
            
            lines.append(f"\n{i}. Session ID: {session_id}")
            lines.append(f"   Created: {created}")
            lines.append(f"   Project: {project}")
            lines.append(f"   Has conversation: {'Yes' if has_conversation else 'No'}")
        
        return "\n".join(lines)
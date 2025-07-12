"""Proactive monitoring system for real-time error detection and suggestions.

This module watches the session log in real-time and provides immediate
feedback when errors are detected.
"""

import os
import time
import json
import threading
from pathlib import Path
from typing import List, Dict, Optional, Callable
from datetime import datetime
from collections import deque

from error_patterns import ErrorDetector, ErrorDetection, ErrorSeverity, ErrorCategory


class ProactiveMonitor:
    """Monitors session logs and provides real-time error detection."""
    
    def __init__(
        self,
        log_file: str,
        sessions_dir: str,
        check_interval: float = 0.5,
        max_suggestions: int = 5
    ):
        """Initialize the proactive monitor.
        
        Args:
            log_file: Path to the session log file to monitor
            sessions_dir: Directory for IPC files
            check_interval: How often to check for new content (seconds)
            max_suggestions: Maximum number of suggestions to keep active
        """
        self.log_file = Path(log_file)
        self.sessions_dir = Path(sessions_dir)
        self.check_interval = check_interval
        self.max_suggestions = max_suggestions
        
        self.error_detector = ErrorDetector()
        self.last_position = 0
        self.session_id = self._extract_session_id()
        self.active_suggestions = deque(maxlen=max_suggestions)
        self.monitoring = False
        self.monitor_thread = None
        
        # IPC files
        self.notification_file = self.sessions_dir / "buddy_notification.tmp"
        self.suggestion_file = self.sessions_dir / "buddy_suggestions.json"
        
    def _extract_session_id(self) -> str:
        """Extract session ID from log filename."""
        # Pattern: claude_session_YYYYMMDD_HHMMSS.log
        name = self.log_file.stem
        if name.startswith("claude_session_"):
            return name.replace("claude_session_", "")
        return str(int(time.time()))
    
    def start(self):
        """Start the proactive monitoring in a background thread."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        print(f"🔍 Proactive monitoring started for session {self.session_id}")
    
    def stop(self):
        """Stop the proactive monitoring."""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self._cleanup_notifications()
        print("🔍 Proactive monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.monitoring:
            try:
                self._check_for_new_content()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in monitor loop: {e}")
                time.sleep(1)
    
    def _check_for_new_content(self):
        """Check log file for new content since last check."""
        if not self.log_file.exists():
            return
            
        try:
            # Get file size
            file_size = self.log_file.stat().st_size
            
            # If file has shrunk, reset position
            if file_size < self.last_position:
                self.last_position = 0
            
            # If no new content, return
            if file_size == self.last_position:
                return
            
            # Read new content
            with open(self.log_file, 'r', encoding='utf-8', errors='ignore') as f:
                f.seek(self.last_position)
                new_content = f.read()
                self.last_position = f.tell()
            
            if new_content.strip():
                self._process_new_content(new_content)
                
        except Exception as e:
            print(f"Error reading log file: {e}")
    
    def _process_new_content(self, content: str):
        """Process new log content for errors."""
        # Detect new errors
        errors = self.error_detector.detect_new_errors(content, self.session_id)
        
        if not errors:
            return
        
        # Filter and prioritize errors
        errors = self._prioritize_errors(errors)
        
        # Add to active suggestions
        for error in errors[:self.max_suggestions]:
            self._add_suggestion(error)
        
        # Notify if we have critical or multiple errors
        if any(e.severity == ErrorSeverity.CRITICAL for e in errors) or len(errors) >= 2:
            self._send_notification(errors)
    
    def _prioritize_errors(self, errors: List[ErrorDetection]) -> List[ErrorDetection]:
        """Prioritize errors by severity and relevance."""
        # Sort by severity (critical first) and category importance
        severity_order = {
            ErrorSeverity.CRITICAL: 0,
            ErrorSeverity.ERROR: 1,
            ErrorSeverity.WARNING: 2,
            ErrorSeverity.INFO: 3
        }
        
        category_importance = {
            ErrorCategory.SECURITY: 0,
            ErrorCategory.RUNTIME: 1,
            ErrorCategory.SYNTAX: 2,
            ErrorCategory.TYPE: 3,
            ErrorCategory.IMPORT: 4,
            ErrorCategory.PERFORMANCE: 5,
            ErrorCategory.STYLE: 6
        }
        
        return sorted(
            errors,
            key=lambda e: (
                severity_order.get(e.severity, 999),
                category_importance.get(e.category, 999)
            )
        )
    
    def _add_suggestion(self, error: ErrorDetection):
        """Add error to active suggestions."""
        suggestion = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error.error_type,
            "category": error.category.value,
            "severity": error.severity.value,
            "description": error.description,
            "suggestion": error.suggestion,
            "context": error.context,
            "line_number": error.line_number
        }
        
        self.active_suggestions.append(suggestion)
        self._save_suggestions()
    
    def _save_suggestions(self):
        """Save active suggestions to file."""
        try:
            suggestions_data = {
                "session_id": self.session_id,
                "updated": datetime.now().isoformat(),
                "suggestions": list(self.active_suggestions)
            }
            
            with open(self.suggestion_file, 'w') as f:
                json.dump(suggestions_data, f, indent=2)
                
        except Exception as e:
            print(f"Error saving suggestions: {e}")
    
    def _send_notification(self, errors: List[ErrorDetection]):
        """Send notification about detected errors."""
        try:
            # Create notification summary
            critical_count = sum(1 for e in errors if e.severity == ErrorSeverity.CRITICAL)
            error_count = sum(1 for e in errors if e.severity == ErrorSeverity.ERROR)
            
            notification = {
                "timestamp": datetime.now().isoformat(),
                "type": "error_detection",
                "summary": f"Detected {len(errors)} issue(s)",
                "critical_count": critical_count,
                "error_count": error_count,
                "top_suggestion": errors[0].suggestion if errors else None
            }
            
            # Write notification
            with open(self.notification_file, 'w') as f:
                json.dump(notification, f)
                
        except Exception as e:
            print(f"Error sending notification: {e}")
    
    def _cleanup_notifications(self):
        """Clean up notification files."""
        try:
            if self.notification_file.exists():
                self.notification_file.unlink()
            if self.suggestion_file.exists():
                self.suggestion_file.unlink()
        except Exception:
            pass
    
    def get_active_suggestions(self) -> List[Dict]:
        """Get current active suggestions."""
        return list(self.active_suggestions)
    
    def clear_suggestions(self):
        """Clear all active suggestions."""
        self.active_suggestions.clear()
        self._save_suggestions()


class ProactiveUI:
    """UI component for displaying proactive suggestions."""
    
    def __init__(self, sessions_dir: str):
        """Initialize the UI component."""
        self.sessions_dir = Path(sessions_dir)
        self.notification_file = self.sessions_dir / "buddy_notification.tmp"
        self.suggestion_file = self.sessions_dir / "buddy_suggestions.json"
        self.last_notification_time = None
        
    def check_notifications(self) -> Optional[Dict]:
        """Check for new notifications."""
        if not self.notification_file.exists():
            return None
            
        try:
            with open(self.notification_file, 'r') as f:
                notification = json.load(f)
            
            # Check if this is a new notification
            timestamp = notification.get("timestamp")
            if timestamp != self.last_notification_time:
                self.last_notification_time = timestamp
                
                # Delete notification file after reading
                self.notification_file.unlink()
                return notification
                
        except Exception:
            pass
            
        return None
    
    def get_suggestions(self) -> Optional[Dict]:
        """Get current suggestions."""
        if not self.suggestion_file.exists():
            return None
            
        try:
            with open(self.suggestion_file, 'r') as f:
                return json.load(f)
        except Exception:
            return None
    
    def format_notification(self, notification: Dict) -> str:
        """Format notification for display."""
        if not notification:
            return ""
            
        lines = [
            "\n🚨 " + "=" * 50,
            f"⚠️  {notification['summary']}",
        ]
        
        if notification.get('critical_count', 0) > 0:
            lines.append(f"🔴 Critical: {notification['critical_count']}")
        if notification.get('error_count', 0) > 0:
            lines.append(f"🟡 Errors: {notification['error_count']}")
            
        if notification.get('top_suggestion'):
            lines.append(f"\n💡 Quick Fix: {notification['top_suggestion']}")
            
        lines.append("=" * 50 + "\n")
        
        return "\n".join(lines)
    
    def format_suggestions(self, suggestions_data: Dict) -> str:
        """Format suggestions for display."""
        if not suggestions_data or not suggestions_data.get('suggestions'):
            return ""
            
        lines = ["\n📋 Active Suggestions:"]
        
        for i, suggestion in enumerate(suggestions_data['suggestions'], 1):
            severity_icon = {
                'critical': '🔴',
                'error': '🟡',
                'warning': '🟠',
                'info': 'ℹ️'
            }.get(suggestion['severity'], '•')
            
            lines.append(f"\n{severity_icon} {i}. {suggestion['description']}")
            lines.append(f"   💡 {suggestion['suggestion']}")
            
            if suggestion.get('line_number'):
                lines.append(f"   📍 Line {suggestion['line_number']}")
                
        return "\n".join(lines)


def integrate_with_monitoring_agent(monitor: ProactiveMonitor):
    """Integration helper to add proactive monitoring to existing monitoring agent."""
    # This would be called from monitoring_agent.py during initialization
    monitor.start()
    
    # Return a cleanup function
    def cleanup():
        monitor.stop()
    
    return cleanup
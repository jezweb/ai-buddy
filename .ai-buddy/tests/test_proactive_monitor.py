"""Tests for the proactive monitoring module."""

import json
import time
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call
from datetime import datetime
from freezegun import freeze_time

from error_patterns import (
    ErrorPattern,
    ErrorCategory,
    ErrorSeverity,
    ErrorDetector,
    ErrorDetection,
)
from proactive_monitor import ProactiveMonitor, ProactiveUI


class TestErrorPatterns:
    """Test error pattern detection."""

    @pytest.mark.unit
    def test_python_syntax_error_detection(self):
        """Test detecting Python syntax errors."""
        detector = ErrorDetector()
        
        log_content = '''File "test.py", line 42
            print("hello"
                    ^
SyntaxError: unexpected EOF while parsing'''
        
        errors = detector.detect_errors(log_content)
        
        assert len(errors) == 1
        assert errors[0].error_type == "python_syntax_error"
        assert errors[0].category == ErrorCategory.SYNTAX
        assert errors[0].severity == ErrorSeverity.ERROR
        assert errors[0].line_number == 42
        assert "Fix syntax error in test.py at line 42" in errors[0].suggestion

    @pytest.mark.unit
    def test_import_error_detection(self):
        """Test detecting import errors."""
        detector = ErrorDetector()
        
        log_content = "ModuleNotFoundError: No module named 'pandas'"
        
        errors = detector.detect_errors(log_content)
        
        assert len(errors) == 1
        assert errors[0].error_type == "import_error"
        assert errors[0].category == ErrorCategory.IMPORT
        assert "pip install pandas" in errors[0].suggestion

    @pytest.mark.unit
    def test_none_type_error_detection(self):
        """Test detecting NoneType attribute errors."""
        detector = ErrorDetector()
        
        log_content = "AttributeError: 'NoneType' object has no attribute 'get'"
        
        errors = detector.detect_errors(log_content)
        
        assert len(errors) == 1
        assert errors[0].error_type == "type_error_none"
        assert errors[0].category == ErrorCategory.TYPE
        assert "Add null check before accessing '.get'" in errors[0].suggestion

    @pytest.mark.unit
    def test_hardcoded_secret_detection(self):
        """Test detecting hardcoded secrets."""
        detector = ErrorDetector()
        
        log_content = 'api_key = "sk-1234567890abcdef"'
        
        errors = detector.detect_errors(log_content)
        
        assert len(errors) == 1
        assert errors[0].error_type == "hardcoded_secret"
        assert errors[0].category == ErrorCategory.SECURITY
        assert errors[0].severity == ErrorSeverity.CRITICAL
        assert "Move api_key to environment variable" in errors[0].suggestion

    @pytest.mark.unit
    def test_multiple_error_detection(self):
        """Test detecting multiple errors in log."""
        detector = ErrorDetector()
        
        log_content = '''ModuleNotFoundError: No module named 'requests'
File "app.py", line 10
    def process(
             ^
SyntaxError: unexpected EOF while parsing
AttributeError: 'NoneType' object has no attribute 'json'
'''
        
        errors = detector.detect_errors(log_content)
        
        assert len(errors) == 3
        # Check that all expected errors are found (order may vary)
        error_types = [e.error_type for e in errors]
        assert "import_error" in error_types
        assert "python_syntax_error" in error_types
        assert "type_error_none" in error_types

    @pytest.mark.unit
    def test_error_context_extraction(self):
        """Test that error context is properly extracted."""
        detector = ErrorDetector()
        
        log_content = '''Line 1
Line 2
KeyError: 'missing_key'
Line 4
Line 5'''
        
        errors = detector.detect_errors(log_content)
        
        assert len(errors) == 1
        assert "Line 1" in errors[0].context
        assert "Line 5" in errors[0].context
        assert "KeyError" in errors[0].context

    @pytest.mark.unit
    def test_new_error_detection(self):
        """Test detecting only new errors."""
        detector = ErrorDetector()
        
        # First detection
        log1 = "KeyError: 'key1'"
        errors1 = detector.detect_new_errors(log1, "session_123")
        assert len(errors1) == 1
        
        # Same error again - should not be detected
        errors2 = detector.detect_new_errors(log1, "session_123")
        assert len(errors2) == 0
        
        # Different error - should be detected
        log2 = "KeyError: 'key2'"
        errors3 = detector.detect_new_errors(log2, "session_123")
        assert len(errors3) == 1
        
        # Different session - same error should be detected
        errors4 = detector.detect_new_errors(log1, "session_456")
        assert len(errors4) == 1


class TestProactiveMonitor:
    """Test proactive monitoring functionality."""

    @pytest.fixture
    def monitor(self, temp_dir, mock_sessions_dir):
        """Create a monitor instance."""
        log_file = temp_dir / "test_session.log"
        log_file.touch()
        return ProactiveMonitor(str(log_file), str(mock_sessions_dir))

    @pytest.mark.unit
    def test_monitor_initialization(self, monitor):
        """Test monitor initialization."""
        assert monitor.monitoring is False
        assert monitor.last_position == 0
        assert monitor.session_id is not None
        assert monitor.max_suggestions == 5

    @pytest.mark.unit
    def test_monitor_start_stop(self, monitor):
        """Test starting and stopping monitor."""
        # Start monitoring
        monitor.start()
        assert monitor.monitoring is True
        assert monitor.monitor_thread is not None
        assert monitor.monitor_thread.is_alive()
        
        # Stop monitoring
        monitor.stop()
        assert monitor.monitoring is False

    @pytest.mark.unit
    def test_session_id_extraction(self, temp_dir, mock_sessions_dir):
        """Test extracting session ID from log filename."""
        # Test with standard format
        log_file = temp_dir / "claude_session_20250112_143000.log"
        log_file.touch()
        monitor = ProactiveMonitor(str(log_file), str(mock_sessions_dir))
        assert monitor.session_id == "20250112_143000"
        
        # Test with non-standard format
        log_file2 = temp_dir / "custom.log"
        log_file2.touch()
        monitor2 = ProactiveMonitor(str(log_file2), str(mock_sessions_dir))
        assert monitor2.session_id.isdigit()  # Should be timestamp

    @pytest.mark.unit
    def test_check_for_new_content(self, monitor, temp_dir):
        """Test checking for new content in log file."""
        log_file = Path(monitor.log_file)
        
        # Write initial content
        log_file.write_text("Initial content\n")
        monitor._check_for_new_content()
        assert monitor.last_position > 0
        
        # Write new content
        with open(log_file, 'a') as f:
            f.write("KeyError: 'test_key'\n")
        
        # Mock process_new_content
        with patch.object(monitor, '_process_new_content') as mock_process:
            monitor._check_for_new_content()
            mock_process.assert_called_once()
            assert "KeyError" in mock_process.call_args[0][0]

    @pytest.mark.unit
    def test_process_new_content_with_errors(self, monitor):
        """Test processing content with errors."""
        content = "ModuleNotFoundError: No module named 'test_module'"
        
        # Mock methods
        with patch.object(monitor, '_add_suggestion') as mock_add:
            with patch.object(monitor, '_send_notification') as mock_notify:
                monitor._process_new_content(content)
                
                # Should add suggestion
                mock_add.assert_called_once()
                error = mock_add.call_args[0][0]
                assert error.error_type == "import_error"
                
                # Should not notify for single non-critical error
                mock_notify.assert_not_called()

    @pytest.mark.unit
    def test_process_critical_error_notification(self, monitor):
        """Test that critical errors trigger notification."""
        content = 'password = "hardcoded_secret_123"'
        
        with patch.object(monitor, '_send_notification') as mock_notify:
            monitor._process_new_content(content)
            
            # Should notify for critical error
            mock_notify.assert_called_once()
            errors = mock_notify.call_args[0][0]
            assert len(errors) == 1
            assert errors[0].severity == ErrorSeverity.CRITICAL

    @pytest.mark.unit
    def test_prioritize_errors(self, monitor):
        """Test error prioritization."""
        errors = [
            ErrorDetection(
                error_type="info",
                category=ErrorCategory.STYLE,
                severity=ErrorSeverity.INFO,
                line_number=None,
                description="Info",
                suggestion="Info suggestion",
                context=""
            ),
            ErrorDetection(
                error_type="critical",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                line_number=None,
                description="Critical",
                suggestion="Critical suggestion",
                context=""
            ),
            ErrorDetection(
                error_type="error",
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.ERROR,
                line_number=None,
                description="Error",
                suggestion="Error suggestion",
                context=""
            ),
        ]
        
        prioritized = monitor._prioritize_errors(errors)
        
        # Critical should be first
        assert prioritized[0].severity == ErrorSeverity.CRITICAL
        assert prioritized[1].severity == ErrorSeverity.ERROR
        assert prioritized[2].severity == ErrorSeverity.INFO

    @pytest.mark.unit
    def test_save_and_load_suggestions(self, monitor):
        """Test saving and loading suggestions."""
        # Add a suggestion
        error = ErrorDetection(
            error_type="test_error",
            category=ErrorCategory.RUNTIME,
            severity=ErrorSeverity.ERROR,
            line_number=42,
            description="Test error",
            suggestion="Test suggestion",
            context="Test context"
        )
        
        with freeze_time("2025-01-12 10:00:00"):
            monitor._add_suggestion(error)
        
        # Verify file was created
        assert monitor.suggestion_file.exists()
        
        # Load and verify content
        with open(monitor.suggestion_file) as f:
            data = json.load(f)
        
        assert data["session_id"] == monitor.session_id
        assert len(data["suggestions"]) == 1
        assert data["suggestions"][0]["error_type"] == "test_error"
        assert data["suggestions"][0]["line_number"] == 42

    @pytest.mark.unit
    def test_notification_creation(self, monitor):
        """Test notification file creation."""
        errors = [
            ErrorDetection(
                error_type="critical",
                category=ErrorCategory.SECURITY,
                severity=ErrorSeverity.CRITICAL,
                line_number=None,
                description="Critical error",
                suggestion="Fix immediately",
                context=""
            ),
            ErrorDetection(
                error_type="error",
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.ERROR,
                line_number=None,
                description="Runtime error",
                suggestion="Check code",
                context=""
            ),
        ]
        
        with freeze_time("2025-01-12 10:00:00"):
            monitor._send_notification(errors)
        
        # Verify notification file
        assert monitor.notification_file.exists()
        
        with open(monitor.notification_file) as f:
            notification = json.load(f)
        
        assert notification["type"] == "error_detection"
        assert notification["summary"] == "Detected 2 issue(s)"
        assert notification["critical_count"] == 1
        assert notification["error_count"] == 1
        assert notification["top_suggestion"] == "Fix immediately"

    @pytest.mark.unit
    def test_max_suggestions_limit(self, monitor):
        """Test that suggestions are limited."""
        # Add more than max suggestions
        for i in range(10):
            error = ErrorDetection(
                error_type=f"error_{i}",
                category=ErrorCategory.RUNTIME,
                severity=ErrorSeverity.ERROR,
                line_number=i,
                description=f"Error {i}",
                suggestion=f"Fix {i}",
                context=""
            )
            monitor._add_suggestion(error)
        
        # Should only keep max_suggestions
        assert len(monitor.active_suggestions) == monitor.max_suggestions


class TestProactiveUI:
    """Test proactive UI functionality."""

    @pytest.fixture
    def ui(self, mock_sessions_dir):
        """Create UI instance."""
        return ProactiveUI(str(mock_sessions_dir))

    @pytest.mark.unit
    def test_check_notifications_none(self, ui):
        """Test checking when no notifications exist."""
        result = ui.check_notifications()
        assert result is None

    @pytest.mark.unit
    def test_check_notifications_new(self, ui):
        """Test checking new notifications."""
        # Create notification
        notification = {
            "timestamp": "2025-01-12T10:00:00",
            "type": "error_detection",
            "summary": "Detected 1 issue(s)",
            "critical_count": 0,
            "error_count": 1,
            "top_suggestion": "Fix the error"
        }
        
        with open(ui.notification_file, 'w') as f:
            json.dump(notification, f)
        
        # Check notification
        result = ui.check_notifications()
        assert result is not None
        assert result["summary"] == "Detected 1 issue(s)"
        
        # File should be deleted
        assert not ui.notification_file.exists()
        
        # Second check should return None
        result2 = ui.check_notifications()
        assert result2 is None

    @pytest.mark.unit
    def test_get_suggestions(self, ui):
        """Test getting suggestions."""
        # No suggestions file
        assert ui.get_suggestions() is None
        
        # Create suggestions
        suggestions_data = {
            "session_id": "test_123",
            "updated": "2025-01-12T10:00:00",
            "suggestions": [
                {
                    "timestamp": "2025-01-12T10:00:00",
                    "error_type": "import_error",
                    "category": "import",
                    "severity": "error",
                    "description": "Missing module",
                    "suggestion": "pip install missing",
                    "context": "import missing",
                    "line_number": None
                }
            ]
        }
        
        with open(ui.suggestion_file, 'w') as f:
            json.dump(suggestions_data, f)
        
        # Get suggestions
        result = ui.get_suggestions()
        assert result is not None
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["error_type"] == "import_error"

    @pytest.mark.unit
    def test_format_notification(self, ui):
        """Test formatting notifications."""
        notification = {
            "summary": "Detected 3 issue(s)",
            "critical_count": 1,
            "error_count": 2,
            "top_suggestion": "Fix critical security issue"
        }
        
        formatted = ui.format_notification(notification)
        
        assert "Detected 3 issue(s)" in formatted
        assert "🔴 Critical: 1" in formatted
        assert "🟡 Errors: 2" in formatted
        assert "💡 Quick Fix: Fix critical security issue" in formatted

    @pytest.mark.unit
    def test_format_suggestions(self, ui):
        """Test formatting suggestions display."""
        suggestions_data = {
            "suggestions": [
                {
                    "severity": "critical",
                    "description": "Hardcoded password",
                    "suggestion": "Use environment variable",
                    "line_number": 42
                },
                {
                    "severity": "error",
                    "description": "Import error",
                    "suggestion": "Install missing module",
                    "line_number": None
                }
            ]
        }
        
        formatted = ui.format_suggestions(suggestions_data)
        
        assert "📋 Active Suggestions:" in formatted
        assert "🔴 1. Hardcoded password" in formatted
        assert "💡 Use environment variable" in formatted
        assert "📍 Line 42" in formatted
        assert "🟡 2. Import error" in formatted

    @pytest.mark.unit
    def test_format_empty_suggestions(self, ui):
        """Test formatting empty suggestions."""
        assert ui.format_suggestions({}) == ""
        assert ui.format_suggestions({"suggestions": []}) == ""


class TestIntegration:
    """Integration tests for proactive monitoring."""

    @pytest.mark.integration
    def test_full_monitoring_flow(self, temp_dir, mock_sessions_dir):
        """Test complete monitoring flow from error detection to UI display."""
        # Create log file
        log_file = temp_dir / "session.log"
        log_file.write_text("Initial content\n")
        
        # Create monitor and UI
        monitor = ProactiveMonitor(str(log_file), str(mock_sessions_dir))
        ui = ProactiveUI(str(mock_sessions_dir))
        
        # Start monitoring
        monitor.start()
        
        try:
            # Simulate error in log
            with open(log_file, 'a') as f:
                f.write("ModuleNotFoundError: No module named 'test_module'\n")
                f.write("password = 'secret123'\n")
            
            # Give monitor time to process
            time.sleep(1)
            
            # Check for notification
            notification = ui.check_notifications()
            assert notification is not None
            assert "Detected 2 issue(s)" in notification["summary"]
            
            # Check suggestions
            suggestions = ui.get_suggestions()
            assert suggestions is not None
            assert len(suggestions["suggestions"]) == 2
            
            # Verify critical error is first
            assert suggestions["suggestions"][0]["severity"] == "critical"
            assert "secret" in suggestions["suggestions"][0]["description"].lower()
            
        finally:
            monitor.stop()

    @pytest.mark.integration
    def test_monitoring_with_no_errors(self, temp_dir, mock_sessions_dir):
        """Test monitoring when no errors occur."""
        log_file = temp_dir / "clean_session.log"
        log_file.write_text("Normal log output\n")
        
        monitor = ProactiveMonitor(str(log_file), str(mock_sessions_dir))
        ui = ProactiveUI(str(mock_sessions_dir))
        
        monitor.start()
        
        try:
            # Add normal content
            with open(log_file, 'a') as f:
                f.write("Processing complete\n")
                f.write("All tests passed\n")
            
            time.sleep(1)
            
            # Should have no notifications or suggestions
            assert ui.check_notifications() is None
            assert ui.get_suggestions() is None
            
        finally:
            monitor.stop()
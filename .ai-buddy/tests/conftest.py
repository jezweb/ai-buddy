"""Shared fixtures and configuration for AI Buddy tests."""

import sys
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import pytest

# Add parent directory to path so we can import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_path = tempfile.mkdtemp()
    yield Path(temp_path)
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def mock_sessions_dir(temp_dir):
    """Create a mock sessions directory."""
    sessions_path = temp_dir / "sessions"
    sessions_path.mkdir(exist_ok=True)
    return sessions_path


@pytest.fixture
def mock_project_root(temp_dir):
    """Create a mock project structure."""
    # Create typical project structure
    (temp_dir / "src").mkdir()
    (temp_dir / "tests").mkdir()
    (temp_dir / ".git").mkdir()

    # Create some sample files
    (temp_dir / "README.md").write_text("# Test Project\n")
    (temp_dir / "src" / "main.py").write_text("def main():\n    print('Hello')\n")
    (temp_dir / "src" / "utils.py").write_text("def helper():\n    pass\n")
    (temp_dir / "tests" / "test_main.py").write_text(
        "def test_main():\n    assert True\n"
    )
    (temp_dir / ".gitignore").write_text("*.pyc\n__pycache__/\n")

    return temp_dir


@pytest.fixture
def mock_genai_client():
    """Mock Google GenAI client."""
    client = MagicMock()

    # Mock model response
    response = MagicMock()
    response.text = "This is a test response from Gemini."
    client.models.generate_content.return_value = response

    # Mock file operations
    uploaded_file = MagicMock()
    uploaded_file.name = "test_file_123"
    client.files.upload.return_value = uploaded_file
    client.files.list.return_value = []
    client.files.delete.return_value = None

    return client


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Set up test environment variables."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-api-key-123")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    monkeypatch.setenv("POLLING_INTERVAL", "0.1")  # Fast polling for tests
    monkeypatch.setenv("SMART_CONTEXT_ENABLED", "true")
    monkeypatch.setenv("MAX_CONTEXT_SIZE", "50000")


@pytest.fixture
def sample_conversation():
    """Sample conversation history."""
    return [
        {
            "timestamp": "2025-01-12T10:00:00",
            "question": "How do I implement error handling?",
            "response": "You can use try-except blocks in Python.",
        },
        {
            "timestamp": "2025-01-12T10:05:00",
            "question": "Can you show an example?",
            "response": "Here's an example:\n```python\ntry:\n    result = risky_operation()\nexcept Exception as e:\n    print(f'Error: {e}')\n```",
        },
    ]


@pytest.fixture
def sample_session_log():
    """Sample Claude session log content."""
    return """Script started on 2025-01-12 10:00:00
$ claude "Help me fix the authentication bug"

Looking at your code...

[Claude output continues...]

$ echo "Fixed!"
Fixed!

Script done on 2025-01-12 10:30:00
"""


@pytest.fixture
def sample_file_operation_request():
    """Sample file operation request from Gemini."""
    return {
        "summary": "Create a new test file",
        "operations": [
            {
                "operation": "create",
                "path": "tests/test_new_feature.py",
                "content": "def test_new_feature():\n    assert True\n",
                "description": "New test file for the feature",
                "overwrite": False,
            }
        ],
        "warnings": [],
    }


@pytest.fixture
def mock_subprocess(monkeypatch):
    """Mock subprocess calls for git commands."""

    def mock_run(*args, **kwargs):
        result = Mock()
        result.returncode = 0

        # Handle different git commands
        if "git" in args[0] and "ls-files" in args[0]:
            result.stdout = "src/main.py\nsrc/utils.py\ntests/test_main.py\n"
        elif "git" in args[0] and "status" in args[0]:
            result.stdout = "On branch main\nnothing to commit, working tree clean\n"
        else:
            result.stdout = ""

        return result

    monkeypatch.setattr("subprocess.run", mock_run)


@pytest.fixture
def mock_time(monkeypatch):
    """Mock time for consistent testing."""
    current_time = 1736683200.0  # 2025-01-12 12:00:00 UTC
    monkeypatch.setattr("time.time", lambda: current_time)
    return current_time


@pytest.fixture
def ipc_files(mock_sessions_dir):
    """Create IPC file paths."""
    return {
        "request": mock_sessions_dir / "buddy_request.tmp",
        "response": mock_sessions_dir / "buddy_response.tmp",
        "processing": mock_sessions_dir / "buddy_processing.tmp",
        "heartbeat": mock_sessions_dir / "buddy_heartbeat.tmp",
        "refresh": mock_sessions_dir / "buddy_refresh_request.tmp",
        "changes": mock_sessions_dir / "changes.log",
    }


@pytest.fixture(autouse=True)
def cleanup_singletons():
    """Clean up any singleton instances between tests."""
    # This ensures tests don't interfere with each other
    yield
    # Add any singleton cleanup here if needed


@pytest.fixture
def mock_prompt_toolkit():
    """Mock prompt_toolkit for UI testing."""
    with patch("prompt_toolkit.prompt") as mock_prompt:
        mock_prompt.return_value = "test input"
        yield mock_prompt


# Markers for different test types
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "requires_api: Tests that require API access")

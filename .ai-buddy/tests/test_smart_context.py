"""Tests for the smart context module."""

import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

from smart_context import (
    QueryIntent,
    FileRelevance,
    QueryAnalyzer,
    FileScorer,
    SmartContextBuilder,
)


class TestQueryIntent:
    """Test QueryIntent enum."""

    @pytest.mark.unit
    def test_query_intent_values(self):
        """Test QueryIntent enum values."""
        assert QueryIntent.DEBUG == "debug"
        assert QueryIntent.FEATURE == "feature"
        assert QueryIntent.EXPLAIN == "explain"
        assert QueryIntent.REFACTOR == "refactor"
        assert QueryIntent.TEST == "test"
        assert QueryIntent.DOCUMENT == "document"
        assert QueryIntent.CONFIG == "config"
        assert QueryIntent.GENERAL == "general"


class TestQueryAnalyzer:
    """Test QueryAnalyzer functionality."""

    @pytest.fixture
    def analyzer(self):
        return QueryAnalyzer()

    @pytest.mark.unit
    def test_detect_debug_intent(self, analyzer):
        """Test detecting debug intent."""
        debug_queries = [
            "Why is this function failing?",
            "Fix the authentication error",
            "Debug the login issue",
            "The app crashes when I click submit",
            "Something is broken in the payment flow",
            "Exception thrown in utils.py",
        ]

        for query in debug_queries:
            intent, _, _ = analyzer.analyze(query)
            assert intent == QueryIntent.DEBUG, f"Failed for: {query}"

    @pytest.mark.unit
    def test_detect_feature_intent(self, analyzer):
        """Test detecting feature intent."""
        feature_queries = [
            "Add a new dark mode toggle",
            "Implement user authentication",
            "Create a dashboard component",
            "Build export functionality",
            "I want to add real-time updates",
            "We need a notification system",
        ]

        for query in feature_queries:
            intent, _, _ = analyzer.analyze(query)
            assert intent == QueryIntent.FEATURE, f"Failed for: {query}"

    @pytest.mark.unit
    def test_detect_explain_intent(self, analyzer):
        """Test detecting explain intent."""
        explain_queries = [
            "What does this function do?",
            "How does authentication work?",
            "Explain the data flow",
            "Tell me about the architecture",
            "Show me how routing works",
            "Why was this implemented this way?",
        ]

        for query in explain_queries:
            intent, _, _ = analyzer.analyze(query)
            assert intent == QueryIntent.EXPLAIN, f"Failed for: {query}"

    @pytest.mark.unit
    def test_detect_test_intent(self, analyzer):
        """Test detecting test intent."""
        test_queries = [
            "Write unit tests for the auth module",
            "Add test coverage for utils",
            "Create integration tests",
            "Test the payment flow",
            "Mock the API calls in tests",
            "Improve test coverage",
        ]

        for query in test_queries:
            intent, _, _ = analyzer.analyze(query)
            assert intent == QueryIntent.TEST, f"Failed for: {query}"

    @pytest.mark.unit
    def test_extract_keywords(self, analyzer):
        """Test keyword extraction."""
        query = "Fix the authentication error in login.py when using OAuth"

        _, keywords, _ = analyzer.analyze(query)

        # Should extract meaningful words
        assert "authentication" in keywords
        assert "error" in keywords
        assert "login.py" in keywords
        assert "oauth" in keywords

        # Should not include stop words
        assert "the" not in keywords
        assert "in" not in keywords
        assert "when" not in keywords

    @pytest.mark.unit
    def test_extract_quoted_strings(self, analyzer):
        """Test extracting quoted strings as keywords."""
        query = 'Update the "UserProfile" component to handle "dark mode"'

        _, keywords, _ = analyzer.analyze(query)

        assert "UserProfile" in keywords
        assert "dark mode" in keywords

    @pytest.mark.unit
    def test_extract_file_paths(self, analyzer):
        """Test extracting file paths."""
        query = "Fix the bug in src/utils/auth.py and update tests/test_auth.py"

        _, keywords, _ = analyzer.analyze(query)

        assert "src/utils/auth.py" in keywords
        assert "tests/test_auth.py" in keywords

    @pytest.mark.unit
    def test_extract_technical_terms(self, analyzer):
        """Test extracting technical terms."""
        query = "The getUserData function in UserService.js needs refactoring"

        _, _, tech_terms = analyzer.analyze(query)

        # Should identify function names
        assert "getUserData" in tech_terms
        assert tech_terms["getUserData"] > 0.5

        # Should identify class names
        assert "UserService" in tech_terms

        # Should identify file extensions
        assert "*.js" in tech_terms

    @pytest.mark.unit
    def test_general_intent_fallback(self, analyzer):
        """Test falling back to general intent."""
        query = "Hello, can you help me?"

        intent, _, _ = analyzer.analyze(query)

        assert intent == QueryIntent.GENERAL


class TestFileScorer:
    """Test FileScorer functionality."""

    @pytest.fixture
    def scorer(self, mock_project_root):
        return FileScorer(str(mock_project_root))

    @pytest.mark.unit
    def test_score_by_filename_match(self, scorer, mock_project_root):
        """Test scoring based on filename matches."""
        # Create a file that matches keyword
        auth_file = mock_project_root / "src" / "auth.py"
        auth_file.parent.mkdir(exist_ok=True)
        auth_file.write_text("def authenticate(): pass")

        files = scorer.score_files(
            QueryIntent.DEBUG, ["auth", "login"], {}, max_files=10
        )

        # Should find and score the auth file
        auth_scores = [f for f in files if "auth.py" in f.path]
        assert len(auth_scores) > 0
        assert auth_scores[0].score > 0
        assert any("Filename contains 'auth'" in r for r in auth_scores[0].reasons)

    @pytest.mark.unit
    def test_score_by_path_match(self, scorer, mock_project_root):
        """Test scoring based on path matches."""
        # Create nested file
        utils_file = mock_project_root / "src" / "utils" / "helpers.py"
        utils_file.parent.mkdir(parents=True, exist_ok=True)
        utils_file.write_text("def helper(): pass")

        files = scorer.score_files(QueryIntent.GENERAL, ["utils"], {}, max_files=10)

        # Should find files in utils directory
        utils_scores = [f for f in files if "utils" in f.path]
        assert len(utils_scores) > 0
        assert any("Path contains 'utils'" in r for r in utils_scores[0].reasons)

    @pytest.mark.unit
    def test_score_by_intent_test_files(self, scorer, mock_project_root):
        """Test scoring test files for TEST intent."""
        files = scorer.score_files(QueryIntent.TEST, [], {}, max_files=10)

        # Should score test files higher
        test_files = [f for f in files if "test" in f.path.lower()]
        assert len(test_files) > 0
        assert any("Test file" in r for r in test_files[0].reasons)

    @pytest.mark.unit
    def test_score_by_recency(self, scorer, mock_project_root):
        """Test scoring based on file modification time."""
        # Create a recently modified file
        recent_file = mock_project_root / "recent.py"
        recent_file.write_text("recent content")
        recent_file.touch()  # Update modification time

        files = scorer.score_files(QueryIntent.GENERAL, ["recent"], {}, max_files=10)

        # Should include recency bonus
        recent_scores = [f for f in files if "recent.py" in f.path]
        assert len(recent_scores) > 0
        assert any("Modified in last" in r for r in recent_scores[0].reasons)

    @pytest.mark.unit
    def test_score_technical_terms(self, scorer, mock_project_root):
        """Test scoring based on technical terms."""
        # Create Python files
        py_file = mock_project_root / "module.py"
        py_file.write_text("import os")

        files = scorer.score_files(
            QueryIntent.GENERAL, [], {"*.py": 0.9, "UserService": 0.7}, max_files=10
        )

        # Should score Python files higher
        py_files = [f for f in files if f.path.endswith(".py")]
        assert len(py_files) > 0
        assert any("File type matches *.py" in r for r in py_files[0].reasons)

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_git_ls_files_integration(self, mock_run, scorer, mock_project_root):
        """Test using git ls-files for file discovery."""
        # Mock git ls-files output
        mock_result = MagicMock()
        mock_result.stdout = "src/main.py\nsrc/utils.py\n.gitignore\n"
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        scorer.score_files(QueryIntent.GENERAL, ["main"], {}, max_files=10)

        # Should have called git ls-files
        mock_run.assert_called_once()
        assert "git" in mock_run.call_args[0][0]
        assert "ls-files" in mock_run.call_args[0][0]

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_fallback_to_walk_on_git_failure(self, mock_run, scorer, mock_project_root):
        """Test falling back to directory walk when git fails."""
        # Mock git failure
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git", "ls-files"])

        files = scorer.score_files(QueryIntent.GENERAL, ["main"], {}, max_files=10)

        # Should still find files using walk
        assert len(files) > 0


class TestSmartContextBuilder:
    """Test SmartContextBuilder functionality."""

    @pytest.fixture
    def builder(self, mock_project_root):
        return SmartContextBuilder(str(mock_project_root), max_context_size=5000)

    @pytest.mark.unit
    def test_build_context_basic(self, builder, mock_project_root):
        """Test basic context building."""
        query = "Fix the authentication bug"
        session_log = "Error in auth module"
        conversation = "User: Help me fix auth\nAssistant: Looking at the code..."

        context, included_files = builder.build_context(
            query, session_log, conversation
        )

        assert "### RECENT CONVERSATION ###" in context
        assert conversation in context
        assert "### RELEVANT PROJECT FILES ###" in context
        assert isinstance(included_files, list)

    @pytest.mark.unit
    def test_context_size_limits(self, builder, mock_project_root):
        """Test respecting context size limits."""
        # Create many files
        for i in range(20):
            file = mock_project_root / f"file{i}.py"
            file.write_text("x" * 1000)  # 1KB each

        query = "Show all files"
        context, included_files = builder.build_context(query, "", "")

        # Should respect max context size
        assert len(context) <= builder.max_context_size
        assert len(included_files) < 20  # Not all files included

    @pytest.mark.unit
    def test_debug_intent_includes_session_log(self, builder):
        """Test that debug intent includes session log."""
        query = "Debug the error in my code"
        session_log = "A" * 20000  # Large log

        context, _ = builder.build_context(query, session_log, "")

        # Should include recent portion of session log
        assert "### RECENT SESSION LOG ###" in context
        assert session_log[-10000:] in context  # Last 10KB

    @pytest.mark.unit
    def test_changes_log_inclusion(self, builder):
        """Test including changes log when available."""
        query = "What changed?"
        changes = "file1.py modified\nfile2.py created"

        context, _ = builder.build_context(query, "", "", changes_log=changes)

        assert "### RECENT CHANGES ###" in context
        assert changes in context

    @pytest.mark.unit
    def test_extract_relevant_portions_large_files(self, builder, mock_project_root):
        """Test extracting relevant portions from large files."""
        # Create large file with specific content
        large_file = mock_project_root / "large.py"
        lines = []
        for i in range(1000):
            if i == 500:
                lines.append("def authenticate_user():")
            else:
                lines.append(f"# Line {i}")
        large_file.write_text("\n".join(lines))

        # Mock the file scorer to return our large file
        with patch.object(builder.scorer, "score_files") as mock_score:
            mock_score.return_value = [
                FileRelevance(
                    path="large.py",
                    score=40,  # Low score triggers extraction
                    reasons=["keyword match"],
                    size=len(large_file.read_text()),
                    last_modified=datetime.now(),
                )
            ]

            context, _ = builder.build_context("fix authenticate_user function", "", "")

        # Should include relevant portion
        assert "authenticate_user" in context
        assert "[truncated]" in context

    @pytest.mark.unit
    def test_intent_based_context_sizing(self, builder):
        """Test different context sizes based on intent."""
        # Test different intents
        test_cases = [
            ("Debug the error", QueryIntent.DEBUG, 80000),
            ("Add new feature", QueryIntent.FEATURE, 60000),
            ("Explain this code", QueryIntent.EXPLAIN, 40000),
        ]

        for query, expected_intent, expected_size in test_cases:
            # Mock analyzer to return expected intent
            with patch.object(builder.analyzer, "analyze") as mock_analyze:
                mock_analyze.return_value = (expected_intent, [], {})

                # Access private method for testing
                size = builder._get_base_context_size(expected_intent)
                assert size == expected_size

    @pytest.mark.unit
    def test_file_read_error_handling(self, builder, mock_project_root, caplog):
        """Test handling files that can't be read."""
        # Create file then make it unreadable
        bad_file = mock_project_root / "bad.py"
        bad_file.write_text("content")

        # Mock file scorer to return the bad file
        with patch.object(builder.scorer, "score_files") as mock_score:
            mock_score.return_value = [
                FileRelevance(
                    path="bad.py",
                    score=100,
                    reasons=["high score"],
                    size=100,
                    last_modified=datetime.now(),
                )
            ]

            # Mock read to fail
            with patch.object(
                Path, "read_text", side_effect=PermissionError("No access")
            ):
                context, included_files = builder.build_context("test query", "", "")

        # Should handle error gracefully
        assert "bad.py" not in included_files
        assert "Error reading" in caplog.text

    @pytest.mark.unit
    def test_smart_context_integration(self, builder, mock_project_root):
        """Test full smart context flow."""
        # Create a mini project
        (mock_project_root / "auth.py").write_text("def login(): pass")
        (mock_project_root / "tests" / "test_auth.py").write_text(
            "def test_login(): pass"
        )
        (mock_project_root / "config.json").write_text('{"auth": true}')

        # Query about authentication
        context, included_files = builder.build_context(
            "How does authentication work in this project?",
            "Session log here",
            "Previous conversation",
        )

        # Should include relevant files
        assert any("auth.py" in f for f in included_files)

        # Should have proper structure
        assert "### RECENT CONVERSATION ###" in context
        assert "### RELEVANT PROJECT FILES ###" in context
        assert "FILE: auth.py" in context or "auth.py" in context

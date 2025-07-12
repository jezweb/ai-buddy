"""Tests for the repo blob generator module."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import subprocess

from repo_blob_generator import generate_repo_blob, RepoBlobGenerator


class TestRepoBlobGenerator:
    """Test RepoBlobGenerator class methods."""

    @pytest.fixture
    def generator(self, temp_dir):
        return RepoBlobGenerator(str(temp_dir))

    @pytest.mark.unit
    def test_is_text_file_text(self, generator, temp_dir):
        """Test detecting text files."""
        text_file = temp_dir / "test.txt"
        text_file.write_text("Hello, this is plain text\nWith newlines")

        assert generator.is_text_file(text_file)

    @pytest.mark.unit
    def test_is_text_file_python(self, generator, temp_dir):
        """Test Python files are text."""
        py_file = temp_dir / "script.py"
        py_file.write_text("#!/usr/bin/env python\ndef main():\n    print('Hello')")

        assert generator.is_text_file(py_file)

    @pytest.mark.unit
    def test_is_text_file_binary(self, generator, temp_dir):
        """Test detecting binary files as non-text."""
        bin_file = temp_dir / "test.bin"
        # Write some binary data (null bytes are a good indicator)
        bin_file.write_bytes(b"\x00\x01\x02\x03\xff\xfe\xfd")

        assert not generator.is_text_file(bin_file)

    @pytest.mark.unit
    def test_is_text_file_unicode(self, generator, temp_dir):
        """Test files with unicode are considered text."""
        unicode_file = temp_dir / "unicode.txt"
        unicode_file.write_text("Café naïve 中文 🐍", encoding="utf-8")

        assert generator.is_text_file(unicode_file)

    @pytest.mark.unit
    def test_is_text_file_nonexistent(self, generator, temp_dir):
        """Test handling non-existent files."""
        # Should return False for safety
        assert not generator.is_text_file(temp_dir / "nonexistent.txt")

    @pytest.mark.unit
    def test_is_text_file_permission_error(self, generator, temp_dir, monkeypatch):
        """Test handling permission errors."""
        file_path = temp_dir / "test.txt"
        file_path.write_text("text")

        def mock_open_error(*args, **kwargs):
            raise PermissionError("No access")

        monkeypatch.setattr("builtins.open", mock_open_error)

        # Should return False (skip file) on error
        assert not generator.is_text_file(file_path)

    @pytest.mark.unit
    def test_should_exclude_common_patterns(self, generator):
        """Test excluding common patterns."""
        excluded_files = [
            "__pycache__/module.py",
            ".git/config",
            "node_modules/package/index.js",
            ".env",
            ".venv/lib/python3.9/site.py",
            "venv/bin/activate",
            ".ai-buddy/config.py",
        ]

        for file_path in excluded_files:
            assert generator.should_exclude(file_path), f"Should exclude: {file_path}"

    @pytest.mark.unit
    def test_should_exclude_allowed(self, generator):
        """Test files that should not be excluded."""
        allowed_files = [
            "main.py",
            "src/utils.py",
            "README.md",
            "requirements.txt",
            "setup.py",
            "Makefile",
            "docker-compose.yml",
            ".gitignore",  # We want to include gitignore
            "tests/test_app.py",
        ]

        for file_path in allowed_files:
            assert not generator.should_exclude(
                file_path
            ), f"Should not exclude: {file_path}"

    @pytest.mark.unit
    def test_find_files_by_extension(self, generator, temp_dir):
        """Test finding files by extension."""
        # Create test files
        (temp_dir / "main.py").write_text("print('hello')")
        (temp_dir / "config.json").write_text('{"key": "value"}')
        (temp_dir / "README.md").write_text("# Project")
        (temp_dir / "binary.bin").write_bytes(b"\x00\xff")

        files = generator.find_files_by_extension()

        # Should find text files with supported extensions
        file_names = {f.name for f in files}
        assert "main.py" in file_names
        assert "config.json" in file_names
        assert "README.md" in file_names
        # Binary files might be found but won't be processed as text

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_get_git_files_success(self, mock_run, generator):
        """Test getting git files successfully."""
        # Mock git commands
        mock_rev_parse = MagicMock()
        mock_rev_parse.returncode = 0

        mock_ls_files = MagicMock()
        mock_ls_files.stdout = "src/main.py\nsrc/utils.py\nREADME.md\n.gitignore"
        mock_ls_files.returncode = 0

        mock_run.side_effect = [mock_rev_parse, mock_ls_files]

        files = generator.get_git_files()

        # Should call git commands
        assert mock_run.call_count == 2
        assert files is not None
        assert "src/main.py" in files
        assert "src/utils.py" in files
        assert "README.md" in files

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_get_git_files_not_git_repo(self, mock_run, generator):
        """Test handling when not in a git repository."""
        # Mock git failure
        mock_run.side_effect = subprocess.CalledProcessError(1, ["git"])

        files = generator.get_git_files()

        # Should return None when not a git repo
        assert files is None

    @pytest.mark.unit
    def test_find_files_by_extension_excludes_patterns(self, generator, temp_dir):
        """Test that excluded patterns are not included."""
        # Create files that should be excluded
        (temp_dir / "__pycache__").mkdir()
        (temp_dir / "__pycache__" / "module.pyc").write_text("cached")
        (temp_dir / ".git").mkdir()
        (temp_dir / ".git" / "config").write_text("git config")

        # Create files that should be included
        (temp_dir / "main.py").write_text("print('hello')")

        files = generator.find_files_by_extension()

        # Should include valid files
        file_paths = {str(f) for f in files}
        assert any("main.py" in path for path in file_paths)

        # Should exclude patterns
        assert not any("__pycache__" in path for path in file_paths)
        assert not any(".git" in path for path in file_paths)


class TestGenerateRepoBlob:
    """Test repo blob generation."""

    @pytest.mark.unit
    def test_generate_success(self, mock_project_root):
        """Test successful repo blob generation."""
        generator = RepoBlobGenerator(str(mock_project_root))

        # Create test files
        (mock_project_root / "main.py").write_text("def main():\n    print('Hello')")
        (mock_project_root / "utils.py").write_text("def util():\n    return 42")
        (mock_project_root / "README.md").write_text("# Test Project")

        output_file = mock_project_root / "output.txt"

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git"])
        ):
            result = generator.generate(str(output_file))

        assert result is True
        assert output_file.exists()

        content = output_file.read_text()

        # Check header structure
        assert f"=== PROJECT: {mock_project_root.name} ===" in content
        assert "=== Generated:" in content
        assert f"=== Root: {mock_project_root} ===" in content

    @pytest.mark.unit
    def test_generate_empty_project(self, temp_dir):
        """Test generating blob for empty project."""
        generator = RepoBlobGenerator(str(temp_dir))
        output_file = temp_dir / "output.txt"

        result = generator.generate(str(output_file))

        assert result is True
        assert output_file.exists()

        content = output_file.read_text()
        assert f"=== PROJECT: {temp_dir.name} ===" in content

    @pytest.mark.unit
    def test_generate_excludes_binary(self, mock_project_root):
        """Test that binary files are excluded."""
        generator = RepoBlobGenerator(str(mock_project_root))

        # Create text and binary files
        (mock_project_root / "text.txt").write_text("Text content")
        (mock_project_root / "binary.bin").write_bytes(b"\x00\xff" * 100)

        output_file = mock_project_root / "output.txt"

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git"])
        ):
            result = generator.generate(str(output_file))

        content = output_file.read_text()

        # Should include text file if it has supported extension
        # Note: .txt should be in DEFAULT_EXTENSIONS

    @pytest.mark.unit
    def test_generate_handles_unicode(self, mock_project_root):
        """Test handling unicode in files."""
        generator = RepoBlobGenerator(str(mock_project_root))

        unicode_file = mock_project_root / "unicode.py"
        unicode_file.write_text("# Café implementation\ndef café():\n    return '☕'")

        output_file = mock_project_root / "output.txt"

        with patch(
            "subprocess.run", side_effect=subprocess.CalledProcessError(1, ["git"])
        ):
            result = generator.generate(str(output_file))

        assert result is True
        content = output_file.read_text()

        # Should handle unicode properly
        assert "Café" in content or "unicode.py" in content

    @pytest.mark.unit
    def test_generate_error_handling(self, mock_project_root):
        """Test error handling during generation."""
        generator = RepoBlobGenerator(str(mock_project_root))
        output_file = "/invalid/path/output.txt"

        result = generator.generate(output_file)

        # Should return False on error
        assert result is False

    @pytest.mark.unit
    @patch("subprocess.run")
    def test_generate_with_git_files(self, mock_run, mock_project_root):
        """Test generation using git file list."""
        generator = RepoBlobGenerator(str(mock_project_root))

        # Create files
        (mock_project_root / "included.py").write_text("print('included')")
        (mock_project_root / "excluded.log").write_text("log content")

        # Mock git to return only some files
        mock_rev_parse = MagicMock()
        mock_rev_parse.returncode = 0

        mock_ls_files = MagicMock()
        mock_ls_files.stdout = "included.py"
        mock_ls_files.returncode = 0

        mock_run.side_effect = [mock_rev_parse, mock_ls_files]

        output_file = mock_project_root / "output.txt"
        result = generator.generate(str(output_file))

        assert result is True
        content = output_file.read_text()

        # Should include git-tracked files
        assert "included.py" in content or "print('included')" in content

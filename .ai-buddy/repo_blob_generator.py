#!/usr/bin/env python3
"""
Repo-Blob Generator
Creates a consolidated text file containing all project source files for AI context.
"""

import os
import subprocess
import datetime
import logging
from pathlib import Path
from typing import Optional, Set


class RepoBlobGenerator:
    """Generates a repo-blob file containing all project source files."""

    # File extensions to include when git is not available
    DEFAULT_EXTENSIONS = {
        ".py",
        ".txt",
        ".md",
        ".sh",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".html",
        ".css",
        ".json",
        ".yml",
        ".yaml",
        ".toml",
        ".ini",
        ".java",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".go",
        ".rs",
        ".rb",
    }

    # Patterns to exclude
    EXCLUDE_PATTERNS = {
        ".ai-buddy/",
        "__pycache__/",
        ".git/",
        "node_modules/",
        ".venv/",
        "venv/",
        "env/",
        ".env",
        ".pyc",
    }

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()
        self.logger = logging.getLogger(__name__)

    def is_text_file(self, file_path: Path) -> bool:
        """Check if a file is likely a text file (not binary)."""
        try:
            # Try to read first 1024 bytes
            with open(file_path, "rb") as f:
                chunk = f.read(1024)

            # Check for null bytes (common in binary files)
            if b"\x00" in chunk:
                return False

            # Try to decode as UTF-8
            try:
                chunk.decode("utf-8")
                return True
            except UnicodeDecodeError:
                return False

        except Exception:
            return False

    def should_exclude(self, file_path: str) -> bool:
        """Check if a file should be excluded based on patterns."""
        for pattern in self.EXCLUDE_PATTERNS:
            if pattern in file_path:
                return True
        return False

    def get_git_files(self) -> Optional[Set[str]]:
        """Get list of files tracked by git."""
        try:
            # Check if we're in a git repository
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.project_root,
                capture_output=True,
                check=True,
            )

            # Get list of tracked files
            result = subprocess.run(
                ["git", "ls-files"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            return set(result.stdout.strip().split("\n")) if result.stdout else set()

        except subprocess.CalledProcessError:
            return None

    def find_files_by_extension(self) -> Set[Path]:
        """Find files by extension when git is not available."""
        files = set()

        for ext in self.DEFAULT_EXTENSIONS:
            for file_path in self.project_root.rglob(f"*{ext}"):
                if not self.should_exclude(str(file_path)):
                    files.add(file_path)

        return files

    def generate(self, output_path: str) -> bool:
        """
        Generate the repo-blob file.

        Args:
            output_path: Path where the repo-blob file should be written

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Generating repo-blob from: {self.project_root}")

            with open(output_path, "w", encoding="utf-8") as output:
                # Write header
                output.write(f"=== PROJECT: {self.project_root.name} ===\n")
                output.write(f"=== Generated: {datetime.datetime.now()} ===\n")
                output.write(f"=== Root: {self.project_root} ===\n\n")

                # Get files to include
                git_files = self.get_git_files()

                if git_files is not None:
                    # Use git-tracked files
                    self.logger.info(
                        f"Using git to find files ({len(git_files)} tracked files)"
                    )

                    for file_name in sorted(git_files):
                        if self.should_exclude(file_name):
                            continue

                        file_path = self.project_root / file_name
                        if file_path.is_file() and self.is_text_file(file_path):
                            self._add_file_to_blob(output, file_path, file_name)
                else:
                    # Fall back to extension-based search
                    self.logger.info(
                        "No git repository found. Using extension-based file search."
                    )

                    files = self.find_files_by_extension()
                    for file_path in sorted(files):
                        relative_path = file_path.relative_to(self.project_root)
                        self._add_file_to_blob(output, file_path, str(relative_path))

                self.logger.info(f"Repo-blob created at: {output_path}")
                return True

        except Exception as e:
            self.logger.error(f"Error generating repo-blob: {e}")
            return False

    def _add_file_to_blob(self, output, file_path: Path, relative_name: str):
        """Add a single file's content to the blob."""
        try:
            output.write(f"--- START FILE: {relative_name} ---\n")

            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                output.write(content)
                if not content.endswith("\n"):
                    output.write("\n")

            output.write(f"--- END FILE: {relative_name} ---\n\n")

        except Exception as e:
            output.write(f"[Could not read file: {e}]\n")
            output.write(f"--- END FILE: {relative_name} ---\n\n")


def generate_repo_blob(project_root: str, output_path: str) -> bool:
    """
    Convenience function to generate a repo-blob.

    Args:
        project_root: Root directory of the project
        output_path: Where to save the repo-blob file

    Returns:
        True if successful, False otherwise
    """
    generator = RepoBlobGenerator(project_root)
    return generator.generate(output_path)


if __name__ == "__main__":
    # For testing
    import sys

    if len(sys.argv) != 3:
        print("Usage: python repo_blob_generator.py <project_root> <output_file>")
        sys.exit(1)

    project_root = sys.argv[1]
    output_file = sys.argv[2]

    logging.basicConfig(level=logging.INFO)

    if generate_repo_blob(project_root, output_file):
        print(f"✓ Repo-blob generated successfully: {output_file}")
    else:
        print("✗ Failed to generate repo-blob")
        sys.exit(1)

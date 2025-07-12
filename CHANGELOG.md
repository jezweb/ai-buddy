# Changelog

All notable changes to the AI Coding Buddy project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Proactive Error Detection** - Real-time monitoring of coding sessions for automatic error detection
  - Error pattern detection for Python syntax, imports, type errors, security issues
  - Instant notifications for critical errors
  - Contextual fix suggestions for each error type
  - `suggestions` command in chat UI to view active suggestions
  - Smart prioritization of errors by severity
- Comprehensive test suite with pytest framework
- Test fixtures and shared test utilities in conftest.py
- Unit and integration test separation with pytest markers
- Code coverage reporting with pytest-cov
- Development dependencies in requirements-dev.txt
- Black code formatter configuration
- Flake8 linting configuration

### Fixed
- Test collection errors due to fixture imports
- Import errors from missing development dependencies
- Numerous code quality issues identified by flake8:
  - Removed unused imports across multiple files
  - Fixed bare except statements (now use `except Exception`)
  - Fixed f-strings without placeholders
  - Corrected undefined variable usage in monitoring_agent.py
- Typo in idea.md (parser.add_gument → parser.add_argument)

### Changed
- Improved code formatting consistency with Black
- Enhanced error handling with specific exception types
- Cleaned up import statements to remove unused dependencies

## [1.0.0] - 2025-01-12

### Added
- Initial implementation of AI Coding Buddy
- Core components:
  - `monitoring_agent.py` - Monitors Claude sessions and handles Gemini API interactions
  - `buddy_chat_ui.py` - Interactive chat interface for users
  - `conversation_manager.py` - Manages conversation history and context
  - `session_manager.py` - Handles session lifecycle and cleanup
  - `file_operations.py` - Enables Gemini to suggest file operations
  - `smart_context.py` - Intelligent context selection for large projects
  - `repo_blob_generator.py` - Creates project context files
- Claude Code integration hooks for real-time change tracking
- Setup and installation scripts
- Comprehensive documentation in README.md
- Session persistence and recovery
- File operation capabilities with safety checks
- Smart context management for efficient token usage
- Multi-platform support (macOS and Linux)

### Features
- Real-time monitoring of Claude coding sessions
- Interactive chat with Gemini for coding advice
- Automatic project context generation
- Session management with cleanup
- File operation suggestions and execution
- Change tracking integration with Claude hooks
- Configurable via environment variables
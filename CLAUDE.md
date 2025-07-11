# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AI Coding Buddy** - A prototype system that creates a collaborative coding environment with two AI assistants:
- Primary AI (Claude) for active coding
- Observer AI (Gemini) for contextual advice and guidance

## Current Status

This project is in the **planning phase**. The repository contains a detailed specification (`idea.md`) but no implementation yet. The project should be built following the phased approach outlined in `idea.md`.

## Architecture

The system consists of three main components:
1. **Launcher** (`start-buddy-session.sh`) - Orchestrates the environment setup
2. **Monitoring Agent** (`monitoring_agent.py`) - Manages Gemini API interactions
3. **Buddy Chat UI** (`buddy_chat_ui.py`) - User interface for interacting with Gemini

Communication between components uses file-based IPC with temporary files in the `sessions/` directory.

## Development Commands

Since the project hasn't been implemented yet, here are the planned commands:

```bash
# Install dependencies (once implemented)
pip install -r requirements.txt

# Start a buddy session (main entry point)
./start-buddy-session.sh

# Run the monitoring agent manually (for testing)
python3 monitoring_agent.py --context_file <path> --log_file <path>

# Run the chat UI manually (for testing)
python3 buddy_chat_ui.py
```

## Updated Gemini API Usage

When implementing, use the new Google GenAI SDK pattern:

```python
from google import genai

# Initialize client
client = genai.Client(api_key='GEMINI_API_KEY')

# Generate content with latest models
response = client.models.generate_content(
    model='gemini-2.5-flash',  # or 'gemini-2.0-flash-001'
    contents='Your prompt here'
)
```

Note: The old `google-generativeai` package is deprecated. The file upload/deletion API will need to be updated to match the new SDK's approach.

## Implementation Guidelines

When implementing this project:

1. **Follow the phased approach** from `idea.md`:
   - Phase 1: Setup files (README.md, .gitignore, requirements.txt, config.py)
   - Phase 2: The orchestrator (start-buddy-session.sh)
   - Phase 3: Core components (monitoring_agent.py, buddy_chat_ui.py)

2. **Key Technical Details**:
   - Python 3.x with `google-genai` library (new unified SDK)
   - File-based IPC using temporary files in `sessions/` directory
   - Session recording via Unix `script` command
   - API key management through `.env` file

3. **Important Considerations**:
   - The `sessions/` directory should be git-ignored (contains logs)
   - Platform-specific terminal commands in the launcher (macOS vs Linux)
   - Error handling for API failures and file operations
   - Proper cleanup of temporary files and Gemini uploaded files

4. **Testing Approach**:
   - Unit tests for individual Python components
   - Integration tests for file-based communication
   - Manual testing of the full workflow

## File Structure (Planned)

```
gemini-coding-budding/
├── README.md                 # Project documentation
├── .gitignore               # Version control exclusions
├── requirements.txt         # Python dependencies
├── config.py               # API key configuration
├── start-buddy-session.sh   # Main entry point script
├── monitoring_agent.py      # Gemini API interaction service
├── buddy_chat_ui.py        # User chat interface
├── .env                    # API keys (git-ignored)
└── sessions/               # Runtime logs and temp files (git-ignored)
```

## Known Issues in Specification

When implementing, be aware of these issues in `idea.md` that need updating:
- Line 304: `parser.add_gument` should be `parser.add_argument`
- The launcher script uses macOS-specific `osascript` commands - will need adaptation for Linux
- **API Updates Required**:
  - Replace deprecated `google-generativeai` with new `google-genai` SDK
  - Update imports from `import google.generativeai as genai` to `from google import genai`
  - Replace model name `gemini-1.5-pro-latest` with current models like `gemini-2.5-flash` or `gemini-2.0-flash-001`
  - Update API initialization to use new client pattern: `client = genai.Client(api_key='GEMINI_API_KEY')`
  - File upload API has changed - check current docs for proper implementation
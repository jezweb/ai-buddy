# AI Coding Buddy Prototype

This project is a prototype for an AI-powered coding assistant. It allows a developer to work with a primary coding AI (like Claude's CLI) while a secondary, "senior" AI (Google's Gemini) observes the entire project's source code and the live coding session. The developer can then ask the senior AI for high-level advice, bug fixes, and architectural guidance.

## Architecture Overview

The system consists of three main components that work together:

1.  **The Launcher (`start-buddy-session.sh`):** A shell script that initializes the entire environment. It creates a "repo mix" of the project's source code, starts the monitoring agent in the background, and launches both the user's chat UI and the recorded Claude session.
2.  **The Monitoring Agent (`monitoring_agent.py`):** The brains of the operation. This Python script runs in the background, watching the live session log. When prompted by the user, it sends the entire project code and the session log to the Gemini API and returns the AI's response.
3.  **The Buddy Chat UI (`buddy_chat_ui.py`):** A simple, dedicated terminal interface where the developer interacts with the "senior dev" (Gemini).

### How Gemini Sees Your Code

When you start AI Buddy, it creates a "repo mix" - a single file containing ALL your project's source code. This means Gemini has complete visibility into:
- Every source file in your project
- Your entire Claude session history
- Real-time changes (if hooks are enabled)

This comprehensive context is why Gemini can provide such informed advice about your project!

### Text-Based Architecture Diagram

```
+-------------+      +--------------------------+      +--------------------+
| Your        |----->|   start-buddy-session.sh |----->|                    |
| Terminal    |      |      (The Launcher)      |      |   Claude CLI in    |
+-------------+      +--------------------------+      |   Recorded Session |
                             |          |              +--------------------+
                             |          |                    |
                             |          `--------------------. (creates claude_session.log)
                             |                               |
                             v (starts in background)        v (watches file)
                      +----------------------+      +--------------------+
                      |   buddy_chat_ui.py   |<---->| monitoring_agent.py|
                      | (Your chat with AI)  |      |  (Manages Gemini)  |
                      +----------------------+      +--------------------+
                                                             |
                                                             v (sends files & prompt)
                                                       +-------------+
                                                       | Gemini API  |
                                                       +-------------+
```

## Prerequisites

- Python 3.7+
- Git (for tracking files in the repo mix)
- A Google Gemini API key
- Claude CLI (or any terminal-based coding session you want to record)

## Installation

AI Coding Buddy is designed to work from a `.ai-buddy` subfolder within your project, keeping it separate from your project's code and avoiding conflicts with existing `.env` files.

### Quick Setup (Recommended)

1. Navigate to your project directory:
   ```bash
   cd /path/to/your/project
   ```

2. Clone and setup AI Buddy:
   ```bash
   git clone https://github.com/jezweb/ai-buddy .ai-buddy
   ./.ai-buddy/full-setup.sh
   ```

That's it! The full setup script will:
- Check Python installation
- Install dependencies (optionally in a virtual environment)
- Configure your API key
- Set up all permissions
- Optionally install Claude Code hooks for enhanced tracking

### Manual Setup

If you prefer to set up manually:

1. Navigate to your project directory:
   ```bash
   cd /path/to/your/project
   ```

2. Clone AI Buddy into a subfolder:
   ```bash
   git clone https://github.com/jezweb/ai-buddy .ai-buddy
   ```

3. Install Python dependencies:
   ```bash
   pip install -r .ai-buddy/requirements.txt
   ```

4. Set up your API key:
   ```bash
   cp .ai-buddy/.env.example .ai-buddy/.env
   # Edit .ai-buddy/.env and add your GEMINI_API_KEY
   ```

5. Make the launcher script executable:
   ```bash
   chmod +x .ai-buddy/start-buddy-session.sh
   ```

## Usage

1.  Navigate to your project directory in the terminal.
2.  Run `./.ai-buddy/start-buddy-session.sh`.
3.  The script generates a `project_context.txt` file (our "repo mix").
4.  Two new terminal windows/tabs open: one for your interactive Claude session and one for the "Buddy Chat".
5.  You work in the Claude window. Everything you and Claude do is saved to `sessions/claude_session.log`.
6.  When you need advice, you switch to the Buddy Chat window, type your question, and hit Enter.
7.  The `monitoring_agent.py` sends your project code, the session log, and your question to Gemini.
8.  Gemini's response appears in your Buddy Chat window.

## Project Structure

When installed in your project, the structure looks like:

```
your-project/
├── your-files...           # Your existing project files
└── .ai-buddy/             # AI Buddy subfolder
    ├── start-buddy-session.sh   # Main entry point script
    ├── monitoring_agent.py      # Gemini API interaction service
    ├── buddy_chat_ui.py        # User chat interface
    ├── config.py               # API key configuration
    ├── requirements.txt        # Python dependencies
    ├── .env.example           # Example configuration
    ├── .env                   # Your API keys (create from .env.example)
    └── sessions/              # Runtime logs and temp files (auto-created)
```

## Configuration

The system uses environment variables for configuration. Copy `.ai-buddy/.env.example` to `.ai-buddy/.env` and set:

- `GEMINI_API_KEY`: Your Google Gemini API key
- `AI_BUDDY_TIMEOUT`: Response timeout in seconds (default: 60). Increase for complex requests
  ```bash
  export AI_BUDDY_TIMEOUT=120  # Wait up to 2 minutes for responses
  ```

### Claude Code Integration (Optional but Recommended)

AI Buddy can integrate with Claude Code hooks to track file changes in real-time. This gives Gemini perfect visibility into what Claude is modifying.

To enable change tracking:

1. Run the hook installer:
   ```bash
   ./.ai-buddy/install-hooks.sh
   ```

2. Restart Claude Code for the hooks to take effect

3. In the Buddy Chat UI, use the `changes` command to view recent file modifications

The hooks will track:
- File edits and creations
- Git operations
- Command executions
- Session checkpoints

This provides much better context to Gemini about what's happening in your coding session!

## Platform Support

- **macOS**: Fully supported with Terminal.app integration
- **Linux**: Supported with automatic detection of terminal emulator (gnome-terminal, konsole, xterm)
- **Windows**: Requires WSL or manual adaptation of the launcher script

## Security Notes

- The `.env` file containing your API key is excluded from version control
- Session logs in the `sessions/` directory may contain sensitive information and are also excluded
- Never commit API keys or session data to your repository

## Future Improvements

*   **Visual Input:** Integrate a library like Playwright to capture screenshots or web output, allowing Gemini to "see" the front-end of a web app.
*   **Automated Triggers:** Allow the monitoring agent to proactively offer advice when it detects common errors (e.g., Python exceptions, HTTP 500 errors) in the session log.
*   ~~**VCS Integration:** Automatically update the project context file when a `git commit` is made.~~ ✅ Implemented via Claude hooks!
*   **Enhanced IPC:** Replace file-based communication with sockets or message queues for better performance and reliability.

## Troubleshooting

- **"GEMINI_API_KEY not found" error**: Make sure you've created a `.env` file with your API key
- **Terminal windows don't open**: Check that the launcher script has execute permissions and your terminal emulator is supported
- **No response from Gemini**: Verify your API key is valid and you have internet connectivity

## License

This is a prototype project. Feel free to modify and adapt it for your needs.
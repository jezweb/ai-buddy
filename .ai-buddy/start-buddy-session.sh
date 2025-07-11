#!/bin/bash

echo "🚀 Starting AI Coding Buddy Session..."

# --- Get AI Buddy directory and project root ---
AI_BUDDY_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$AI_BUDDY_DIR/.." && pwd)"

# --- Configuration ---
SESSION_ID=$(date +%Y%m%d_%H%M%S)
SESSIONS_DIR="${SESSIONS_DIR:-$AI_BUDDY_DIR/sessions}"
CONTEXT_FILE="$SESSIONS_DIR/project_context_${SESSION_ID}.txt"
CLAUDE_LOG_FILE="$SESSIONS_DIR/claude_session_${SESSION_ID}.log"

# --- Setup ---
mkdir -p "$SESSIONS_DIR"

# --- Function to detect OS and terminal ---
detect_platform() {
    case "$(uname -s)" in
        Darwin*)
            echo "macos"
            ;;
        Linux*)
            echo "linux"
            ;;
        *)
            echo "unsupported"
            ;;
    esac
}

# --- Function to find available terminal emulator on Linux ---
find_linux_terminal() {
    # Try to find an available terminal emulator
    if command -v gnome-terminal &> /dev/null; then
        echo "gnome-terminal"
    elif command -v konsole &> /dev/null; then
        echo "konsole"
    elif command -v xfce4-terminal &> /dev/null; then
        echo "xfce4-terminal"
    elif command -v xterm &> /dev/null; then
        echo "xterm"
    else
        echo "none"
    fi
}

# --- Function to Create "Repo Mix" ---
create_repo_mix() {
    echo "  -> Generating 'repo mix' from project files..."
    echo "  -> Project root: $PROJECT_ROOT"
    
    # Clear the file if it exists
    > "$CONTEXT_FILE"
    
    # Add project metadata
    echo "=== PROJECT: $(basename "$PROJECT_ROOT") ===" >> "$CONTEXT_FILE"
    echo "=== Generated: $(date) ===" >> "$CONTEXT_FILE"
    echo "=== Root: $PROJECT_ROOT ===" >> "$CONTEXT_FILE"
    echo "" >> "$CONTEXT_FILE"
    
    # Change to project root for scanning
    cd "$PROJECT_ROOT"
    
    # Check if git is initialized
    if [ -d .git ]; then
        # Use git to list all tracked files, respecting .gitignore
        git ls-files | while read -r file; do
            # Skip AI Buddy files, session files, and binary files
            if [[ "$file" == .ai-buddy/* || "$file" == *.pyc || "$file" == .env* ]]; then
                continue
            fi
            
            # Check if file is text (not binary)
            if file "$file" | grep -q "text"; then
                echo "--- START FILE: $file ---" >> "$CONTEXT_FILE"
                cat "$file" >> "$CONTEXT_FILE" 2>/dev/null || echo "[Could not read file]" >> "$CONTEXT_FILE"
                echo -e "\n--- END FILE: $file ---\n" >> "$CONTEXT_FILE"
            fi
        done
    else
        # If no git, include Python files and other text files
        echo "  -> No git repository found. Including Python and text files..."
        find . -type f \( -name "*.py" -o -name "*.txt" -o -name "*.md" -o -name "*.sh" \) \
            -not -path "./.ai-buddy/*" -not -path "./.git/*" -not -path "./__pycache__/*" \
            -not -name ".env*" 2>/dev/null | while read -r file; do
            echo "--- START FILE: $file ---" >> "$CONTEXT_FILE"
            cat "$file" >> "$CONTEXT_FILE" 2>/dev/null || echo "[Could not read file]" >> "$CONTEXT_FILE"
            echo -e "\n--- END FILE: $file ---\n" >> "$CONTEXT_FILE"
        done
    fi
    
    echo "  -> 'Repo mix' created at $CONTEXT_FILE"
}

# --- Function to open terminal based on platform ---
open_terminal() {
    local command="$1"
    local title="$2"
    local working_dir="$3"
    local platform=$(detect_platform)
    
    case "$platform" in
        macos)
            # Use AppleScript to open Terminal.app
            osascript -e "tell app \"Terminal\" to do script \"cd '$working_dir'; $command\""
            ;;
        linux)
            local terminal=$(find_linux_terminal)
            case "$terminal" in
                gnome-terminal)
                    gnome-terminal --working-directory="$working_dir" --title="$title" -- bash -c "$command; exec bash"
                    ;;
                konsole)
                    konsole --workdir "$working_dir" --title "$title" -e bash -c "$command; exec bash"
                    ;;
                xfce4-terminal)
                    xfce4-terminal --working-directory="$working_dir" --title="$title" -e "bash -c '$command; exec bash'"
                    ;;
                xterm)
                    xterm -title "$title" -e bash -c "cd '$working_dir'; $command; exec bash" &
                    ;;
                none)
                    echo "❌ Error: No supported terminal emulator found!"
                    echo "   Please install one of: gnome-terminal, konsole, xfce4-terminal, or xterm"
                    return 1
                    ;;
            esac
            ;;
        *)
            echo "❌ Error: Unsupported platform. This script works on macOS and Linux only."
            return 1
            ;;
    esac
}

# --- Main Execution ---

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed. Please install Python 3.7+ first."
    exit 1
fi

# Check if required Python packages are installed
python3 -c "import google.genai" 2>/dev/null || {
    echo "❌ Error: Required Python packages not installed."
    echo "   Please run: pip install -r $AI_BUDDY_DIR/requirements.txt"
    exit 1
}

# Create the repo mix
create_repo_mix

echo "  -> Launching Monitoring Agent in the background..."
# Pass the file paths to the agent
cd "$AI_BUDDY_DIR"
python3 monitoring_agent.py --context_file "$CONTEXT_FILE" --log_file "$CLAUDE_LOG_FILE" &
AGENT_PID=$!

# Give the agent a moment to start
sleep 1

# Check if agent started successfully
if ! kill -0 $AGENT_PID 2>/dev/null; then
    echo "❌ Error: Monitoring agent failed to start. Check your configuration."
    exit 1
fi

echo "  -> Opening Buddy Chat UI and Claude Session in new terminals..."

# Open Buddy Chat UI
open_terminal "python3 $AI_BUDDY_DIR/buddy_chat_ui.py" "AI Buddy Chat" "$AI_BUDDY_DIR"

# Open Claude session with script recording
# Check which claude command is available
if command -v claude &> /dev/null; then
    CLAUDE_CMD="claude"
elif command -v claude-cli &> /dev/null; then
    CLAUDE_CMD="claude-cli"
else
    echo "⚠️  Warning: Claude CLI not found. Opening a regular shell instead."
    echo "   Install Claude CLI from: https://claude.ai/cli"
    CLAUDE_CMD="bash"
fi

open_terminal "script -q '$CLAUDE_LOG_FILE' $CLAUDE_CMD" "Claude Coding Session" "$PROJECT_ROOT"

echo ""
echo "✅ Session is live!"
echo "   - Work in the 'Claude Coding Session' window"
echo "   - Ask questions in the 'AI Buddy Chat' window"
echo "   - Session ID: $SESSION_ID"
echo "   - Press Ctrl+C here to stop the monitoring agent"
echo ""

# Trap to clean up on exit
trap "echo ''; echo '🛑 Shutting down...'; kill $AGENT_PID 2>/dev/null; echo '👋 Session ended.'" EXIT

# Wait for the agent to be terminated
wait $AGENT_PID
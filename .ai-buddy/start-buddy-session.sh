#!/bin/bash

echo "🚀 Starting AI Coding Buddy Session..."

# --- Get AI Buddy directory and project root ---
# This script can be run from either:
# 1. Project root: ./.ai-buddy/start-buddy-session.sh
# 2. Inside .ai-buddy: ./start-buddy-session.sh

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRIPT_NAME="$(basename "$SCRIPT_DIR")"

# Determine AI_BUDDY_DIR and PROJECT_ROOT based on where we're running from
if [ "$SCRIPT_NAME" = ".ai-buddy" ]; then
    # Running from project root (case 1)
    AI_BUDDY_DIR="$SCRIPT_DIR"
    PROJECT_ROOT="$(cd "$AI_BUDDY_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/../.ai-buddy/start-buddy-session.sh" ]; then
    # We're inside .ai-buddy but there's another .ai-buddy above us
    # This handles nested or unusual structures
    AI_BUDDY_DIR="$SCRIPT_DIR"
    PROJECT_ROOT="$(cd "$AI_BUDDY_DIR/.." && pwd)"
else
    # Running from inside .ai-buddy (case 2)
    # Look for project root by finding where .ai-buddy lives
    CURRENT_DIR="$SCRIPT_DIR"
    while [ "$CURRENT_DIR" != "/" ]; do
        if [ "$(basename "$CURRENT_DIR")" = ".ai-buddy" ] && [ -f "$CURRENT_DIR/start-buddy-session.sh" ]; then
            AI_BUDDY_DIR="$CURRENT_DIR"
            PROJECT_ROOT="$(cd "$CURRENT_DIR/.." && pwd)"
            break
        fi
        CURRENT_DIR="$(cd "$CURRENT_DIR/.." && pwd)"
    done
    
    # Fallback if we couldn't find .ai-buddy
    if [ -z "$AI_BUDDY_DIR" ]; then
        AI_BUDDY_DIR="$SCRIPT_DIR"
        PROJECT_ROOT="$(cd "$AI_BUDDY_DIR/.." && pwd)"
    fi
fi

# --- Validate project root ---
# Ensure we're not in system directories or trash
if [[ "$PROJECT_ROOT" == "/home/"* ]] && [[ "$PROJECT_ROOT" == *"/.local/share/Trash/"* ]]; then
    echo "❌ Error: Detected project root in Trash folder: $PROJECT_ROOT"
    echo "   Please run this script from your actual project directory:"
    echo "   cd /path/to/your/project && ./.ai-buddy/start-buddy-session.sh"
    exit 1
fi

if [[ "$PROJECT_ROOT" == "/" ]] || [[ "$PROJECT_ROOT" == "/home" ]] || [[ "$PROJECT_ROOT" == "/usr" ]] || [[ "$PROJECT_ROOT" == "/etc" ]]; then
    echo "❌ Error: Invalid project root detected: $PROJECT_ROOT"
    echo "   Please run this script from your actual project directory:"
    echo "   cd /path/to/your/project && ./.ai-buddy/start-buddy-session.sh"
    exit 1
fi

# Debug output
echo "  -> AI Buddy directory: $AI_BUDDY_DIR"
echo "  -> Project root: $PROJECT_ROOT"

# --- Check and activate virtual environment if it exists ---
VENV_DIR="$AI_BUDDY_DIR/venv"
PYTHON_CMD="python3"

if [ -d "$VENV_DIR" ]; then
    echo "  -> Using virtual environment..."
    if [ -f "$VENV_DIR/bin/python" ]; then
        # Linux/macOS
        PYTHON_CMD="$VENV_DIR/bin/python"
    elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        # Windows
        PYTHON_CMD="$VENV_DIR/Scripts/python.exe"
    fi
fi

# --- Configuration ---
# Check for --resume flag
RESUME_MODE=false
RESUME_SESSION_ID=""
for arg in "$@"; do
    case $arg in
        --resume)
            RESUME_MODE=true
            shift
            ;;
        --resume=*)
            RESUME_MODE=true
            RESUME_SESSION_ID="${arg#*=}"
            shift
            ;;
        *)
            ;;
    esac
done

if [ "$RESUME_MODE" = true ]; then
    # Resume mode - list sessions and let user choose
    echo "  -> Resume mode activated"
    
    # Run Python script to list sessions
    if [ -z "$RESUME_SESSION_ID" ]; then
        echo "  -> Listing available sessions..."
        SESSION_INFO=$($PYTHON_CMD -c "
import sys
sys.path.append('$AI_BUDDY_DIR')
from session_manager import SessionManager
mgr = SessionManager('$AI_BUDDY_DIR/sessions')
print(mgr.format_session_list())
print()
sessions = mgr.list_recent_sessions()
if sessions:
    print('Enter session number to resume (or press Enter for new session): ', end='')
" 2>/dev/null)
        
        if [ $? -eq 0 ]; then
            echo "$SESSION_INFO"
            read -r SESSION_CHOICE
            
            if [ ! -z "$SESSION_CHOICE" ] && [ "$SESSION_CHOICE" -eq "$SESSION_CHOICE" ] 2>/dev/null; then
                # Get session ID from choice
                RESUME_SESSION_ID=$($PYTHON_CMD -c "
import sys
sys.path.append('$AI_BUDDY_DIR')
from session_manager import SessionManager
mgr = SessionManager('$AI_BUDDY_DIR/sessions')
sessions = mgr.list_recent_sessions()
if len(sessions) >= $SESSION_CHOICE > 0:
    print(sessions[$SESSION_CHOICE - 1]['id'])
" 2>/dev/null)
            fi
        fi
    fi
    
    if [ ! -z "$RESUME_SESSION_ID" ]; then
        SESSION_ID="$RESUME_SESSION_ID"
        echo "  -> Resuming session: $SESSION_ID"
    else
        echo "  -> Creating new session instead"
        SESSION_ID=$(date +%Y%m%d_%H%M%S)
    fi
else
    SESSION_ID=$(date +%Y%m%d_%H%M%S)
fi

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
$PYTHON_CMD -c "import google.genai" 2>/dev/null || {
    echo "❌ Error: Required Python packages not installed."
    echo "   Please run: $PYTHON_CMD -m pip install -r $AI_BUDDY_DIR/requirements.txt"
    exit 1
}

# Create the repo mix (skip if resuming and context already exists)
if [ "$RESUME_MODE" = true ] && [ -f "$CONTEXT_FILE" ]; then
    echo "  -> Using existing project context from resumed session"
else
    create_repo_mix
fi

# Register session with session manager
$PYTHON_CMD -c "
import sys
sys.path.append('$AI_BUDDY_DIR')
from session_manager import SessionManager
mgr = SessionManager('$AI_BUDDY_DIR/sessions')
if '$RESUME_MODE' == 'true':
    mgr.update_session_access('$SESSION_ID')
else:
    mgr.create_session('$SESSION_ID', '$PROJECT_ROOT')
" 2>/dev/null

echo "  -> Launching Monitoring Agent in the background..."
# Pass the file paths to the agent
cd "$AI_BUDDY_DIR"
$PYTHON_CMD monitoring_agent.py --context_file "$CONTEXT_FILE" --log_file "$CLAUDE_LOG_FILE" &
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
# Pass session ID to chat UI
export AI_BUDDY_SESSION_ID="$SESSION_ID"
open_terminal "AI_BUDDY_SESSION_ID=$SESSION_ID $PYTHON_CMD $AI_BUDDY_DIR/buddy_chat_ui.py" "AI Buddy Chat" "$AI_BUDDY_DIR"

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
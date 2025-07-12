#!/bin/bash

# AI Buddy Hook Script for Claude Code Integration
# This script is called by Claude Code hooks to track changes in real-time
# It receives JSON data about Claude's actions via stdin

# Get the event type from command line argument
EVENT_TYPE="$1"

# Read JSON input from stdin
json=$(cat)

# Get session directory from environment or use default
SESSIONS_DIR="${AI_BUDDY_SESSIONS_DIR:-$(dirname "$0")/sessions}"
CHANGES_LOG="$SESSIONS_DIR/changes.log"

# Create sessions directory if it doesn't exist
mkdir -p "$SESSIONS_DIR"

# Helper function to log with timestamp
log_change() {
    local change_type="$1"
    local details="$2"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $change_type: $details" >> "$CHANGES_LOG"
}

# Extract common fields
tool_name=$(echo "$json" | jq -r '.tool_name // empty')
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Handle different event types
case "$EVENT_TYPE" in
    "PostToolUse")
        # Log successful tool uses
        case "$tool_name" in
            "Edit"|"MultiEdit")
                file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
                if [ -n "$file_path" ]; then
                    log_change "FILE_EDITED" "$file_path"
                    # Also track the specific changes if available
                    old_string=$(echo "$json" | jq -r '.tool_input.old_string // empty' | head -1)
                    if [ -n "$old_string" ] && [ "$old_string" != "null" ]; then
                        log_change "EDIT_DETAIL" "Modified content in $file_path"
                    fi
                fi
                ;;
            
            "Write")
                file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
                if [ -n "$file_path" ]; then
                    # Check if file exists to determine if it's new
                    if [ -f "$file_path" ]; then
                        log_change "FILE_OVERWRITTEN" "$file_path"
                    else
                        log_change "FILE_CREATED" "$file_path"
                    fi
                fi
                ;;
            
            "Bash")
                command=$(echo "$json" | jq -r '.tool_input.command // empty')
                if [ -n "$command" ]; then
                    # Log git commands specially
                    if [[ "$command" == git* ]]; then
                        log_change "GIT_COMMAND" "$command"
                        
                        # Special handling for commits
                        if [[ "$command" == *"git commit"* ]]; then
                            log_change "GIT_COMMIT" "New commit created"
                        fi
                    elif [[ "$command" == *"rm "* ]] || [[ "$command" == *"mv "* ]]; then
                        log_change "FILE_OPERATION" "$command"
                    fi
                fi
                ;;
            
            "Read")
                file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
                if [ -n "$file_path" ]; then
                    log_change "FILE_READ" "$file_path"
                fi
                ;;
        esac
        ;;
    
    "PreToolUse")
        # Log what Claude is about to do (useful for debugging)
        case "$tool_name" in
            "Edit"|"Write"|"MultiEdit")
                file_path=$(echo "$json" | jq -r '.tool_input.file_path // empty')
                if [ -n "$file_path" ]; then
                    log_change "PLANNED_EDIT" "$file_path (tool: $tool_name)"
                fi
                ;;
        esac
        ;;
    
    "Stop")
        # Claude finished responding - good time to capture state
        log_change "SESSION_CHECKPOINT" "Claude finished current response"
        
        # Run git status to capture current state
        if command -v git &> /dev/null && [ -d .git ]; then
            git_status=$(git status --porcelain 2>/dev/null | head -10)
            if [ -n "$git_status" ]; then
                log_change "GIT_STATUS" "$(echo "$git_status" | tr '\n' ';')"
            fi
        fi
        ;;
    
    "Notification")
        # Log when Claude is waiting for permission
        notification_type=$(echo "$json" | jq -r '.notification_type // empty')
        if [ -n "$notification_type" ]; then
            log_change "NOTIFICATION" "$notification_type"
        fi
        ;;
esac

# Always exit successfully to avoid blocking Claude
exit 0
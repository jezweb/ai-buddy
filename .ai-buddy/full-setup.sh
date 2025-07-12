#!/bin/bash

# AI Coding Buddy Full Setup Script
# This script runs both basic setup and optionally configures Claude hooks

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║     🚀 AI CODING BUDDY FULL SETUP 🚀     ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}This script will:${NC}"
echo -e "  1. Install Python dependencies (including enhanced UI)"
echo -e "  2. Configure your Gemini API key"
echo -e "  3. Optionally set up Claude Code integration"
echo ""
echo -e "${GREEN}New features included:${NC}"
echo -e "  • Session persistence & resumption"
echo -e "  • Conversation memory"
echo -e "  • Rich terminal interface with auto-completion"
echo -e "  • Better file handling for large projects"
echo ""

# Step 1: Run basic setup
echo -e "${YELLOW}Step 1: Running basic setup...${NC}"
echo -e "${YELLOW}═══════════════════════════════${NC}"
"$SCRIPT_DIR/setup.sh"

# Check if setup was successful
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Basic setup failed. Please fix any errors and try again.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Basic setup completed successfully!${NC}"
echo ""

# Step 2: Ask about Claude hooks
echo -e "${YELLOW}Step 2: Claude Code Integration (Optional)${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Claude Code hooks provide:${NC}"
echo -e "  • Real-time tracking of file changes"
echo -e "  • Git operation awareness"
echo -e "  • Better context for Gemini's responses"
echo ""
read -p "Would you like to install Claude Code hooks? [Y/n] " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    echo -e "${YELLOW}Installing Claude Code hooks...${NC}"
    
    # Check if install-hooks.sh exists
    if [ -f "$SCRIPT_DIR/install-hooks.sh" ]; then
        "$SCRIPT_DIR/install-hooks.sh"
        
        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}✅ Claude Code hooks installed successfully!${NC}"
            HOOKS_INSTALLED=true
        else
            echo -e "${YELLOW}⚠️  Hook installation encountered issues. You can try again later with:${NC}"
            echo -e "   ${CYAN}./.ai-buddy/install-hooks.sh${NC}"
            HOOKS_INSTALLED=false
        fi
    else
        echo -e "${RED}❌ install-hooks.sh not found!${NC}"
        HOOKS_INSTALLED=false
    fi
else
    echo -e "${YELLOW}Skipping Claude Code hooks installation.${NC}"
    echo -e "You can install them later with: ${CYAN}./.ai-buddy/install-hooks.sh${NC}"
    HOOKS_INSTALLED=false
fi

# Final summary
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║          ✨ SETUP COMPLETE! ✨           ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}What's been configured:${NC}"
echo -e "  ✓ Python dependencies installed"
echo -e "  ✓ Gemini API key configured"

if [ "$HOOKS_INSTALLED" = true ]; then
    echo -e "  ✓ Claude Code hooks installed"
else
    echo -e "  ○ Claude Code hooks (not installed)"
fi

echo ""
echo -e "${BLUE}How AI Buddy works:${NC}"
echo -e "  1. Creates a 'repo mix' with ALL your project files"
echo -e "  2. Records your Claude session in real-time"
echo -e "  3. Sends both to Gemini when you ask questions"
echo -e "  4. Gemini sees your ENTIRE codebase + session history!"

echo ""
echo -e "${BLUE}New commands available:${NC}"
echo -e "  • ${CYAN}history${NC} - View conversation history"
echo -e "  • ${CYAN}--resume${NC} - Resume previous sessions"
echo -e "  • Tab completion for commands"
echo -e "  • Arrow keys for command history"

if [ "$HOOKS_INSTALLED" = true ]; then
    echo ""
    echo -e "${YELLOW}⚠️  IMPORTANT: Restart Claude Code for hooks to take effect!${NC}"
fi

echo ""
echo -e "${GREEN}Ready to start coding?${NC}"
echo ""

# Check if there are existing sessions
SESSIONS_EXIST=false
if [ -d "$SCRIPT_DIR/sessions" ] && [ -f "$SCRIPT_DIR/sessions/session_index.json" ]; then
    SESSION_COUNT=$(python3 -c "
import json
try:
    with open('$SCRIPT_DIR/sessions/session_index.json', 'r') as f:
        data = json.load(f)
        print(len(data.get('sessions', [])))
except:
    print(0)
" 2>/dev/null)
    
    if [ "$SESSION_COUNT" -gt 0 ] 2>/dev/null; then
        SESSIONS_EXIST=true
    fi
fi

if [ "$SESSIONS_EXIST" = true ]; then
    echo -e "${BLUE}Found $SESSION_COUNT existing session(s).${NC}"
    echo ""
    echo "What would you like to do?"
    echo "  1) Resume a previous session"
    echo "  2) Start a new session"
    echo "  3) Exit"
    echo ""
    read -p "Enter your choice (1-3): " CHOICE
    
    case $CHOICE in
        1)
            echo ""
            echo -e "${CYAN}Launching AI Buddy in resume mode...${NC}"
            exec "$SCRIPT_DIR/start-buddy-session.sh" --resume
            ;;
        2)
            echo ""
            echo -e "${CYAN}Starting new AI Buddy session...${NC}"
            exec "$SCRIPT_DIR/start-buddy-session.sh"
            ;;
        *)
            echo ""
            echo -e "${GREEN}To start AI Buddy later:${NC}"
            echo -e "  New session: ${CYAN}./.ai-buddy/start-buddy-session.sh${NC}"
            echo -e "  Resume session: ${CYAN}./.ai-buddy/start-buddy-session.sh --resume${NC}"
            echo ""
            echo -e "${BLUE}Happy coding with your AI buddy! 🤖${NC}"
            echo ""
            ;;
    esac
else
    # No existing sessions, simple yes/no prompt
    read -p "Would you like to start AI Coding Buddy now? [Y/n] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        echo -e "${CYAN}Starting AI Coding Buddy...${NC}"
        exec "$SCRIPT_DIR/start-buddy-session.sh"
    else
        echo ""
        echo -e "${GREEN}To start AI Buddy later:${NC}"
        echo -e "  ${CYAN}./.ai-buddy/start-buddy-session.sh${NC}"
        echo ""
        echo -e "${BLUE}Happy coding with your AI buddy! 🤖${NC}"
        echo ""
    fi
fi
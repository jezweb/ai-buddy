#!/bin/bash

# AI Coding Buddy Setup Script
# This script automates the installation and configuration process

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
# This script can be run from either:
# 1. Project root: ./.ai-buddy/setup.sh
# 2. Inside .ai-buddy: ./setup.sh

CURRENT_SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CURRENT_SCRIPT_NAME="$(basename "$CURRENT_SCRIPT_DIR")"

# Determine SCRIPT_DIR (the .ai-buddy directory) based on where we're running from
if [ "$CURRENT_SCRIPT_NAME" = ".ai-buddy" ]; then
    # Running from project root (case 1)
    SCRIPT_DIR="$CURRENT_SCRIPT_DIR"
elif [ -f "$CURRENT_SCRIPT_DIR/setup.sh" ] && [ -f "$CURRENT_SCRIPT_DIR/start-buddy-session.sh" ]; then
    # We're already in .ai-buddy (case 2)
    SCRIPT_DIR="$CURRENT_SCRIPT_DIR"
else
    # Fallback - try to find .ai-buddy directory
    echo "⚠️  Warning: Could not determine .ai-buddy directory location"
    SCRIPT_DIR="$CURRENT_SCRIPT_DIR"
fi

echo -e "${BLUE}🚀 AI Coding Buddy Setup${NC}"
echo -e "${BLUE}========================${NC}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to get Python command
get_python_cmd() {
    if command_exists python3; then
        echo "python3"
    elif command_exists python; then
        # Check if it's Python 3
        if python --version 2>&1 | grep -q "Python 3"; then
            echo "python"
        else
            echo ""
        fi
    else
        echo ""
    fi
}

# Check for Python
echo -e "${YELLOW}Checking dependencies...${NC}"
PYTHON_CMD=$(get_python_cmd)

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Error: Python 3.7+ is required but not found.${NC}"
    echo "Please install Python 3.7 or higher and try again."
    exit 1
fi

# Check Python version
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo -e "✓ Found Python $PYTHON_VERSION"

# Check for pip
if ! $PYTHON_CMD -m pip --version >/dev/null 2>&1; then
    echo -e "${RED}❌ Error: pip is not installed.${NC}"
    echo "Please install pip and try again."
    exit 1
fi
echo -e "✓ pip is installed"

# Ask about virtual environment
echo ""
read -p "Would you like to use a virtual environment? (recommended) [Y/n] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Nn]$ ]]; then
    USE_VENV=false
else
    USE_VENV=true
fi

# Setup virtual environment if requested
if [ "$USE_VENV" = true ]; then
    VENV_DIR="$SCRIPT_DIR/venv"
    if [ ! -d "$VENV_DIR" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        $PYTHON_CMD -m venv "$VENV_DIR"
    fi
    
    # Use the virtual environment's Python directly
    if [ -f "$VENV_DIR/bin/python" ]; then
        PYTHON_CMD="$VENV_DIR/bin/python"
    elif [ -f "$VENV_DIR/Scripts/python.exe" ]; then
        PYTHON_CMD="$VENV_DIR/Scripts/python.exe"
    else
        echo -e "${RED}❌ Error: Could not find Python in virtual environment.${NC}"
        exit 1
    fi
    echo -e "✓ Virtual environment ready"
fi

# Install dependencies
echo ""
echo -e "${YELLOW}Installing Python dependencies...${NC}"
# Use python -m pip to ensure we're using the right pip
$PYTHON_CMD -m pip install -q -r "$SCRIPT_DIR/requirements.txt"
echo -e "✓ Dependencies installed"

# Setup .env file
echo ""
if [ -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${GREEN}✓ .env file already exists${NC}"
    read -p "Would you like to update your Gemini API key? [y/N] " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        UPDATE_KEY=true
    else
        UPDATE_KEY=false
    fi
else
    echo -e "${YELLOW}Setting up configuration...${NC}"
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    UPDATE_KEY=true
fi

# Handle API key setup
if [ "$UPDATE_KEY" = true ]; then
    echo ""
    echo "To get your Gemini API key, visit: https://makersuite.google.com/app/apikey"
    read -p "Enter your Gemini API key (or press Enter to skip): " API_KEY
    
    if [ ! -z "$API_KEY" ]; then
        # Update .env file with the API key
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            sed -i '' "s/GEMINI_API_KEY=\".*\"/GEMINI_API_KEY=\"$API_KEY\"/" "$SCRIPT_DIR/.env"
        else
            # Linux
            sed -i "s/GEMINI_API_KEY=\".*\"/GEMINI_API_KEY=\"$API_KEY\"/" "$SCRIPT_DIR/.env"
        fi
        echo -e "${GREEN}✓ API key configured${NC}"
    else
        echo -e "${YELLOW}⚠️  Skipped API key configuration. You'll need to edit .ai-buddy/.env manually.${NC}"
    fi
fi

# Ensure .env has all configuration options from .env.example
if [ -f "$SCRIPT_DIR/.env" ]; then
    # Check if .env is missing any configuration options
    if ! grep -q "AI_BUDDY_TIMEOUT" "$SCRIPT_DIR/.env" 2>/dev/null; then
        echo ""
        echo -e "${YELLOW}Updating .env with new configuration options...${NC}"
        
        # Create a temporary file with existing values
        TEMP_ENV="$SCRIPT_DIR/.env.tmp"
        
        # Extract existing values
        EXISTING_API_KEY=$(grep "^GEMINI_API_KEY=" "$SCRIPT_DIR/.env" 2>/dev/null || echo "")
        EXISTING_MODEL=$(grep "^GEMINI_MODEL=" "$SCRIPT_DIR/.env" 2>/dev/null || echo "")
        EXISTING_SESSIONS=$(grep "^SESSIONS_DIR=" "$SCRIPT_DIR/.env" 2>/dev/null || echo "")
        EXISTING_POLLING=$(grep "^POLLING_INTERVAL=" "$SCRIPT_DIR/.env" 2>/dev/null || echo "")
        EXISTING_TIMEOUT=$(grep "^AI_BUDDY_TIMEOUT=" "$SCRIPT_DIR/.env" 2>/dev/null || echo "")
        
        # Copy template
        cp "$SCRIPT_DIR/.env.example" "$TEMP_ENV"
        
        # Restore existing values
        if [ ! -z "$EXISTING_API_KEY" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/^GEMINI_API_KEY=.*/$(echo "$EXISTING_API_KEY" | sed 's/[[\/.*]/\\&/g')/" "$TEMP_ENV"
            else
                sed -i "s/^GEMINI_API_KEY=.*/$(echo "$EXISTING_API_KEY" | sed 's/[[\/.*]/\\&/g')/" "$TEMP_ENV"
            fi
        fi
        
        if [ ! -z "$EXISTING_MODEL" ]; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                sed -i '' "s/^# GEMINI_MODEL=.*/$(echo "$EXISTING_MODEL" | sed 's/[[\/.*]/\\&/g')/" "$TEMP_ENV"
            else
                sed -i "s/^# GEMINI_MODEL=.*/$(echo "$EXISTING_MODEL" | sed 's/[[\/.*]/\\&/g')/" "$TEMP_ENV"
            fi
        fi
        
        # Move temp file to .env
        mv "$TEMP_ENV" "$SCRIPT_DIR/.env"
        echo -e "${GREEN}✓ Configuration file updated with all options${NC}"
    fi
fi

# Make scripts executable
echo ""
echo -e "${YELLOW}Setting up permissions...${NC}"
chmod +x "$SCRIPT_DIR/start-buddy-session.sh"
chmod +x "$SCRIPT_DIR/setup.sh"
echo -e "✓ Scripts are now executable"

# Check if API key is configured
API_KEY_CONFIGURED=true
if [ ! -f "$SCRIPT_DIR/.env" ] || grep -q "your-gemini-api-key-here" "$SCRIPT_DIR/.env" 2>/dev/null; then
    API_KEY_CONFIGURED=false
fi

# Final message
echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""

# Show how to start
echo -e "${BLUE}To start AI Coding Buddy later, just run:${NC}"
echo -e "  ${YELLOW}./.ai-buddy/start-buddy-session.sh${NC}"

if [ "$API_KEY_CONFIGURED" = false ]; then
    echo ""
    echo -e "${YELLOW}⚠️  Remember to add your Gemini API key to .ai-buddy/.env first${NC}"
fi

echo ""
echo -e "${BLUE}Happy coding with your AI buddy! 🤖${NC}"
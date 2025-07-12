#!/bin/bash

# AI Buddy Claude Hooks Installer
# This script sets up Claude Code hooks to track changes in real-time

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔧 AI Buddy Claude Hooks Installer${NC}"
echo -e "${BLUE}===================================${NC}"
echo ""

# Get the AI Buddy directory
AI_BUDDY_DIR="$(cd "$(dirname "$0")" && pwd)"

# Check if Claude settings directory exists
CLAUDE_CONFIG_DIR="$HOME/.claude"
if [ ! -d "$CLAUDE_CONFIG_DIR" ]; then
    echo -e "${YELLOW}Creating Claude configuration directory...${NC}"
    mkdir -p "$CLAUDE_CONFIG_DIR"
fi

# Backup existing settings if they exist
SETTINGS_FILE="$CLAUDE_CONFIG_DIR/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    echo -e "${YELLOW}Backing up existing Claude settings...${NC}"
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%Y%m%d_%H%M%S)"
fi

# Check if hooks are already configured
if [ -f "$SETTINGS_FILE" ] && grep -q "ai-buddy-hook.sh" "$SETTINGS_FILE" 2>/dev/null; then
    echo -e "${GREEN}✓ AI Buddy hooks are already configured in Claude settings${NC}"
    read -p "Would you like to update the configuration? [y/N] " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping configuration update."
        exit 0
    fi
fi

# Create or update the settings file
echo -e "${YELLOW}Configuring Claude hooks...${NC}"

# If settings file exists, we need to merge the hooks
if [ -f "$SETTINGS_FILE" ] && [ -s "$SETTINGS_FILE" ]; then
    # Use jq to merge if available
    if command -v jq &> /dev/null; then
        echo -e "${YELLOW}Merging hooks into existing settings...${NC}"
        
        # Create the hooks configuration with actual path
        cat > /tmp/ai-buddy-hooks.json << EOF
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh PostToolUse"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh PreToolUse"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh Stop"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh Notification"
          }
        ]
      }
    ]
  }
}
EOF
        
        # Merge the configurations
        jq -s '.[0] * .[1]' "$SETTINGS_FILE" /tmp/ai-buddy-hooks.json > "$SETTINGS_FILE.new"
        mv "$SETTINGS_FILE.new" "$SETTINGS_FILE"
        rm /tmp/ai-buddy-hooks.json
    else
        echo -e "${RED}⚠️  Warning: 'jq' is not installed. Manual merge may be required.${NC}"
        echo "Please manually add the hooks configuration to $SETTINGS_FILE"
        echo "Refer to $AI_BUDDY_DIR/claude-settings-example.json for the format"
    fi
else
    # Create new settings file
    cat > "$SETTINGS_FILE" << EOF
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh PostToolUse"
          }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh PreToolUse"
          }
        ]
      }
    ],
    "Stop": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh Stop"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "$AI_BUDDY_DIR/ai-buddy-hook.sh Notification"
          }
        ]
      }
    ]
  }
}
EOF
fi

# Set environment variable for hook script
echo ""
echo -e "${YELLOW}Setting up environment...${NC}"
EXPORT_LINE="export AI_BUDDY_SESSIONS_DIR=\"$AI_BUDDY_DIR/sessions\""

# Add to .bashrc if not already there
if ! grep -q "AI_BUDDY_SESSIONS_DIR" "$HOME/.bashrc" 2>/dev/null; then
    echo "$EXPORT_LINE" >> "$HOME/.bashrc"
    echo -e "${GREEN}✓ Added AI_BUDDY_SESSIONS_DIR to .bashrc${NC}"
fi

# Also add to .zshrc if it exists
if [ -f "$HOME/.zshrc" ] && ! grep -q "AI_BUDDY_SESSIONS_DIR" "$HOME/.zshrc" 2>/dev/null; then
    echo "$EXPORT_LINE" >> "$HOME/.zshrc"
    echo -e "${GREEN}✓ Added AI_BUDDY_SESSIONS_DIR to .zshrc${NC}"
fi

# Verify the setup
echo ""
echo -e "${BLUE}Verification:${NC}"
echo -e "Claude settings file: $SETTINGS_FILE"
echo -e "Hook script: $AI_BUDDY_DIR/ai-buddy-hook.sh"

if [ -f "$SETTINGS_FILE" ] && grep -q "ai-buddy-hook.sh" "$SETTINGS_FILE"; then
    echo -e "${GREEN}✅ AI Buddy hooks successfully configured!${NC}"
else
    echo -e "${RED}❌ Hook configuration may have failed. Please check $SETTINGS_FILE${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "1. Restart Claude Code for the hooks to take effect"
echo -e "2. Run AI Buddy with: ${YELLOW}./.ai-buddy/start-buddy-session.sh${NC}"
echo -e "3. Claude's file changes will be tracked in real-time!"
echo ""
echo -e "${GREEN}🎉 Setup complete!${NC}"
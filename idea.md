Of course. This is the perfect way to approach it. By breaking the project down into well-defined files and phases, we can use Claude's CLI to build this prototype step-by-step.

Here is the complete project plan, structured exactly as you requested. You can prompt me for each file one at a time.

---

### **Project: AI Coding Buddy**

This plan outlines the files and architecture for a prototype "AI Coding Buddy" system. The system allows a developer to work in an interactive session with one AI (Claude) while a second AI (Gemini) observes the entire project context and conversation, acting as a senior developer providing guidance on demand.

---

### **File & Build Plan**

Here is the complete list of files we will create for the prototype. I've broken them down into logical build phases.

**Phase 1: Project Setup & Documentation**
1.  `README.md`
2.  `.gitignore`
3.  `requirements.txt`
4.  `config.py`

**Phase 2: The Orchestrator**
5.  `start-buddy-session.sh`

**Phase 3: The Core AI Components**
6.  `monitoring_agent.py`
7.  `buddy_chat_ui.py`

---

### **Phase 1, File 1: `README.md`**

**(This will be the main documentation for our project)**

```markdown
# AI Coding Buddy Prototype

This project is a prototype for an AI-powered coding assistant. It allows a developer to work with a primary coding AI (like Claude's CLI) while a secondary, "senior" AI (Google's Gemini) observes the entire project's source code and the live coding session. The developer can then ask the senior AI for high-level advice, bug fixes, and architectural guidance.

## Architecture Overview

The system consists of three main components that work together:

1.  **The Launcher (`start-buddy-session.sh`):** A shell script that initializes the entire environment. It creates a "repo mix" of the project's source code, starts the monitoring agent in the background, and launches both the user's chat UI and the recorded Claude session.
2.  **The Monitoring Agent (`monitoring_agent.py`):** The brains of the operation. This Python script runs in the background, watching the live session log. When prompted by the user, it uploads the project code and the session log to the Gemini API and returns the AI's response.
3.  **The Buddy Chat UI (`buddy_chat_ui.py`):** A simple, dedicated terminal interface where the developer interacts with the "senior dev" (Gemini).

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

### Workflow

1.  Navigate to your project directory in the terminal.
2.  Run `./start-buddy-session.sh`.
3.  The script generates a `project_context.txt` file (our "repo mix").
4.  Two new terminal windows/tabs open: one for your interactive Claude session and one for the "Buddy Chat".
5.  You work in the Claude window. Everything you and Claude do is saved to `sessions/claude_session.log`.
6.  When you need advice, you switch to the Buddy Chat window, type your question, and hit Enter.
7.  The `monitoring_agent.py` sends your project code, the session log, and your question to Gemini.
8.  Gemini's response appears in your Buddy Chat window.

### Future Improvements
*   **Visual Input:** Integrate a library like Playwright to capture screenshots or web output, allowing Gemini to "see" the front-end of a web app.
*   **Automated Triggers:** Allow the monitoring agent to proactively offer advice when it detects common errors (e.g., Python exceptions, HTTP 500 errors) in the session log.
*   **VCS Integration:** Automatically update the project context file when a `git commit` is made.

```

---

### **Phase 1, File 2: `.gitignore`**

**Purpose:** To prevent sensitive information and unnecessary files from being checked into version control.

**Content:**
```
# Python
__pycache__/
*.pyc
venv/
*.env

# Session Data (IMPORTANT!)
# These logs can contain sensitive info or be very large.
sessions/

# IDE / OS specific
.vscode/
.idea/
.DS_Store
```

---

### **Phase 1, File 3: `requirements.txt`**

**Purpose:** To list the Python dependencies needed for the project.

**Content:**
```
google-generativeai
python-dotenv
# We might add a file-watcher library later for efficiency, but this is a good start.
```

---

### **Phase 1, File 4: `config.py`**

**Purpose:** A simple way to manage the API key. We'll use a `.env` file in practice, but this is a clear starting point.

**Content:**
```python
# config.py
import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# IMPORTANT: Create a file named .env in the same directory
# and add your Gemini API key like this:
# GEMINI_API_KEY="YOUR_API_KEY_HERE"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Please set it in your .env file.")

```

---

### **Phase 2, File 5: `start-buddy-session.sh`**

**Purpose:** The main entry point. This script orchestrates the entire session setup.

**Key Functionality:**
*   Creates a `sessions` directory if it doesn't exist.
*   Generates the `project_context.txt` "repo mix".
*   Launches the Python scripts in new terminal windows.
*   Starts the `script` command to record the Claude session.

**Rough Content:**
```bash
#!/bin/bash

echo "🚀 Starting AI Coding Buddy Session..."

# --- Configuration ---
SESSION_ID=$(date +%Y%m%d_%H%M%S)
SESSIONS_DIR="sessions"
CONTEXT_FILE="$SESSIONS_DIR/project_context_${SESSION_ID}.txt"
CLAUDE_LOG_FILE="$SESSIONS_DIR/claude_session_${SESSION_ID}.log"

# --- Setup ---
mkdir -p "$SESSIONS_DIR"

# --- Function to Create "Repo Mix" ---
create_repo_mix() {
  echo "  -> Generating 'repo mix' from tracked files..."
  # Clear the file if it exists
  > "$CONTEXT_FILE"

  # Use git to list all tracked files, respecting .gitignore
  git ls-files | while read -r file; do
    # Skip our own script and session files
    if [[ "$file" == "start-buddy-session.sh" || "$file" == sessions/* ]]; then
      continue
    fi
    echo "--- START FILE: $file ---" >> "$CONTEXT_FILE"
    cat "$file" >> "$CONTEXT_FILE"
    echo -e "\n--- END FILE: $file ---\n" >> "$CONTEXT_FILE"
  done
  echo "  -> 'Repo mix' created at $CONTEXT_FILE"
}

# --- Main Execution ---
create_repo_mix

echo "  -> Launching Monitoring Agent in the background..."
# Pass the file paths to the agent
python3 monitoring_agent.py --context_file "$CONTEXT_FILE" --log_file "$CLAUDE_LOG_FILE" &
AGENT_PID=$!

echo "  -> Opening Buddy Chat UI and Claude Session in new terminals..."
# This command is for macOS. Linux/Windows will require different commands.
# For Linux (e.g., gnome-terminal):
# gnome-terminal -- python3 buddy_chat_ui.py
# gnome-terminal -- script -q "$CLAUDE_LOG_FILE" claude-cli --start-session

# For macOS:
osascript -e "tell app \"Terminal\" to do script \"cd $(pwd); python3 buddy_chat_ui.py\""
osascript -e "tell app \"Terminal\" to do script \"cd $(pwd); script -q '$CLAUDE_LOG_FILE' claude-cli --start-session\""

echo "✅ Session is live! Work in the 'script' window and chat in the 'Buddy Chat' window."
echo "   Press Ctrl+C in this window to terminate the monitoring agent when done."

# Wait for the agent to be terminated
wait $AGENT_PID
echo "👋 Monitoring agent shut down. Session ended."
```

---

### **Phase 3, File 6: `monitoring_agent.py`**

**Purpose:** The core background service. It watches for user requests, packages all context, calls the Gemini API, and provides the response.

**Key Functionality:**
*   Parses command-line arguments for file paths.
*   Initializes the Gemini client.
*   Enters a main loop to watch for a "request" file.
*   When a request appears, it uploads the context and log files to the Gemini File API.
*   Constructs the detailed prompt with file references.
*   Calls the Gemini model and writes the output to a "response" file.

**Rough Content:**
```python
# monitoring_agent.py
import time
import os
import argparse
import google.generativeai as genai
from config import GEMINI_API_KEY

# Simple file-based IPC (Inter-Process Communication)
REQUEST_FILE = "sessions/buddy_request.tmp"
RESPONSE_FILE = "sessions/buddy_response.tmp"

def main(context_file, log_file):
    print(f"Monitoring Agent Started. PID: {os.getpid()}")
    print(f"Watching context: {context_file}")
    print(f"Watching log: {log_file}")

    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-pro-latest')

    while True:
        # Wait for the UI to create a request file
        if os.path.exists(REQUEST_FILE):
            with open(REQUEST_FILE, 'r') as f:
                user_question = f.read()
            os.remove(REQUEST_FILE)

            print("  -> Request received. Processing with Gemini...")

            # 1. Upload files to Gemini
            print("  -> Uploading context files...")
            project_context_file = genai.upload_file(path=context_file)
            claude_log_file_upload = genai.upload_file(path=log_file)
            
            # 2. Construct the prompt
            prompt = f"""
            You are a world-class senior software architect. Analyze the two files provided:
            1. 'Project Context': A concatenation of all relevant source code files in my project.
            2. 'Session Log': A live log of my coding session with another AI.
            
            Please analyze these files to get the full context of my project. Then, answer my specific question that follows.

            ### My Question ###
            {user_question}
            """

            # 3. Call Gemini API
            response = model.generate_content([prompt, project_context_file, claude_log_file_upload])
            
            # 4. Write the response for the UI to pick up
            with open(RESPONSE_FILE, 'w') as f:
                f.write(response.text)
            
            print("  -> Response sent to UI.")
            
            # Clean up uploaded files to manage storage
            genai.delete_file(project_context_file.name)
            genai.delete_file(claude_log_file_upload.name)

        time.sleep(1) # Check for request every second

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--context_file", required=True)
    parser.add_argument("--log_file", required=True)
    args = parser.parse_args()
    main(args.context_file, args.log_file)
```

---

### **Phase 3, File 7: `buddy_chat_ui.py`**

**Purpose:** The user-facing chat interface. It takes user input, communicates with the agent, and displays the AI's response.

**Key Functionality:**
*   Provides a continuous input loop for the user.
*   Writes the user's question to the `REQUEST_FILE`.
*   Waits for the `RESPONSE_FILE` to be created by the agent.
*   Reads the response, prints it to the console, and cleans up the file.

**Rough Content:**
```python
# buddy_chat_ui.py
import os
import time

REQUEST_FILE = "sessions/buddy_request.tmp"
RESPONSE_FILE = "sessions/buddy_response.tmp"

def main():
    print("--- AI Coding Buddy Chat ---")
    print("Ask for help, architectural advice, or a bug fix. Type 'exit' to quit.")

    while True:
        try:
            prompt = input("\n[Ask Gemini]: ")
            if prompt.lower() == 'exit':
                break

            # 1. Send request to the agent
            with open(REQUEST_FILE, 'w') as f:
                f.write(prompt)

            # 2. Wait for the agent's response
            print("... (Thinking) ...")
            while not os.path.exists(RESPONSE_FILE):
                time.sleep(0.5)

            # 3. Read and display the response
            with open(RESPONSE_FILE, 'r') as f:
                response_text = f.read()
            
            os.remove(RESPONSE_FILE)

            print("\n--- [Gemini's Advice] ---")
            print(response_text)
            print("-------------------------")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred: {e}")
    
    print("\nBuddy chat closed.")


if __name__ == "__main__":
    # Clean up any stale files on start
    if os.path.exists(REQUEST_FILE): os.remove(REQUEST_FILE)
    if os.path.exists(RESPONSE_FILE): os.remove(RESPONSE_FILE)
    main()
```

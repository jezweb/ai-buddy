# monitoring_agent.py
import time
import os
import argparse
import sys
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SESSIONS_DIR, POLLING_INTERVAL

# Simple file-based IPC (Inter-Process Communication)
REQUEST_FILE = os.path.join(SESSIONS_DIR, "buddy_request.tmp")
RESPONSE_FILE = os.path.join(SESSIONS_DIR, "buddy_response.tmp")
PROCESSING_FILE = os.path.join(SESSIONS_DIR, "buddy_processing.tmp")

def read_file_safely(file_path, max_size=10*1024*1024):  # 10MB limit
    """Read file with size limit to prevent memory issues."""
    try:
        file_size = os.path.getsize(file_path)
        if file_size > max_size:
            # Read first and last portions if file is too large
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(max_size // 2)
                f.seek(file_size - max_size // 2)
                content += "\n\n[... middle portion truncated due to size ...]\n\n"
                content += f.read()
            return content
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
    except Exception as e:
        return f"[Error reading file: {e}]"

def main(context_file, log_file):
    print(f"Monitoring Agent Started. PID: {os.getpid()}")
    print(f"Watching context: {context_file}")
    print(f"Watching log: {log_file}")
    print(f"Using model: {GEMINI_MODEL}")
    print(f"Polling interval: {POLLING_INTERVAL}s")
    
    # Initialize Gemini client with new SDK
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("✓ Gemini client initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize Gemini client: {e}")
        sys.exit(1)
    
    # Ensure sessions directory exists
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    # Clean up any stale files
    for temp_file in [REQUEST_FILE, RESPONSE_FILE, PROCESSING_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    while True:
        try:
            # Wait for the UI to create a request file
            if os.path.exists(REQUEST_FILE):
                # Create processing indicator
                Path(PROCESSING_FILE).touch()
                
                # Read and remove request
                user_question = read_file_safely(REQUEST_FILE)
                os.remove(REQUEST_FILE)
                
                print(f"\n  -> Request received: {user_question[:100]}...")
                print("  -> Processing with Gemini...")
                
                try:
                    # Read context files
                    project_context = read_file_safely(context_file)
                    
                    # Read session log if it exists
                    if os.path.exists(log_file):
                        session_log = read_file_safely(log_file)
                    else:
                        session_log = "[Session log not yet created - Claude session hasn't started]"
                    
                    # Construct the prompt
                    prompt = f"""You are a world-class senior software architect reviewing an AI Coding Buddy project.

I'm providing you with two important pieces of context:

1. **Project Context**: All the source code files in the project
2. **Session Log**: A live recording of the developer's coding session with Claude

Please analyze these to understand the project fully, then answer my specific question.

### PROJECT CONTEXT ###
{project_context}

### SESSION LOG ###
{session_log}

### MY QUESTION ###
{user_question}

Please provide a thoughtful, actionable response that considers both the project code and the ongoing session."""
                    
                    # Call Gemini API with new SDK format
                    response = client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=prompt
                    )
                    
                    # Extract text from response
                    response_text = response.text if hasattr(response, 'text') else str(response)
                    
                    # Write the response for the UI to pick up
                    with open(RESPONSE_FILE, 'w', encoding='utf-8') as f:
                        f.write(response_text)
                    
                    print("  -> Response sent to UI")
                    
                except Exception as e:
                    # Write error message for UI
                    error_msg = f"Error processing request: {type(e).__name__}: {str(e)}"
                    print(f"  ✗ {error_msg}")
                    
                    with open(RESPONSE_FILE, 'w', encoding='utf-8') as f:
                        f.write(f"⚠️ {error_msg}\n\nPlease check:\n1. Your API key is valid\n2. You have internet connectivity\n3. The Gemini API is accessible\n4. Your request doesn't exceed token limits")
                
                finally:
                    # Remove processing indicator
                    if os.path.exists(PROCESSING_FILE):
                        os.remove(PROCESSING_FILE)
            
            time.sleep(POLLING_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n  -> Monitoring agent shutting down...")
            break
        except Exception as e:
            print(f"  ✗ Unexpected error in main loop: {e}")
            time.sleep(POLLING_INTERVAL)
    
    # Cleanup on exit
    for temp_file in [REQUEST_FILE, RESPONSE_FILE, PROCESSING_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    print("  -> Monitoring agent stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Coding Buddy Monitoring Agent")
    parser.add_argument("--context_file", required=True, help="Path to project context file")
    parser.add_argument("--log_file", required=True, help="Path to Claude session log file")
    args = parser.parse_args()
    
    # Validate file paths
    if not os.path.exists(args.context_file):
        print(f"✗ Error: Context file not found: {args.context_file}")
        sys.exit(1)
    
    try:
        main(args.context_file, args.log_file)
    except KeyboardInterrupt:
        print("\n  -> Received interrupt signal. Shutting down gracefully...")
        sys.exit(0)
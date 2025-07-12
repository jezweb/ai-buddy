# monitoring_agent.py
import time
import os
import argparse
import sys
import logging
import traceback
from datetime import datetime
from pathlib import Path
from google import genai
from config import GEMINI_API_KEY, GEMINI_MODEL, SESSIONS_DIR, POLLING_INTERVAL

# Simple file-based IPC (Inter-Process Communication)
REQUEST_FILE = os.path.join(SESSIONS_DIR, "buddy_request.tmp")
RESPONSE_FILE = os.path.join(SESSIONS_DIR, "buddy_response.tmp")
PROCESSING_FILE = os.path.join(SESSIONS_DIR, "buddy_processing.tmp")
HEARTBEAT_FILE = os.path.join(SESSIONS_DIR, "buddy_heartbeat.tmp")
CHANGES_LOG = os.path.join(SESSIONS_DIR, "changes.log")

# Setup logging
LOG_FILE = os.path.join(SESSIONS_DIR, f"monitoring_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

def update_heartbeat():
    """Update heartbeat file to indicate agent is alive."""
    try:
        with open(HEARTBEAT_FILE, 'w') as f:
            f.write(str(time.time()))
    except Exception as e:
        logging.error(f"Failed to update heartbeat: {e}")

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
        logging.error(f"Error reading file {file_path}: {e}")
        return f"[Error reading file: {e}]"

def get_recent_changes():
    """Read recent changes from the changes log if it exists."""
    if not os.path.exists(CHANGES_LOG):
        return None
    
    try:
        # Read last 100 lines of changes log
        with open(CHANGES_LOG, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-100:] if len(lines) > 100 else lines
            return ''.join(recent_lines)
    except Exception as e:
        logging.error(f"Error reading changes log: {e}")
        return None

def main(context_file, log_file):
    logging.info(f"Monitoring Agent Started. PID: {os.getpid()}")
    logging.info(f"Watching context: {context_file}")
    logging.info(f"Watching log: {log_file}")
    logging.info(f"Using model: {GEMINI_MODEL}")
    logging.info(f"Polling interval: {POLLING_INTERVAL}s")
    logging.info(f"Log file: {LOG_FILE}")
    
    # Initialize Gemini client with new SDK
    client = None
    retry_count = 0
    while retry_count < 3:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            logging.info("✓ Gemini client initialized successfully")
            break
        except Exception as e:
            retry_count += 1
            logging.error(f"Failed to initialize Gemini client (attempt {retry_count}/3): {e}")
            if retry_count >= 3:
                logging.critical("Failed to initialize Gemini client after 3 attempts. Exiting.")
                sys.exit(1)
            time.sleep(2)
    
    # Ensure sessions directory exists
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    # Clean up any stale files
    for temp_file in [REQUEST_FILE, RESPONSE_FILE, PROCESSING_FILE, HEARTBEAT_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logging.info(f"Cleaned up stale file: {temp_file}")
    
    # Create initial heartbeat immediately
    update_heartbeat()
    logging.info("Initial heartbeat created")
    
    # Main processing loop
    consecutive_errors = 0
    last_heartbeat = time.time()
    
    while True:
        try:
            # Update heartbeat every 5 seconds
            if time.time() - last_heartbeat > 5:
                update_heartbeat()
                last_heartbeat = time.time()
            
            # Wait for the UI to create a request file
            if os.path.exists(REQUEST_FILE):
                # Create processing indicator
                Path(PROCESSING_FILE).touch()
                
                # Read and remove request
                user_question = read_file_safely(REQUEST_FILE)
                os.remove(REQUEST_FILE)
                
                logging.info(f"Request received: {user_question[:100]}...")
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
                    
                    # Get recent changes from Claude hooks if available
                    recent_changes = get_recent_changes()
                    
                    # Construct the prompt
                    prompt = f"""You are a world-class senior software architect reviewing an AI Coding Buddy project.

I'm providing you with multiple pieces of context:

1. **Project Context**: All the source code files in the project
2. **Session Log**: A live recording of the developer's coding session with Claude
3. **Recent Changes**: Real-time tracking of files modified by Claude (if available)

Please analyze these to understand the project fully, then answer my specific question.

### PROJECT CONTEXT ###
{project_context}

### SESSION LOG ###
{session_log}

### RECENT CHANGES (from Claude hooks) ###
{recent_changes if recent_changes else "[No change tracking data available - Claude hooks may not be configured]"}

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
                    
                    logging.info("Response sent to UI successfully")
                    print("  -> Response sent to UI")
                    consecutive_errors = 0  # Reset error counter on success
                    
                except Exception as e:
                    # Write error message for UI
                    error_msg = f"Error processing request: {type(e).__name__}: {str(e)}"
                    logging.error(f"{error_msg}\n{traceback.format_exc()}")
                    print(f"  ✗ {error_msg}")
                    
                    with open(RESPONSE_FILE, 'w', encoding='utf-8') as f:
                        f.write(f"⚠️ {error_msg}\n\nPlease check:\n1. Your API key is valid\n2. You have internet connectivity\n3. The Gemini API is accessible\n4. Your request doesn't exceed token limits\n\nCheck the log file for details: {LOG_FILE}")
                    
                    consecutive_errors += 1
                
                finally:
                    # Remove processing indicator
                    if os.path.exists(PROCESSING_FILE):
                        os.remove(PROCESSING_FILE)
            
            time.sleep(POLLING_INTERVAL)
            
        except KeyboardInterrupt:
            logging.info("Received interrupt signal, shutting down gracefully")
            print("\n  -> Monitoring agent shutting down...")
            break
        except Exception as e:
            consecutive_errors += 1
            logging.error(f"Unexpected error in main loop: {e}\n{traceback.format_exc()}")
            print(f"  ✗ Unexpected error in main loop: {e}")
            
            # If too many consecutive errors, exit to avoid infinite error loop
            if consecutive_errors > 10:
                logging.critical(f"Too many consecutive errors ({consecutive_errors}), exiting")
                print(f"  ✗ Too many consecutive errors ({consecutive_errors}), exiting")
                sys.exit(1)
            
            time.sleep(POLLING_INTERVAL * 2)  # Wait longer after errors
    
    # Cleanup on exit
    for temp_file in [REQUEST_FILE, RESPONSE_FILE, PROCESSING_FILE, HEARTBEAT_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logging.info(f"Cleaned up {temp_file}")
    
    logging.info("Monitoring agent stopped")
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
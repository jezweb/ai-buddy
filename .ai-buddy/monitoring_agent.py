# monitoring_agent.py
import time
import os
import argparse
import sys
import logging
import traceback
import json
from datetime import datetime
from pathlib import Path
from google import genai
from config import (
    GEMINI_API_KEY, GEMINI_MODEL, SESSIONS_DIR, POLLING_INTERVAL,
    SMART_CONTEXT_ENABLED, MAX_CONTEXT_SIZE
)
from conversation_manager import ConversationManager
from repo_blob_generator import generate_repo_blob
from file_operations import (
    FileOperationResponse, FileOperationExecutor,
    detect_file_operation_request
)
from smart_context import SmartContextBuilder

# Simple file-based IPC (Inter-Process Communication)
REQUEST_FILE = os.path.join(SESSIONS_DIR, "buddy_request.tmp")
RESPONSE_FILE = os.path.join(SESSIONS_DIR, "buddy_response.tmp")
PROCESSING_FILE = os.path.join(SESSIONS_DIR, "buddy_processing.tmp")
HEARTBEAT_FILE = os.path.join(SESSIONS_DIR, "buddy_heartbeat.tmp")
CHANGES_LOG = os.path.join(SESSIONS_DIR, "changes.log")
REFRESH_REQUEST_FILE = os.path.join(SESSIONS_DIR, "buddy_refresh_request.tmp")

# Track uploaded files per session to enable cleanup
uploaded_file_tracker = {}  # session_id -> file_name

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

def cleanup_old_gemini_files(client, session_id=None):
    """Clean up old uploaded files from Gemini, optionally keeping files for current session."""
    try:
        logging.info("Checking for old Gemini files to clean up...")
        cleaned_count = 0
        
        # List all files
        for file in client.files.list():
            # Check if this is one of our temp context files
            if file.name and 'temp_context_' in file.name:
                # If we have a session_id and this file belongs to current session, skip it
                if session_id and f"temp_context_{session_id}" in file.name:
                    logging.info(f"Keeping current session file: {file.name}")
                    continue
                
                # Otherwise, delete the old file
                try:
                    client.files.delete(name=file.name)
                    logging.info(f"Deleted old file: {file.name}")
                    cleaned_count += 1
                except Exception as e:
                    logging.warning(f"Could not delete file {file.name}: {e}")
        
        if cleaned_count > 0:
            logging.info(f"Cleaned up {cleaned_count} old file(s)")
        else:
            logging.info("No old files to clean up")
            
    except Exception as e:
        logging.error(f"Error during file cleanup: {e}")

def main(context_file, log_file, session_id=None):
    # Extract session ID from log file name if not provided
    if not session_id:
        # claude_session_20250712_140230.log -> 20250712_140230
        session_id = os.path.basename(log_file).replace('claude_session_', '').replace('.log', '')
    
    logging.info(f"Monitoring Agent Started. PID: {os.getpid()}")
    logging.info(f"Session ID: {session_id}")
    logging.info(f"Watching context: {context_file}")
    logging.info(f"Watching log: {log_file}")
    logging.info(f"Using model: {GEMINI_MODEL}")
    logging.info(f"Smart context: {'ENABLED' if SMART_CONTEXT_ENABLED else 'DISABLED'}")
    logging.info(f"Polling interval: {POLLING_INTERVAL}s")
    logging.info(f"Log file: {LOG_FILE}")
    
    # Initialize conversation manager
    conversation_mgr = ConversationManager(session_id, SESSIONS_DIR)
    logging.info(f"Conversation history initialized: {len(conversation_mgr.conversation_history)} previous exchanges")
    
    # Initialize Gemini client with hot-reload support
    client = None
    retry_count = 0
    max_retries = 30  # 5 minutes total (10s intervals)
    
    while retry_count < max_retries:
        try:
            # Reload environment variables in case user added the key
            from dotenv import load_dotenv
            load_dotenv(Path(__file__).parent / '.env', override=True)
            api_key = os.getenv("GEMINI_API_KEY")
            
            # Check if we have a valid API key
            if not api_key or api_key == "YOUR_GEMINI_KEY_GOES_HERE":
                retry_count += 1
                if retry_count == 1:
                    print("\n⚠️  No valid Gemini API key found!")
                    print("📝 Please add your API key to .ai-buddy/.env file:")
                    print("   1. Edit .ai-buddy/.env")
                    print("   2. Replace YOUR_GEMINI_KEY_GOES_HERE with your actual key")
                    print("   3. Get a key from: https://makersuite.google.com/app/apikey")
                    print(f"\n⏳ Waiting for API key... (checking every 10 seconds)")
                
                if retry_count % 6 == 0:  # Remind every minute
                    print(f"⏳ Still waiting for API key in .env file... (attempt {retry_count}/{max_retries})")
                
                time.sleep(10)
                continue
            
            # Try to initialize client with the API key
            client = genai.Client(api_key=api_key)
            logging.info("✓ Gemini client initialized successfully")
            print("\n✅ API key loaded successfully!")
            
            # Clean up any old uploaded files from previous sessions
            cleanup_old_gemini_files(client, session_id)
            
            break
            
        except Exception as e:
            retry_count += 1
            logging.error(f"Failed to initialize Gemini client (attempt {retry_count}/{max_retries}): {e}")
            
            if "API key not valid" in str(e):
                print(f"\n❌ Invalid API key. Please check your key in .env file.")
                print(f"   Current key starts with: {api_key[:20]}..." if api_key and len(api_key) > 20 else "")
            
            if retry_count >= max_retries:
                logging.critical("Failed to initialize Gemini client after all attempts. Exiting.")
                print("\n❌ Failed to initialize after 5 minutes. Please check:")
                print("   1. Your API key is valid")
                print("   2. You have internet connectivity")
                print("   3. The Gemini API is accessible")
                sys.exit(1)
            
            time.sleep(10)
    
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
            
            # Check for refresh request
            if os.path.exists(REFRESH_REQUEST_FILE):
                logging.info("Refresh request received")
                print("\n  -> Refresh request received. Regenerating repo-blob...")
                
                try:
                    # Extract project root from context file path
                    # e.g., /path/to/.ai-buddy/sessions/project_context_20250712_140230.txt
                    # We need to go up two directories from the context file
                    project_root = Path(context_file).parent.parent.parent
                    
                    # Generate new repo-blob
                    if generate_repo_blob(str(project_root), context_file):
                        logging.info(f"Repo-blob refreshed successfully: {context_file}")
                        print("  -> Repo-blob refreshed successfully!")
                    else:
                        logging.error("Failed to refresh repo-blob")
                        print("  -> Failed to refresh repo-blob")
                    
                except Exception as e:
                    logging.error(f"Error during refresh: {e}\n{traceback.format_exc()}")
                    print(f"  -> Error during refresh: {e}")
                
                finally:
                    # Remove the request file to signal completion
                    if os.path.exists(REFRESH_REQUEST_FILE):
                        os.remove(REFRESH_REQUEST_FILE)
            
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
                    # Get recent conversation context first
                    conversation_context = conversation_mgr.get_recent_context()
                    
                    # Read session log if it exists
                    if os.path.exists(log_file):
                        session_log = read_file_safely(log_file)
                    else:
                        session_log = "[Session log not yet created - Claude session hasn't started]"
                    
                    # Get recent changes from Claude hooks if available
                    recent_changes = get_recent_changes()
                    
                    # Check if smart context is enabled
                    if SMART_CONTEXT_ENABLED:
                        # Extract project root from context file path
                        project_root = Path(context_file).parent.parent.parent
                        
                        # Use smart context builder
                        context_builder = SmartContextBuilder(
                            str(project_root),
                            max_context_size=MAX_CONTEXT_SIZE
                        )
                        
                        # Build optimized context
                        project_context, included_files = context_builder.build_context(
                            query=user_question,
                            session_log=session_log,
                            conversation_history=conversation_context,
                            changes_log=recent_changes
                        )
                        
                        logging.info(f"Smart context built with {len(included_files)} files")
                        
                        # Note: conversation_context is already included in project_context
                        conversation_context = ""  # Avoid duplication
                    else:
                        # Traditional approach - read full repo-blob
                        project_context = read_file_safely(context_file)
                    
                    # Construct the prompt
                    base_prompt = f"""You are a world-class senior software architect reviewing an AI Coding Buddy project.

I'm providing you with multiple pieces of context:

1. **Project Context**: All the source code files in the project
2. **Session Log**: A live recording of the developer's coding session with Claude
3. **Recent Changes**: Real-time tracking of files modified by Claude (if available)
4. **Previous Conversation**: Recent exchanges from our current session

Please analyze these to understand the project fully, then answer my specific question."""
                    
                    # Add file operation instructions if needed
                    if is_file_operation:
                        prompt = base_prompt + """

When creating or modifying files:
- Use relative paths from the project root
- Provide clear descriptions for each file operation
- Consider existing project structure and conventions
- Include appropriate file headers, imports, and documentation
- Set overwrite=true only when explicitly asked to replace existing files
- Add warnings for any potential issues or considerations"""
                    else:
                        prompt = base_prompt
                    
                    # For smart context, the context is already included in project_context
                    if SMART_CONTEXT_ENABLED:
                        prompt += f"""

{project_context}

### MY QUESTION ###
{user_question}

Please provide a thoughtful, actionable response that considers both the project code and the ongoing session."""
                    else:
                        # Traditional format
                        prompt += f"""

### RECENT CONVERSATION HISTORY ###
{conversation_context}

### PROJECT CONTEXT ###
{project_context}

### SESSION LOG ###
{session_log}

### RECENT CHANGES (from Claude hooks) ###
{recent_changes if recent_changes else "[No change tracking data available - Claude hooks may not be configured]"}

### MY QUESTION ###
{user_question}

Please provide a thoughtful, actionable response that considers both the project code and the ongoing session."""
                    
                    # Check if this is a file operation request
                    is_file_operation = detect_file_operation_request(user_question)
                    
                    # Extract project root from context file path
                    project_root = Path(context_file).parent.parent.parent
                    
                    # Upload files to Gemini for better handling
                    uploaded_files = []
                    try:
                        # Upload project context if it's large
                        if len(project_context) > 50000:  # If over 50KB, use file upload
                            logging.info("Uploading project context to Gemini Files API...")
                            
                            # Check if we have an old uploaded file for this session
                            if session_id in uploaded_file_tracker:
                                old_file_name = uploaded_file_tracker[session_id]
                                try:
                                    client.files.delete(name=old_file_name)
                                    logging.info(f"Deleted previous upload for session: {old_file_name}")
                                except Exception as e:
                                    logging.warning(f"Could not delete old file {old_file_name}: {e}")
                            
                            context_path = os.path.join(SESSIONS_DIR, f"temp_context_{session_id}.txt")
                            with open(context_path, 'w', encoding='utf-8') as f:
                                f.write(project_context)
                            
                            uploaded_context = client.files.upload(file=context_path)
                            uploaded_files.append(uploaded_context)
                            os.remove(context_path)  # Clean up temp file
                            
                            # Track this upload for future cleanup
                            uploaded_file_tracker[session_id] = uploaded_context.name
                            logging.info(f"Tracking uploaded file: {uploaded_context.name}")
                            
                            # Adjust prompt to reference uploaded file
                            prompt = prompt.replace(project_context, "[Project context uploaded as file - see attached]")
                            
                            # Call with uploaded file (file first, then prompt)
                            if is_file_operation:
                                # Use structured output for file operations
                                response = client.models.generate_content(
                                    model=GEMINI_MODEL,
                                    contents=[uploaded_context, prompt + "\n\nGenerate the requested file operations."],
                                    config={
                                        'response_mime_type': 'application/json',
                                        'response_schema': FileOperationResponse
                                    }
                                )
                            else:
                                response = client.models.generate_content(
                                    model=GEMINI_MODEL,
                                    contents=[uploaded_context, prompt]
                                )
                        else:
                            # Small enough to include inline
                            if is_file_operation:
                                # Use structured output for file operations
                                response = client.models.generate_content(
                                    model=GEMINI_MODEL,
                                    contents=prompt + "\n\nGenerate the requested file operations.",
                                    config={
                                        'response_mime_type': 'application/json',
                                        'response_schema': FileOperationResponse
                                    }
                                )
                            else:
                                response = client.models.generate_content(
                                    model=GEMINI_MODEL,
                                    contents=prompt
                                )
                    finally:
                        # Note: Uploaded files are automatically deleted after 48 hours
                        # No need to manually delete them
                        if uploaded_files:
                            logging.info(f"Uploaded {len(uploaded_files)} file(s) to Gemini. They will auto-delete after 48 hours.")
                    
                    # Process response based on type
                    if is_file_operation:
                        # Handle structured file operation response
                        try:
                            # Parse the JSON response
                            file_ops = FileOperationResponse.model_validate_json(response.text)
                            
                            # Execute file operations
                            executor = FileOperationExecutor(str(project_root))
                            result = executor.execute_operations(file_ops)
                            
                            # Create user-friendly response
                            response_lines = [f"# {file_ops.summary}\n"]
                            
                            if result.files_created:
                                response_lines.append("\n## Files Created:")
                                for f in result.files_created:
                                    response_lines.append(f"✅ {f}")
                            
                            if result.files_updated:
                                response_lines.append("\n## Files Updated:")
                                for f in result.files_updated:
                                    response_lines.append(f"📝 {f}")
                            
                            if result.files_deleted:
                                response_lines.append("\n## Files Deleted:")
                                for f in result.files_deleted:
                                    response_lines.append(f"🗑️ {f}")
                            
                            if result.errors:
                                response_lines.append("\n## Errors:")
                                for e in result.errors:
                                    response_lines.append(f"❌ {e}")
                            
                            if file_ops.warnings:
                                response_lines.append("\n## Warnings:")
                                for w in file_ops.warnings:
                                    response_lines.append(f"⚠️ {w}")
                            
                            response_lines.append(f"\n\n✨ Operations completed: {len(result.operations_performed)}")
                            response_text = "\n".join(response_lines)
                            
                            # Also log the operations
                            logging.info(f"File operations completed: {json.dumps(result.model_dump(), indent=2)}")
                            
                        except Exception as e:
                            # If file operations fail, return error message
                            response_text = f"❌ Error processing file operations: {str(e)}\n\nPlease check the logs for details."
                            logging.error(f"File operation error: {e}\n{traceback.format_exc()}")
                    else:
                        # Extract text from regular response
                        response_text = response.text if hasattr(response, 'text') else str(response)
                    
                    # Write the response for the UI to pick up
                    with open(RESPONSE_FILE, 'w', encoding='utf-8') as f:
                        f.write(response_text)
                    
                    # Save to conversation history
                    conversation_mgr.add_exchange(user_question, response_text)
                    
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
    for temp_file in [REQUEST_FILE, RESPONSE_FILE, PROCESSING_FILE, HEARTBEAT_FILE, REFRESH_REQUEST_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
            logging.info(f"Cleaned up {temp_file}")
    
    # Clean up any uploaded files for this session
    if session_id in uploaded_file_tracker:
        try:
            file_name = uploaded_file_tracker[session_id]
            client.files.delete(name=file_name)
            logging.info(f"Cleaned up uploaded file on exit: {file_name}")
        except Exception as e:
            logging.warning(f"Could not clean up uploaded file on exit: {e}")
    
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
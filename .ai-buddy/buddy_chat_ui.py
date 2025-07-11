# buddy_chat_ui.py
import os
import time
import sys
import subprocess
from pathlib import Path
from config import SESSIONS_DIR

REQUEST_FILE = os.path.join(SESSIONS_DIR, "buddy_request.tmp")
RESPONSE_FILE = os.path.join(SESSIONS_DIR, "buddy_response.tmp")
PROCESSING_FILE = os.path.join(SESSIONS_DIR, "buddy_processing.tmp")
HEARTBEAT_FILE = os.path.join(SESSIONS_DIR, "buddy_heartbeat.tmp")

def check_agent_health():
    """Check if monitoring agent is alive by checking heartbeat."""
    if not os.path.exists(HEARTBEAT_FILE):
        return False
    
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            last_heartbeat = float(f.read().strip())
        
        # Consider agent healthy if heartbeat is less than 10 seconds old
        return (time.time() - last_heartbeat) < 10
    except:
        return False

def print_welcome():
    """Print welcome message and instructions."""
    print("=" * 60)
    print("🤖 AI Coding Buddy Chat")
    print("=" * 60)
    print("Ask for help, architectural advice, or bug fixes.")
    print("Commands:")
    print("  - Type your question and press Enter")
    print("  - 'exit' or 'quit' to close")
    print("  - 'clear' to clear the screen")
    print("  - 'help' for this message")
    print("  - 'status' to check monitoring agent status")
    print("=" * 60)
    print()

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')

def format_response(response_text):
    """Format the response for better readability."""
    # Add some basic formatting
    lines = response_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Preserve code blocks
        if line.strip().startswith('```'):
            formatted_lines.append(line)
        # Add spacing for headers
        elif line.strip().startswith('#'):
            formatted_lines.append('\n' + line)
        # Preserve lists
        elif line.strip().startswith(('- ', '* ', '1.', '2.', '3.')):
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines)

def wait_for_response():
    """Wait for response with animated indicator."""
    animation = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    idx = 0
    start_time = time.time()
    last_health_check = time.time()
    
    print("\n💭 Thinking", end='', flush=True)
    
    while not os.path.exists(RESPONSE_FILE):
        # Check agent health every 2 seconds
        if time.time() - last_health_check > 2:
            if not check_agent_health():
                print("\r⚠️  Monitoring agent appears to be down!                    ", flush=True)
                return False
            last_health_check = time.time()
        
        # Check if still processing
        if os.path.exists(PROCESSING_FILE):
            print(f"\r💭 Thinking {animation[idx % len(animation)]}", end='', flush=True)
            idx += 1
        else:
            # If no processing file and it's been more than 5 seconds, assume lost
            if time.time() - start_time > 5:
                print("\r⚠️  Request might have been lost or agent is not responding.     ", flush=True)
                return False
        
        time.sleep(0.1)
    
    print("\r✓ Response received!                    ", flush=True)
    return True

def main():
    # Ensure sessions directory exists
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    
    # Clean up any stale files on start
    for temp_file in [REQUEST_FILE, RESPONSE_FILE, PROCESSING_FILE]:
        if os.path.exists(temp_file):
            os.remove(temp_file)
    
    clear_screen()
    print_welcome()
    
    # Check if monitoring agent is running
    if not os.path.exists(os.path.dirname(REQUEST_FILE)):
        print("⚠️  Warning: Sessions directory not found. Is the monitoring agent running?")
        print("   Run ./start-buddy-session.sh to start the system properly.")
        print()
    
    while True:
        try:
            # Get user input
            prompt = input("\n🎯 [You]: ").strip()
            
            # Handle commands
            if prompt.lower() in ['exit', 'quit']:
                print("\n👋 Goodbye! Happy coding!")
                break
            elif prompt.lower() == 'clear':
                clear_screen()
                print_welcome()
                continue
            elif prompt.lower() == 'help':
                print_welcome()
                continue
            elif prompt.lower() == 'status':
                if check_agent_health():
                    print("\n✅ Monitoring agent is running and healthy")
                else:
                    print("\n❌ Monitoring agent appears to be down!")
                    print("   Check the terminal where you started the session.")
                    print("   You may need to restart the AI Buddy session.")
                continue
            elif not prompt:
                continue
            
            # Send request to the agent
            try:
                with open(REQUEST_FILE, 'w', encoding='utf-8') as f:
                    f.write(prompt)
            except Exception as e:
                print(f"⚠️  Error sending request: {e}")
                continue
            
            # Wait for the agent's response
            if wait_for_response():
                try:
                    # Read and display the response
                    with open(RESPONSE_FILE, 'r', encoding='utf-8') as f:
                        response_text = f.read()
                    
                    os.remove(RESPONSE_FILE)
                    
                    print("\n" + "─" * 60)
                    print("🧠 [Gemini]:")
                    print("─" * 60)
                    print(format_response(response_text))
                    print("─" * 60)
                    
                except Exception as e:
                    print(f"\n⚠️  Error reading response: {e}")
            else:
                if not check_agent_health():
                    print("\n❌ The monitoring agent is not responding.")
                    print("   Please check the monitoring agent terminal for errors.")
                    print("   You may need to restart the AI Buddy session.")
                else:
                    print("\n⚠️  No response received despite agent being healthy.")
                    print("   There might be an issue with the Gemini API.")
                    print("   Check the monitoring agent terminal for error details.")
        
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except EOFError:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n⚠️  Unexpected error: {e}")
            print("   You can continue typing or 'exit' to quit.")
    
    # Cleanup on exit
    for temp_file in [REQUEST_FILE, RESPONSE_FILE]:
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n⚠️  Fatal error: {e}")
        sys.exit(1)
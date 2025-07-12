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
CHANGES_LOG = os.path.join(SESSIONS_DIR, "changes.log")

def check_agent_health():
    """Check if monitoring agent is alive by checking heartbeat and processing state."""
    # If actively processing, consider healthy regardless of heartbeat
    if os.path.exists(PROCESSING_FILE):
        return True
    
    # Check heartbeat file
    if not os.path.exists(HEARTBEAT_FILE):
        return False
    
    try:
        with open(HEARTBEAT_FILE, 'r') as f:
            last_heartbeat = float(f.read().strip())
        
        # Consider agent healthy if heartbeat is less than 15 seconds old (was 10)
        # This gives more time for heartbeat updates during heavy processing
        return (time.time() - last_heartbeat) < 15
    except:
        return False

# ANSI color codes for better readability
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def print_welcome():
    """Print welcome message and instructions."""
    timeout = int(os.getenv("AI_BUDDY_TIMEOUT", "60"))
    print("=" * 60)
    print(f"{Colors.BOLD}🤖 AI Coding Buddy Chat{Colors.END}")
    print("=" * 60)
    print("Ask for help, architectural advice, or bug fixes.")
    print("Commands:")
    print("  - Type your question and press Enter")
    print("  - 'exit' or 'quit' to close")
    print("  - 'clear' to clear the screen")
    print("  - 'help' for this message")
    print("  - 'status' to check monitoring agent status")
    print("  - 'changes' to view recent file changes")
    print(f"\nTimeout: {timeout}s (set AI_BUDDY_TIMEOUT env var to change)")
    print("=" * 60)
    print()

def clear_screen():
    """Clear the terminal screen."""
    os.system('clear' if os.name != 'nt' else 'cls')

def format_response(response_text):
    """Format the response for better readability with enhanced markdown support."""
    import re
    import textwrap
    
    lines = response_text.split('\n')
    formatted_lines = []
    in_code_block = False
    terminal_width = 80  # Conservative width for better readability
    
    for i, line in enumerate(lines):
        # Handle code blocks
        if line.strip().startswith('```'):
            in_code_block = not in_code_block
            if in_code_block:
                formatted_lines.append('')
                formatted_lines.append(f"{Colors.YELLOW}{'─' * 60}{Colors.END}")
                formatted_lines.append(f"{Colors.YELLOW}{line}{Colors.END}")
            else:
                formatted_lines.append(f"{Colors.YELLOW}{line}{Colors.END}")
                formatted_lines.append(f"{Colors.YELLOW}{'─' * 60}{Colors.END}")
                formatted_lines.append('')
            continue
        
        # Don't format inside code blocks
        if in_code_block:
            formatted_lines.append(line)
            continue
        
        # Handle headers with better visual separation
        if line.strip().startswith('###'):
            # H3 headers
            header_text = line.strip().lstrip('#').strip()
            formatted_lines.append('')
            formatted_lines.append(f"{Colors.YELLOW}▓ {header_text.upper()} ▓{Colors.END}")
            formatted_lines.append('')
        elif line.strip().startswith('##'):
            # H2 headers
            header_text = line.strip().lstrip('#').strip()
            formatted_lines.append('')
            formatted_lines.append(f"{Colors.CYAN}{'═' * 60}{Colors.END}")
            formatted_lines.append(f"{Colors.CYAN}{Colors.BOLD}{header_text}{Colors.END}")
            formatted_lines.append(f"{Colors.CYAN}{'═' * 60}{Colors.END}")
        elif line.strip().startswith('#'):
            # H1 headers
            header_text = line.strip().lstrip('#').strip()
            formatted_lines.append('')
            formatted_lines.append(f"{Colors.HEADER}{Colors.BOLD}╔{'═' * (len(header_text) + 2)}╗{Colors.END}")
            formatted_lines.append(f"{Colors.HEADER}{Colors.BOLD}║ {header_text} ║{Colors.END}")
            formatted_lines.append(f"{Colors.HEADER}{Colors.BOLD}╚{'═' * (len(header_text) + 2)}╝{Colors.END}")
        
        # Handle bullet points with better formatting
        elif re.match(r'^\s*\*\*[^*]+\*\*:', line):
            # Bullet points that start with bold text
            # Extract the bold part and the rest
            match = re.match(r'^(\s*)\*\*([^*]+)\*\*:(.*)$', line)
            if match:
                indent, bold_text, rest = match.groups()
                formatted_lines.append('')
                formatted_lines.append(f"{indent}{Colors.GREEN}►{Colors.END} {Colors.BOLD}{bold_text}:{Colors.END}{rest}")
        elif re.match(r'^\s*\d+\.\s+\*\*[^*]+\*\*:', line):
            # Numbered lists with bold text
            match = re.match(r'^(\s*)(\d+)\.\s+\*\*([^*]+)\*\*:(.*)$', line)
            if match:
                indent, num, bold_text, rest = match.groups()
                formatted_lines.append('')
                formatted_lines.append(f"{indent}{Colors.BLUE}{num}.{Colors.END} {Colors.BOLD}{bold_text}:{Colors.END}{rest}")
        elif line.strip().startswith(('- ', '* ', '•')):
            # Regular bullet points
            formatted_lines.append('  ' + line.strip())
        elif re.match(r'^\s*\d+\.', line):
            # Numbered lists
            formatted_lines.append('  ' + line.strip())
        
        # Handle lines with just bold text
        elif '**' in line:
            # Convert **text** to bold colored text
            formatted_line = re.sub(r'\*\*([^*]+)\*\*', rf'{Colors.BOLD}\1{Colors.END}', line)
            # Wrap long lines
            if len(formatted_line) > terminal_width:
                wrapped = textwrap.fill(formatted_line, width=terminal_width, 
                                      break_long_words=False, break_on_hyphens=False)
                formatted_lines.extend(wrapped.split('\n'))
            else:
                formatted_lines.append(formatted_line)
        
        # Empty lines
        elif not line.strip():
            # Don't add too many empty lines
            if formatted_lines and formatted_lines[-1] != '':
                formatted_lines.append('')
        
        # Regular text
        else:
            # Wrap long lines for better readability
            if len(line) > terminal_width:
                wrapped = textwrap.fill(line, width=terminal_width, 
                                      break_long_words=False, break_on_hyphens=False)
                formatted_lines.extend(wrapped.split('\n'))
            else:
                formatted_lines.append(line)
    
    # Clean up excessive empty lines
    result = []
    prev_empty = False
    for line in formatted_lines:
        if line == '':
            if not prev_empty:
                result.append(line)
            prev_empty = True
        else:
            result.append(line)
            prev_empty = False
    
    return '\n'.join(result)

def wait_for_response():
    """Wait for response with animated indicator and progress feedback."""
    animation = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]
    idx = 0
    start_time = time.time()
    last_health_check = time.time()
    last_progress_update = time.time()
    consecutive_health_failures = 0
    
    # Configurable timeout (default 60 seconds)
    timeout = int(os.getenv("AI_BUDDY_TIMEOUT", "60"))
    
    print("\n💭 Processing", end='', flush=True)
    
    while not os.path.exists(RESPONSE_FILE):
        elapsed = int(time.time() - start_time)
        
        # Check agent health every 2 seconds
        if time.time() - last_health_check > 2:
            if not check_agent_health():
                consecutive_health_failures += 1
                # Only declare agent down after 3 consecutive failures (6 seconds)
                if consecutive_health_failures >= 3:
                    print(f"\r❌ Monitoring agent is not responding after {elapsed}s!                    ", flush=True)
                    return False
            else:
                consecutive_health_failures = 0  # Reset on successful check
            last_health_check = time.time()
        
        # Update progress every second
        if time.time() - last_progress_update >= 1:
            if os.path.exists(PROCESSING_FILE):
                # Show different messages based on elapsed time
                if elapsed < 10:
                    status = "Processing"
                elif elapsed < 20:
                    status = "Still processing"
                elif elapsed < 30:
                    status = "Taking a bit longer"
                else:
                    status = "Complex request"
                
                print(f"\r💭 {status} {animation[idx % len(animation)]} ({elapsed}s)", end='', flush=True)
                idx += 1
            else:
                # Processing file missing but agent is healthy - still waiting for it to start
                print(f"\r⏳ Waiting for processing to start ({elapsed}s)", end='', flush=True)
            
            last_progress_update = time.time()
        
        # Only timeout if we've exceeded the limit AND there's no processing happening
        if elapsed > timeout:
            if os.path.exists(PROCESSING_FILE):
                # Still processing, give it more time
                if elapsed > timeout * 2:
                    print(f"\r⚠️  Request timed out after {elapsed}s (processing was still active)     ", flush=True)
                    return False
            else:
                print(f"\r⚠️  Request timed out after {elapsed}s (no processing detected)     ", flush=True)
                return False
        
        time.sleep(0.1)
    
    elapsed = int(time.time() - start_time)
    print(f"\r✓ Response received after {elapsed}s!                    ", flush=True)
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
                print("\n🔍 Checking system status...")
                
                # Check processing state
                if os.path.exists(PROCESSING_FILE):
                    print("⚡ Currently processing a request")
                
                # Check heartbeat
                if os.path.exists(HEARTBEAT_FILE):
                    try:
                        with open(HEARTBEAT_FILE, 'r') as f:
                            last_heartbeat = float(f.read().strip())
                        age = int(time.time() - last_heartbeat)
                        if age < 15:
                            print(f"✅ Monitoring agent is healthy (heartbeat: {age}s ago)")
                        else:
                            print(f"⚠️  Monitoring agent heartbeat is stale ({age}s ago)")
                    except:
                        print("⚠️  Could not read heartbeat file")
                else:
                    print("❌ No heartbeat file found - agent may not be running")
                
                # Check for change tracking
                if os.path.exists(CHANGES_LOG):
                    try:
                        with open(CHANGES_LOG, 'r') as f:
                            lines = f.readlines()
                        print(f"📝 Change tracking active: {len(lines)} events logged")
                    except:
                        pass
                else:
                    print("📝 Change tracking: Not active (Claude hooks may not be configured)")
                
                # Check for recent logs
                log_files = sorted([f for f in os.listdir(SESSIONS_DIR) if f.startswith("monitoring_agent_") and f.endswith(".log")])
                if log_files:
                    print(f"📄 Latest log: {log_files[-1]}")
                
                continue
            elif prompt.lower() == 'changes':
                print("\n📋 Recent File Changes:")
                print("-" * 60)
                
                if os.path.exists(CHANGES_LOG):
                    try:
                        with open(CHANGES_LOG, 'r') as f:
                            lines = f.readlines()
                        
                        # Show last 20 changes
                        recent = lines[-20:] if len(lines) > 20 else lines
                        if recent:
                            for line in recent:
                                print(line.rstrip())
                        else:
                            print("No changes recorded yet.")
                    except Exception as e:
                        print(f"Error reading changes: {e}")
                else:
                    print("Change tracking not active. To enable:")
                    print("1. Run: ./.ai-buddy/install-hooks.sh")
                    print("2. Restart Claude Code")
                
                print("-" * 60)
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
                    
                    # Format and display the response with enhanced styling
                    print("")
                    print(f"{Colors.CYAN}{'━' * 60}{Colors.END}")
                    print(f"{Colors.CYAN}🧠 GEMINI RESPONSE{Colors.END}")
                    print(f"{Colors.CYAN}{'━' * 60}{Colors.END}")
                    print("")
                    print(format_response(response_text))
                    print("")
                    print(f"{Colors.CYAN}{'━' * 60}{Colors.END}")
                    print(f"{Colors.CYAN}END OF RESPONSE{Colors.END}")
                    print(f"{Colors.CYAN}{'━' * 60}{Colors.END}")
                    
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
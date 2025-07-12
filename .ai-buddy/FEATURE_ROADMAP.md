# AI Buddy Feature Roadmap

## Current Priority: Smart Context Management

### Goal
Automatically detect and prioritize the most relevant files for each query, reducing token usage while improving response quality.

### Implementation Ideas
- Analyze user query to identify relevant files/modules
- Use file modification times and git history
- Track which files are frequently accessed together
- Implement smart ignore patterns beyond .gitignore
- Dynamic context sizing based on query complexity

---

## Future Feature Ideas (Saved for Later)

### 1. Conversation Branching/Checkpoints
- Save conversation state at key points
- Branch off to explore different solutions
- Return to previous states if needed
- "What if we tried X instead?" scenarios

### 2. Multi-Model Support
- Add OpenAI GPT-4 as an alternative
- Claude API integration (for comparison)
- Model switching mid-conversation
- Cost tracking per model

### 4. Session Recording & Playback
- Record entire coding sessions (terminal + chat)
- Playback with timeline scrubbing
- Export sessions as tutorials
- Share sessions with team members

### 5. Team Collaboration Features
- Shared conversation history
- Team knowledge base from past sessions
- Code review mode (Gemini reviews PR diffs)
- Architectural decision records (ADRs) generation

### 6. Enhanced Claude Integration
- Two-way sync: Claude's changes update Gemini's context in real-time
- Gemini can suggest commands for Claude to run
- Joint problem-solving mode
- Automatic error detection and fixing

### 7. Project Templates & Scaffolding
- "Set up a new FastAPI project with auth"
- Generate entire project structures
- Best practices enforcement
- Technology stack recommendations

### 8. Testing & Quality Assistance
- Auto-generate test cases for new code
- Coverage analysis and suggestions
- Performance profiling insights
- Security vulnerability scanning

### 9. Learning & Documentation Mode
- Generate inline code explanations
- Create architecture diagrams (Mermaid)
- Build interactive tutorials
- Knowledge extraction from codebase

### 10. Voice Interface
- Voice commands for common operations
- Dictate questions instead of typing
- Audio feedback for long responses
- Hands-free coding assistance

### 11. Smart Notifications
- Alert when build breaks
- Notify about potential issues in code
- Reminders for TODOs and FIXMEs
- Progress tracking on long tasks

### 12. Plugin System
- Custom tools for specific workflows
- Language-specific analyzers
- Framework-specific helpers
- Community extensions

### 13. Web UI
- Browser-based interface
- Rich text formatting
- Code syntax highlighting
- File tree navigation
- Session management UI
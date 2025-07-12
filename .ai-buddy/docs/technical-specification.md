# Technical Specification - Intelligent Proactive System
## AI Buddy v2.0

**Document Version:** 1.0  
**Date:** January 2025  
**Status:** Draft

---

## 1. System Overview

The Intelligent Proactive System extends AI Buddy with real-time code analysis, error prediction, and automated fix generation capabilities. This specification details the technical implementation of each component.

---

## 2. Core Components Specification

### 2.1 Enhanced Hook Processor

#### Purpose
Capture and process all Claude Code events with minimal latency while extracting actionable intelligence.

#### Interface
```python
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

class EventType(Enum):
    PRE_TOOL_USE = "PreToolUse"
    POST_TOOL_USE = "PostToolUse"
    NOTIFICATION = "Notification"
    STOP = "Stop"

@dataclass
class ProcessedEvent:
    event_type: EventType
    tool_name: Optional[str]
    file_path: Optional[str]
    content: Optional[str]
    metadata: Dict[str, Any]
    risk_score: float
    requires_intervention: bool

class HookProcessor:
    def process_event(self, raw_event: Dict[str, Any]) -> ProcessedEvent:
        """Process raw Claude hook event into structured format."""
        pass
    
    def should_intervene(self, event: ProcessedEvent) -> bool:
        """Determine if proactive intervention is needed."""
        pass
```

#### Implementation Details
- Uses multiprocessing.Queue for async event handling
- Maintains rolling window of last 100 events for context
- Sub-50ms processing time per event

### 2.2 Event Analyzer

#### Purpose
Perform deep analysis of code changes to detect patterns, anti-patterns, and potential issues.

#### Interface
```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class CodePattern:
    pattern_type: str
    confidence: float
    location: str
    description: str
    severity: str

@dataclass
class AnalysisResult:
    patterns_detected: List[CodePattern]
    api_calls: List[str]
    dependencies: List[str]
    complexity_score: float
    security_risks: List[str]

class EventAnalyzer:
    def analyze(self, event: ProcessedEvent) -> AnalysisResult:
        """Perform deep analysis of the event."""
        pass
    
    def detect_patterns(self, code: str) -> List[CodePattern]:
        """Detect code patterns and anti-patterns."""
        pass
    
    def extract_api_calls(self, code: str) -> List[str]:
        """Extract all API calls from code."""
        pass
```

#### Pattern Detection Rules
```yaml
patterns:
  - name: "hardcoded_credentials"
    regex: "(password|api_key|secret)\\s*=\\s*[\"'][^\"']+[\"']"
    severity: "critical"
    suggestion: "Use environment variables"
    
  - name: "sql_injection_risk"
    regex: "execute\\([^?]*\\+.*\\)"
    severity: "high"
    suggestion: "Use parameterized queries"
    
  - name: "deprecated_api"
    regex: "requests\\.get\\(.*verify=False"
    severity: "medium"
    suggestion: "Update to use secure connection"
```

### 2.3 Documentation Lookup Service

#### Purpose
Fetch and cache current API documentation for real-time verification.

#### Interface
```python
from typing import Optional, Dict, List
from datetime import datetime
from abc import ABC, abstractmethod

@dataclass
class APIDoc:
    name: str
    version: str
    signature: str
    description: str
    parameters: List[Dict[str, Any]]
    return_type: str
    deprecated: bool
    alternative: Optional[str]
    examples: List[str]
    last_updated: datetime

class DocFetcher(ABC):
    @abstractmethod
    async def fetch(self, api_name: str) -> Optional[APIDoc]:
        pass

class DocumentationLookup:
    def __init__(self):
        self.fetchers = {
            'python': PythonDocFetcher(),
            'javascript': MDNDocFetcher(),
            'react': ReactDocFetcher(),
            'django': DjangoDocFetcher(),
        }
        self.cache = DocCache(ttl=3600)  # 1 hour TTL
    
    async def lookup(self, api_call: str, language: str) -> Optional[APIDoc]:
        """Lookup API documentation with caching."""
        pass
    
    def verify_usage(self, api_call: str, actual_usage: str) -> Dict[str, Any]:
        """Verify if API is being used correctly."""
        pass
```

#### Documentation Sources
- Python: Official docs API + pypistats
- JavaScript: MDN Web Docs API
- React: Parsed from official docs
- Node.js: nodejs.org JSON API

### 2.4 Proactive Engine

#### Purpose
Orchestrate all proactive features and manage intervention timing.

#### Interface
```python
from typing import List, Optional
from dataclasses import dataclass
from queue import PriorityQueue

@dataclass
class Intervention:
    priority: int
    type: str
    message: str
    fix: Optional[str]
    documentation: Optional[str]
    
class ProactiveEngine:
    def __init__(self):
        self.intervention_queue = PriorityQueue()
        self.cooldown_manager = CooldownManager()
        self.user_preferences = UserPreferences()
    
    def handle_event(self, event: ProcessedEvent, analysis: AnalysisResult):
        """Process event and determine interventions."""
        pass
    
    def create_intervention(self, issue: CodePattern) -> Optional[Intervention]:
        """Create intervention for detected issue."""
        pass
    
    def should_notify(self, intervention: Intervention) -> bool:
        """Check if user should be notified now."""
        pass
```

#### Intervention Rules
- Max 5 notifications per 5 minutes
- Critical issues bypass cooldown
- Group related issues together
- Respect user's focus mode

### 2.5 Fix Generator

#### Purpose
Generate concrete, applicable code fixes for detected issues.

#### Interface
```python
from typing import List, Optional, Dict
from dataclasses import dataclass

@dataclass
class CodeFix:
    description: str
    old_code: str
    new_code: str
    explanation: str
    confidence: float
    references: List[str]

class FixGenerator:
    def generate_fix(
        self, 
        issue: CodePattern, 
        context: Dict[str, Any]
    ) -> Optional[CodeFix]:
        """Generate fix for the issue."""
        pass
    
    def validate_fix(self, fix: CodeFix, full_code: str) -> bool:
        """Validate that fix won't break existing code."""
        pass
```

#### Fix Templates
```python
FIX_TEMPLATES = {
    "hardcoded_secret": {
        "template": """
import os
from dotenv import load_dotenv

load_dotenv()

# Replace hardcoded value with environment variable
{variable_name} = os.getenv('{env_var_name}')
""",
        "env_instruction": "Add {env_var_name}={value} to .env file"
    },
    
    "missing_error_handling": {
        "template": """
try:
    {original_code}
except {exception_type} as e:
    # Log error and handle gracefully
    logger.error(f"Error in {function_name}: {e}")
    {error_handling}
"""
    }
}
```

### 2.6 Injection System

#### Purpose
Deliver suggestions and fixes to the user through non-intrusive channels.

#### Interface
```python
from typing import List, Optional
from dataclasses import dataclass

@dataclass
class Suggestion:
    id: str
    title: str
    description: str
    fix: Optional[CodeFix]
    priority: str
    actions: List[str]

class InjectionSystem:
    def __init__(self):
        self.delivery_channels = {
            'terminal': TerminalNotifier(),
            'file': FileBasedNotifier(),
            'inline': InlineCommentInjector()
        }
    
    def deliver_suggestion(self, suggestion: Suggestion) -> bool:
        """Deliver suggestion through appropriate channel."""
        pass
    
    def apply_fix(self, suggestion_id: str) -> bool:
        """Apply the fix associated with suggestion."""
        pass
```

---

## 3. Data Models

### 3.1 Session Context
```python
@dataclass
class SessionContext:
    session_id: str
    project_root: str
    active_files: List[str]
    recent_changes: List[FileChange]
    detected_patterns: List[CodePattern]
    api_usage: Dict[str, List[str]]
    error_history: List[ErrorEvent]
    intervention_history: List[Intervention]
```

### 3.2 Configuration Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "proactive": {
      "type": "object",
      "properties": {
        "enabled": {"type": "boolean"},
        "intervention_threshold": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "cooldown_seconds": {"type": "integer"},
        "max_suggestions_per_minute": {"type": "integer"},
        "channels": {
          "type": "array",
          "items": {
            "enum": ["terminal", "file", "inline"]
          }
        }
      }
    }
  }
}
```

---

## 4. API Specifications

### 4.1 Internal APIs

#### Event Processing API
```python
POST /api/v1/events
Content-Type: application/json

{
  "event_type": "PostToolUse",
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "/src/auth.py",
    "old_string": "password = 'admin123'",
    "new_string": "password = os.getenv('ADMIN_PASSWORD')"
  },
  "timestamp": "2025-01-12T10:30:00Z"
}

Response:
{
  "event_id": "evt_123",
  "interventions": [
    {
      "id": "int_456",
      "type": "security",
      "message": "Hardcoded password detected",
      "fix_available": true
    }
  ]
}
```

#### Documentation Lookup API
```python
GET /api/v1/docs/lookup?api=requests.get&lang=python

Response:
{
  "found": true,
  "api": {
    "name": "requests.get",
    "version": "2.31.0",
    "signature": "get(url, params=None, **kwargs)",
    "parameters": [...],
    "deprecated": false
  }
}
```

### 4.2 Gemini Integration

#### Enhanced Prompt Structure
```python
GEMINI_ANALYSIS_PROMPT = """
You are an expert code reviewer with deep knowledge of {language} best practices.

Analyze the following code change:
- File: {file_path}
- Change Type: {change_type}
- Code:
```{language}
{code_content}
```

Previous Context:
{session_context}

Identify:
1. Potential bugs or errors
2. Security vulnerabilities
3. Performance issues
4. Best practice violations
5. Deprecated API usage

For each issue found, provide:
- Severity (critical/high/medium/low)
- Specific location
- Clear explanation
- Concrete fix with code

Format response as JSON.
"""
```

---

## 5. Performance Specifications

### 5.1 Latency Requirements
- Event processing: < 50ms
- Pattern detection: < 100ms
- Documentation lookup: < 500ms (cached: < 10ms)
- Fix generation: < 2s
- End-to-end suggestion: < 3s

### 5.2 Resource Limits
- Memory usage: < 200MB baseline, < 500MB peak
- CPU usage: < 5% idle, < 25% active
- Disk cache: < 100MB
- Network: < 1MB/min average

### 5.3 Scalability
- Support 1000+ events/minute
- Handle projects with 10,000+ files
- Cache 1000+ API documentation entries

---

## 6. Security Considerations

### 6.1 Code Analysis Security
- Sandboxed execution for pattern matching
- No execution of user code
- Sanitization of all inputs

### 6.2 API Key Management
- Encrypted storage of API keys
- Separate keys for each service
- Rate limiting and quota management

### 6.3 Privacy
- No code sent to external services without consent
- Local analysis preferred over cloud
- Configurable data retention

---

## 7. Error Handling

### 7.1 Graceful Degradation
```python
class ServiceDegradation:
    def __init__(self):
        self.fallback_chain = [
            LocalAnalysis(),      # Try local first
            CachedResults(),      # Use cache if available  
            BasicPatterns(),      # Basic pattern matching
            DisableFeature()      # Disable if all fail
        ]
```

### 7.2 Error Recovery
- Automatic retry with exponential backoff
- Circuit breaker for external services
- Detailed error logging and reporting

---

## 8. Testing Specifications

### 8.1 Unit Test Coverage
- Minimum 90% code coverage
- All public APIs tested
- Edge cases documented

### 8.2 Integration Test Scenarios
1. Full event flow from hook to suggestion
2. Multi-language project analysis
3. High-volume event processing
4. Network failure recovery
5. Cache invalidation

### 8.3 Performance Benchmarks
```python
# benchmark_suite.py
benchmarks = [
    ("process_simple_edit", 50),      # 50ms target
    ("analyze_complex_file", 200),    # 200ms target
    ("generate_security_fix", 1000),  # 1s target
    ("lookup_cached_doc", 10),        # 10ms target
]
```

---

## 9. Deployment Specifications

### 9.1 Dependencies
```
# requirements-v2.txt
fastapi>=0.104.0
aiohttp>=3.9.0
redis>=5.0.0  # For distributed caching
scikit-learn>=1.3.0  # For ML features
pydantic>=2.5.0
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.12.0
mypy>=1.8.0
```

### 9.2 Configuration Files
- `.ai-buddy/config/proactive.json` - Main configuration
- `.ai-buddy/config/patterns.yaml` - Pattern definitions
- `.ai-buddy/config/fix_templates.json` - Fix templates

### 9.3 Migration Plan
1. Backward compatible with v1.0
2. Feature flags for gradual rollout
3. Data migration for existing sessions

---

## Document History
- v1.0 - Initial technical specification (January 2025)
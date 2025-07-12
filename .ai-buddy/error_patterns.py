"""Error detection patterns for proactive monitoring.

This module defines patterns to detect common errors in real-time
and provides suggestions for fixing them.
"""

import re
from typing import Dict, List, Optional, Tuple, NamedTuple
from enum import Enum
from dataclasses import dataclass


class ErrorSeverity(Enum):
    """Severity levels for detected errors."""
    
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Categories of errors we can detect."""
    
    SYNTAX = "syntax"
    RUNTIME = "runtime"
    IMPORT = "import"
    TYPE = "type"
    SECURITY = "security"
    PERFORMANCE = "performance"
    STYLE = "style"


@dataclass
class ErrorPattern:
    """Definition of an error pattern."""
    
    name: str
    category: ErrorCategory
    severity: ErrorSeverity
    pattern: re.Pattern
    description: str
    suggestion_template: str
    extract_groups: List[str] = None
    
    def match(self, text: str) -> Optional[re.Match]:
        """Check if pattern matches the text."""
        return self.pattern.search(text)
    
    def get_suggestion(self, match: re.Match) -> str:
        """Generate suggestion based on match groups."""
        if self.extract_groups and match.groups():
            group_dict = {}
            for i, group_name in enumerate(self.extract_groups):
                if i < len(match.groups()):
                    group_dict[group_name] = match.group(i + 1)
            return self.suggestion_template.format(**group_dict)
        return self.suggestion_template


class ErrorDetection(NamedTuple):
    """Result of error detection."""
    
    error_type: str
    category: ErrorCategory
    severity: ErrorSeverity
    line_number: Optional[int]
    description: str
    suggestion: str
    context: str


# Define common error patterns
ERROR_PATTERNS = [
    # Python Syntax Errors
    ErrorPattern(
        name="python_syntax_error",
        category=ErrorCategory.SYNTAX,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'File "([^"]+)", line (\d+).*?\^.*?(\w+Error): (.+)', re.DOTALL),
        description="Python syntax error detected",
        suggestion_template="Fix syntax error in {file} at line {line}: {error_type} - {message}",
        extract_groups=["file", "line", "error_type", "message"]
    ),
    
    # Import Errors
    ErrorPattern(
        name="import_error",
        category=ErrorCategory.IMPORT,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'ModuleNotFoundError: No module named [\'"]([^\'"]+)[\'"]'),
        description="Missing module import",
        suggestion_template="Install missing module: pip install {module}",
        extract_groups=["module"]
    ),
    
    ErrorPattern(
        name="import_attribute_error",
        category=ErrorCategory.IMPORT,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'ImportError: cannot import name [\'"]([^\'"]+)[\'"] from [\'"]([^\'"]+)[\'"]'),
        description="Cannot import specific attribute",
        suggestion_template="Check if '{name}' exists in module '{module}' or fix the import statement",
        extract_groups=["name", "module"]
    ),
    
    # Type Errors
    ErrorPattern(
        name="type_error_none",
        category=ErrorCategory.TYPE,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'AttributeError: \'NoneType\' object has no attribute [\'"]([^\'"]+)[\'"]'),
        description="Attempting to access attribute on None",
        suggestion_template="Add null check before accessing '.{attribute}' - the object might be None",
        extract_groups=["attribute"]
    ),
    
    ErrorPattern(
        name="type_error_operation",
        category=ErrorCategory.TYPE,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'TypeError: unsupported operand type\(s\) for ([^:]+): \'([^\']+)\' and \'([^\']+)\''),
        description="Type mismatch in operation",
        suggestion_template="Cannot use {operation} between {type1} and {type2} - ensure compatible types",
        extract_groups=["operation", "type1", "type2"]
    ),
    
    # Runtime Errors
    ErrorPattern(
        name="division_by_zero",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'ZeroDivisionError: division by zero'),
        description="Division by zero error",
        suggestion_template="Add check for zero before division: if denominator != 0:"
    ),
    
    ErrorPattern(
        name="index_error",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'IndexError: list index out of range'),
        description="List index out of range",
        suggestion_template="Check list length before accessing: if index < len(list):"
    ),
    
    ErrorPattern(
        name="key_error",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'KeyError: [\'"]([^\'"]+)[\'"]'),
        description="Dictionary key not found",
        suggestion_template="Use dict.get('{key}', default) or check if '{key}' in dict",
        extract_groups=["key"]
    ),
    
    # Security Issues
    ErrorPattern(
        name="hardcoded_secret",
        category=ErrorCategory.SECURITY,
        severity=ErrorSeverity.CRITICAL,
        pattern=re.compile(r'(password|api_key|secret|token)\s*=\s*["\']([^"\']+)["\']', re.IGNORECASE),
        description="Hardcoded secret detected",
        suggestion_template="Move {secret_type} to environment variable or config file",
        extract_groups=["secret_type", "value"]
    ),
    
    # Performance Issues
    ErrorPattern(
        name="memory_error",
        category=ErrorCategory.PERFORMANCE,
        severity=ErrorSeverity.CRITICAL,
        pattern=re.compile(r'MemoryError'),
        description="Out of memory error",
        suggestion_template="Optimize memory usage: process data in chunks, use generators, or increase memory limit"
    ),
    
    # Common Python Issues
    ErrorPattern(
        name="indentation_error",
        category=ErrorCategory.SYNTAX,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'IndentationError: (.+)'),
        description="Indentation error",
        suggestion_template="Fix indentation: {message}",
        extract_groups=["message"]
    ),
    
    ErrorPattern(
        name="name_error",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'NameError: name [\'"]([^\'"]+)[\'"] is not defined'),
        description="Undefined variable",
        suggestion_template="Variable '{name}' is not defined - check spelling or import it",
        extract_groups=["name"]
    ),
    
    # File Operations
    ErrorPattern(
        name="file_not_found",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'FileNotFoundError: \[Errno 2\] No such file or directory: [\'"]([^\'"]+)[\'"]'),
        description="File not found",
        suggestion_template="File '{file}' not found - check path or create the file",
        extract_groups=["file"]
    ),
    
    ErrorPattern(
        name="permission_denied",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.ERROR,
        pattern=re.compile(r'PermissionError: \[Errno 13\] Permission denied: [\'"]([^\'"]+)[\'"]'),
        description="Permission denied",
        suggestion_template="Permission denied for '{file}' - check file permissions or run with appropriate privileges",
        extract_groups=["file"]
    ),
    
    # Test Failures
    ErrorPattern(
        name="assertion_error",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.WARNING,
        pattern=re.compile(r'AssertionError: (.+)'),
        description="Test assertion failed",
        suggestion_template="Assertion failed: {message} - update test or fix implementation",
        extract_groups=["message"]
    ),
    
    ErrorPattern(
        name="pytest_failed",
        category=ErrorCategory.RUNTIME,
        severity=ErrorSeverity.WARNING,
        pattern=re.compile(r'FAILED (.+) - (.+)'),
        description="Pytest test failed",
        suggestion_template="Test {test} failed: {reason}",
        extract_groups=["test", "reason"]
    ),
]


class ErrorDetector:
    """Detects errors in log output using predefined patterns."""
    
    def __init__(self, patterns: List[ErrorPattern] = None):
        """Initialize with error patterns."""
        self.patterns = patterns or ERROR_PATTERNS
        self._line_cache = {}
        
    def detect_errors(self, text: str) -> List[ErrorDetection]:
        """Detect all errors in the given text."""
        errors = []
        lines = text.split('\n')
        
        # First, try to match patterns on the entire text for multiline patterns
        for pattern in self.patterns:
            if pattern.name == "python_syntax_error":
                # This pattern needs multiline matching
                match = pattern.match(text)
                if match:
                    # Extract line number if available
                    line_number = None
                    if 'line' in (pattern.extract_groups or []):
                        try:
                            line_idx = pattern.extract_groups.index('line')
                            if line_idx < len(match.groups()):
                                line_number = int(match.group(line_idx + 1))
                        except (ValueError, IndexError):
                            pass
                    
                    errors.append(ErrorDetection(
                        error_type=pattern.name,
                        category=pattern.category,
                        severity=pattern.severity,
                        line_number=line_number,
                        description=pattern.description,
                        suggestion=pattern.get_suggestion(match),
                        context=match.group(0)  # Full match as context
                    ))
        
        # Then, match line by line for single-line patterns
        for i, line in enumerate(lines):
            for pattern in self.patterns:
                if pattern.name == "python_syntax_error":
                    continue  # Already handled above
                    
                match = pattern.match(line)
                if match:
                    # Extract line number if available
                    line_number = None
                    if 'line' in (pattern.extract_groups or []):
                        try:
                            line_idx = pattern.extract_groups.index('line')
                            if line_idx < len(match.groups()):
                                line_number = int(match.group(line_idx + 1))
                        except (ValueError, IndexError):
                            pass
                    
                    # Get context (surrounding lines)
                    context_start = max(0, i - 2)
                    context_end = min(len(lines), i + 3)
                    context = '\n'.join(lines[context_start:context_end])
                    
                    errors.append(ErrorDetection(
                        error_type=pattern.name,
                        category=pattern.category,
                        severity=pattern.severity,
                        line_number=line_number,
                        description=pattern.description,
                        suggestion=pattern.get_suggestion(match),
                        context=context
                    ))
                    
        return errors
    
    def detect_new_errors(self, text: str, session_id: str) -> List[ErrorDetection]:
        """Detect only new errors not seen before in this session."""
        all_errors = self.detect_errors(text)
        
        # Get cached errors for this session
        cached = self._line_cache.get(session_id, set())
        new_errors = []
        
        for error in all_errors:
            # Create unique key for error
            error_key = f"{error.error_type}:{error.line_number}:{error.context[:50]}"
            if error_key not in cached:
                new_errors.append(error)
                cached.add(error_key)
        
        self._line_cache[session_id] = cached
        return new_errors
    
    def get_suggestions_for_file(self, file_content: str, file_path: str) -> List[ErrorDetection]:
        """Analyze a file for potential issues (static analysis)."""
        suggestions = []
        
        # Check for common code smells and issues
        lines = file_content.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Check for hardcoded secrets
            if re.search(r'(password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']', line, re.IGNORECASE):
                suggestions.append(ErrorDetection(
                    error_type="potential_hardcoded_secret",
                    category=ErrorCategory.SECURITY,
                    severity=ErrorSeverity.WARNING,
                    line_number=i,
                    description="Potential hardcoded secret",
                    suggestion="Consider moving this to environment variables",
                    context=line.strip()
                ))
            
            # Check for print statements in production code
            if re.match(r'^\s*print\s*\(', line) and not file_path.endswith('_test.py'):
                suggestions.append(ErrorDetection(
                    error_type="print_statement",
                    category=ErrorCategory.STYLE,
                    severity=ErrorSeverity.INFO,
                    line_number=i,
                    description="Print statement in code",
                    suggestion="Consider using logging instead of print",
                    context=line.strip()
                ))
            
            # Check for bare except
            if re.match(r'^\s*except\s*:', line):
                suggestions.append(ErrorDetection(
                    error_type="bare_except",
                    category=ErrorCategory.STYLE,
                    severity=ErrorSeverity.WARNING,
                    line_number=i,
                    description="Bare except clause",
                    suggestion="Specify exception type: except Exception:",
                    context=line.strip()
                ))
                
        return suggestions
"""
Smart Context Management
Intelligently selects and prioritizes files based on user queries.
"""

import os
import re
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import subprocess


class QueryIntent(str, Enum):
    """Types of user query intents."""
    DEBUG = "debug"              # Fixing errors, debugging issues
    FEATURE = "feature"          # Adding new functionality
    EXPLAIN = "explain"          # Understanding code
    REFACTOR = "refactor"        # Improving code structure
    TEST = "test"                # Writing or fixing tests
    DOCUMENT = "document"        # Creating documentation
    CONFIG = "config"            # Configuration/setup
    GENERAL = "general"          # General questions


@dataclass
class FileRelevance:
    """Represents a file's relevance to a query."""
    path: str
    score: float
    reasons: List[str]
    size: int
    last_modified: datetime
    

class QueryAnalyzer:
    """Analyzes user queries to extract intent and keywords."""
    
    # Intent patterns
    INTENT_PATTERNS = {
        QueryIntent.DEBUG: [
            r'\b(error|bug|fail|failing|broken|fix|issue|problem|crash|exception)\b',
            r'\b(not work|doesn\'t work|won\'t work)\b',
            r'\b(debug|troubleshoot|investigate)\b'
        ],
        QueryIntent.FEATURE: [
            r'\b(add|implement|create|build|feature|new|enhance|extend)\b',
            r'\b(want|need|should|could)\s+\w+\s+(to|that|which)',
            r'\b(functionality|capability)\b'
        ],
        QueryIntent.EXPLAIN: [
            r'\b(what|how|why|explain|understand|tell me|show me)\b',
            r'\b(does|work|mean|purpose)\b',
            r'\b(documentation|docs|comment)\b'
        ],
        QueryIntent.REFACTOR: [
            r'\b(refactor|improve|optimize|clean|reorganize|restructure)\b',
            r'\b(better|efficient|readable|maintainable)\b',
            r'\b(code smell|duplicate|redundant)\b'
        ],
        QueryIntent.TEST: [
            r'\b(test|testing|unit test|integration test|pytest|jest)\b',
            r'\b(coverage|mock|assert|fixture)\b',
            r'\b(tdd|test-driven)\b'
        ],
        QueryIntent.CONFIG: [
            r'\b(config|configure|setup|install|deploy|environment)\b',
            r'\b(settings|options|parameters)\b',
            r'\b(docker|kubernetes|ci|cd|github actions)\b'
        ]
    }
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def analyze(self, query: str) -> Tuple[QueryIntent, List[str], Dict[str, float]]:
        """
        Analyze a user query.
        
        Returns:
            - Intent of the query
            - List of keywords
            - Dictionary of technical terms with confidence scores
        """
        query_lower = query.lower()
        
        # Detect intent
        intent = self._detect_intent(query_lower)
        
        # Extract keywords
        keywords = self._extract_keywords(query)
        
        # Extract technical terms
        tech_terms = self._extract_technical_terms(query)
        
        self.logger.info(f"Query analysis - Intent: {intent}, Keywords: {keywords[:5]}")
        
        return intent, keywords, tech_terms
    
    def _detect_intent(self, query_lower: str) -> QueryIntent:
        """Detect the primary intent of the query."""
        intent_scores = {}
        
        for intent, patterns in self.INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            intent_scores[intent] = score
        
        # Return intent with highest score, or GENERAL if no matches
        if max(intent_scores.values()) > 0:
            return max(intent_scores, key=intent_scores.get)
        return QueryIntent.GENERAL
    
    def _extract_keywords(self, query: str) -> List[str]:
        """Extract important keywords from the query."""
        # Remove common words
        stop_words = {
            'the', 'is', 'at', 'which', 'on', 'a', 'an', 'and', 'or', 'but',
            'in', 'with', 'to', 'for', 'of', 'as', 'by', 'that', 'this',
            'it', 'from', 'be', 'are', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
            'might', 'must', 'can', 'need', 'my', 'our', 'we', 'i', 'me'
        }
        
        # Tokenize and filter
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Also extract quoted strings
        quoted = re.findall(r'"([^"]+)"', query) + re.findall(r"'([^']+)'", query)
        keywords.extend(quoted)
        
        # Extract file paths
        paths = re.findall(r'[\w/\\.-]+\.\w+', query)
        keywords.extend(paths)
        
        return list(set(keywords))  # Remove duplicates
    
    def _extract_technical_terms(self, query: str) -> Dict[str, float]:
        """Extract technical terms with confidence scores."""
        tech_terms = {}
        
        # Function/method names (camelCase or snake_case)
        for match in re.finditer(r'\b([a-z_]+[A-Z]\w+|[a-z]+_[a-z_]+)\b', query):
            tech_terms[match.group(1)] = 0.8
        
        # File extensions
        for match in re.finditer(r'\b\w+\.(\w+)\b', query):
            ext = match.group(1)
            if ext in ['py', 'js', 'ts', 'jsx', 'tsx', 'java', 'cpp', 'c', 'h', 'go', 'rs']:
                tech_terms[f"*.{ext}"] = 0.9
        
        # Class names (PascalCase)
        for match in re.finditer(r'\b[A-Z][a-z]+[A-Z]\w*\b', query):
            tech_terms[match.group(0)] = 0.7
        
        # Module/package names
        for match in re.finditer(r'\b(import|from|require)\s+(\S+)', query):
            tech_terms[match.group(2)] = 0.9
        
        return tech_terms


class FileScorer:
    """Scores files based on relevance to a query."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.logger = logging.getLogger(__name__)
        self._file_cache = {}  # Cache file metadata
        
    def score_files(
        self, 
        intent: QueryIntent,
        keywords: List[str],
        tech_terms: Dict[str, float],
        max_files: int = 50
    ) -> List[FileRelevance]:
        """
        Score all project files based on relevance.
        
        Returns top scored files up to max_files.
        """
        scored_files = []
        
        # Get all text files in project
        for file_path in self._get_project_files():
            score, reasons = self._score_single_file(
                file_path, intent, keywords, tech_terms
            )
            
            if score > 0:
                try:
                    stat = file_path.stat()
                    scored_files.append(FileRelevance(
                        path=str(file_path.relative_to(self.project_root)),
                        score=score,
                        reasons=reasons,
                        size=stat.st_size,
                        last_modified=datetime.fromtimestamp(stat.st_mtime)
                    ))
                except Exception as e:
                    self.logger.warning(f"Could not stat file {file_path}: {e}")
        
        # Sort by score descending
        scored_files.sort(key=lambda x: x.score, reverse=True)
        
        return scored_files[:max_files]
    
    def _get_project_files(self) -> List[Path]:
        """Get all relevant files in the project."""
        files = []
        
        # Use git if available
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    files.append(self.project_root / line)
                    
        except subprocess.CalledProcessError:
            # Fallback to walking directory
            exclude_dirs = {'.git', '__pycache__', 'node_modules', '.venv', 'venv'}
            
            for root, dirs, filenames in os.walk(self.project_root):
                dirs[:] = [d for d in dirs if d not in exclude_dirs]
                
                for filename in filenames:
                    if not filename.startswith('.'):
                        files.append(Path(root) / filename)
        
        return files
    
    def _score_single_file(
        self,
        file_path: Path,
        intent: QueryIntent,
        keywords: List[str],
        tech_terms: Dict[str, float]
    ) -> Tuple[float, List[str]]:
        """Score a single file."""
        score = 0.0
        reasons = []
        
        relative_path = str(file_path.relative_to(self.project_root))
        
        # 1. Check filename matches
        filename_lower = file_path.name.lower()
        for keyword in keywords:
            if keyword.lower() in filename_lower:
                score += 10
                reasons.append(f"Filename contains '{keyword}'")
        
        # 2. Check path matches
        path_lower = relative_path.lower()
        for keyword in keywords:
            if keyword.lower() in path_lower:
                score += 5
                reasons.append(f"Path contains '{keyword}'")
        
        # 3. Intent-based scoring
        score_mod, reason = self._score_by_intent(file_path, intent)
        if score_mod > 0:
            score += score_mod
            reasons.append(reason)
        
        # 4. Technical term matching
        for term, confidence in tech_terms.items():
            if term.startswith('*.'):
                # File extension match
                if file_path.suffix == term[1:]:
                    score += 5 * confidence
                    reasons.append(f"File type matches {term}")
            elif term in relative_path:
                score += 8 * confidence
                reasons.append(f"Path contains technical term '{term}'")
        
        # 5. Recency bonus
        try:
            stat = file_path.stat()
            age_hours = (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).total_seconds() / 3600
            if age_hours < 1:
                score += 5
                reasons.append("Modified in last hour")
            elif age_hours < 24:
                score += 3
                reasons.append("Modified in last 24 hours")
            elif age_hours < 168:  # 1 week
                score += 1
                reasons.append("Modified in last week")
        except:
            pass
        
        return score, reasons
    
    def _score_by_intent(self, file_path: Path, intent: QueryIntent) -> Tuple[float, str]:
        """Score based on intent-specific patterns."""
        name_lower = file_path.name.lower()
        
        if intent == QueryIntent.TEST:
            if 'test' in name_lower or file_path.parts[-2] == 'tests':
                return 15, "Test file"
        
        elif intent == QueryIntent.CONFIG:
            config_files = {'.env', 'config', 'settings', 'docker', 'compose', '.yml', '.yaml', '.json', '.toml'}
            if any(cf in name_lower for cf in config_files):
                return 12, "Configuration file"
        
        elif intent == QueryIntent.DOCUMENT:
            if file_path.suffix in ['.md', '.rst', '.txt'] or 'readme' in name_lower:
                return 10, "Documentation file"
        
        elif intent == QueryIntent.DEBUG:
            if 'log' in name_lower or 'error' in name_lower:
                return 8, "Log/error related file"
        
        return 0, ""


class SmartContextBuilder:
    """Builds optimized context for Gemini based on query analysis."""
    
    def __init__(self, project_root: str, max_context_size: int = 100000):
        self.project_root = Path(project_root)
        self.max_context_size = max_context_size
        self.analyzer = QueryAnalyzer()
        self.scorer = FileScorer(project_root)
        self.logger = logging.getLogger(__name__)
        
    def build_context(
        self,
        query: str,
        session_log: str,
        conversation_history: str,
        changes_log: Optional[str] = None
    ) -> Tuple[str, List[str]]:
        """
        Build optimized context for the query.
        
        Returns:
            - The built context string
            - List of included file paths
        """
        # Analyze query
        intent, keywords, tech_terms = self.analyzer.analyze(query)
        
        # Score and rank files
        scored_files = self.scorer.score_files(intent, keywords, tech_terms)
        
        # Determine context size based on intent
        base_size = self._get_base_context_size(intent)
        
        # Build context
        context_parts = []
        included_files = []
        current_size = 0
        
        # Always include conversation history
        if conversation_history:
            context_parts.append(f"### RECENT CONVERSATION ###\n{conversation_history}\n")
            current_size += len(conversation_history)
        
        # Include session log for debugging
        if intent == QueryIntent.DEBUG and session_log:
            log_excerpt = session_log[-10000:]  # Last 10KB
            context_parts.append(f"### RECENT SESSION LOG ###\n{log_excerpt}\n")
            current_size += len(log_excerpt)
        
        # Include changes log if available
        if changes_log:
            context_parts.append(f"### RECENT CHANGES ###\n{changes_log}\n")
            current_size += len(changes_log)
        
        # Add files based on relevance
        context_parts.append("### RELEVANT PROJECT FILES ###\n")
        
        for file_rel in scored_files:
            if current_size >= base_size:
                break
                
            file_path = self.project_root / file_rel.path
            
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                
                # For large files, include only relevant portions
                if len(content) > 5000 and file_rel.score < 50:
                    content = self._extract_relevant_portions(content, keywords, tech_terms)
                
                if content:
                    file_header = f"\n--- FILE: {file_rel.path} (score: {file_rel.score:.1f}) ---\n"
                    file_footer = f"\n--- END FILE: {file_rel.path} ---\n"
                    
                    file_section = file_header + content + file_footer
                    
                    if current_size + len(file_section) <= self.max_context_size:
                        context_parts.append(file_section)
                        included_files.append(file_rel.path)
                        current_size += len(file_section)
                        
                        self.logger.info(f"Included {file_rel.path} - Score: {file_rel.score:.1f}, Reasons: {file_rel.reasons[:2]}")
                        
            except Exception as e:
                self.logger.error(f"Error reading {file_rel.path}: {e}")
        
        # Log context stats
        self.logger.info(f"Built context - Intent: {intent}, Size: {current_size:,} bytes, Files: {len(included_files)}")
        
        return ''.join(context_parts), included_files
    
    def _get_base_context_size(self, intent: QueryIntent) -> int:
        """Get base context size based on intent."""
        size_map = {
            QueryIntent.DEBUG: 80000,      # Need more context for debugging
            QueryIntent.FEATURE: 60000,    # Medium context for features
            QueryIntent.EXPLAIN: 40000,    # Less context for explanations
            QueryIntent.REFACTOR: 70000,   # More context to understand structure
            QueryIntent.TEST: 50000,       # Medium context for tests
            QueryIntent.CONFIG: 30000,     # Less context for config
            QueryIntent.GENERAL: 50000     # Default medium context
        }
        return size_map.get(intent, 50000)
    
    def _extract_relevant_portions(
        self,
        content: str,
        keywords: List[str],
        tech_terms: Dict[str, float]
    ) -> str:
        """Extract relevant portions from a large file."""
        lines = content.split('\n')
        relevant_lines = []
        context_window = 10  # Lines before/after match
        
        # Find lines with matches
        match_indices = set()
        for i, line in enumerate(lines):
            line_lower = line.lower()
            
            # Check keywords
            for keyword in keywords:
                if keyword.lower() in line_lower:
                    for j in range(max(0, i - context_window), 
                                 min(len(lines), i + context_window + 1)):
                        match_indices.add(j)
            
            # Check tech terms
            for term in tech_terms:
                if term in line:
                    for j in range(max(0, i - context_window),
                                 min(len(lines), i + context_window + 1)):
                        match_indices.add(j)
        
        # Build relevant portions
        if match_indices:
            sorted_indices = sorted(match_indices)
            current_section = []
            last_index = -context_window - 1
            
            for idx in sorted_indices:
                if idx > last_index + context_window:
                    # Start new section
                    if current_section:
                        relevant_lines.extend(current_section)
                        relevant_lines.append("\n... [truncated] ...\n")
                    current_section = [f"{idx + 1}: {lines[idx]}"]
                else:
                    current_section.append(f"{idx + 1}: {lines[idx]}")
                last_index = idx
            
            if current_section:
                relevant_lines.extend(current_section)
            
            return '\n'.join(relevant_lines)
        
        # If no matches, return first and last portions
        if len(lines) > 100:
            return '\n'.join(lines[:50] + ["\n... [truncated] ...\n"] + lines[-50:])
        
        return content
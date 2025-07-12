"""
File Operations Module
Handles structured file creation/update/delete operations from Gemini responses.
"""

import os
import logging
from pathlib import Path
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field, validator
import json


class FileOperation(str, Enum):
    """Types of file operations supported."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    

class FileCommand(BaseModel):
    """Single file operation command."""
    operation: FileOperation
    path: str = Field(description="Relative path from project root")
    content: Optional[str] = Field(None, description="File content for create/update operations")
    description: str = Field(description="What this file does or why this operation is needed")
    overwrite: bool = Field(False, description="Whether to overwrite existing file (for create operations)")
    
    @validator('path')
    def validate_path(cls, v):
        """Ensure path is safe and relative."""
        # Remove any leading slashes
        v = v.lstrip('/')
        
        # Check for dangerous patterns
        if '..' in v or v.startswith('/'):
            raise ValueError(f"Invalid path: {v}")
        
        # Check for system files
        dangerous_patterns = ['.git/', '.env', '.ssh', 'node_modules/']
        for pattern in dangerous_patterns:
            if pattern in v:
                raise ValueError(f"Cannot modify system files: {v}")
                
        return v


class FileOperationResponse(BaseModel):
    """Response containing file operations to perform."""
    files: List[FileCommand] = Field(description="List of file operations to perform")
    summary: str = Field(description="Summary of what was done or will be done")
    warnings: Optional[List[str]] = Field(None, description="Any warnings or notes for the user")


class FileOperationResult(BaseModel):
    """Result of executing file operations."""
    success: bool
    operations_performed: List[dict]
    errors: List[str]
    files_created: List[str]
    files_updated: List[str]
    files_deleted: List[str]


class FileOperationExecutor:
    """Safely executes file operations within project boundaries."""
    
    def __init__(self, project_root: str, max_file_size: int = 1024 * 1024):  # 1MB default
        self.project_root = Path(project_root).resolve()
        self.max_file_size = max_file_size
        self.logger = logging.getLogger(__name__)
        
    def validate_and_resolve_path(self, relative_path: str) -> Path:
        """Validate and resolve a path within project boundaries."""
        # Resolve the full path
        full_path = (self.project_root / relative_path).resolve()
        
        # Ensure it's within project root
        if not str(full_path).startswith(str(self.project_root)):
            raise ValueError(f"Path escapes project root: {relative_path}")
            
        return full_path
    
    def execute_operations(self, operations: FileOperationResponse) -> FileOperationResult:
        """Execute a set of file operations."""
        result = FileOperationResult(
            success=True,
            operations_performed=[],
            errors=[],
            files_created=[],
            files_updated=[],
            files_deleted=[]
        )
        
        for file_cmd in operations.files:
            try:
                self._execute_single_operation(file_cmd, result)
            except Exception as e:
                error_msg = f"Error with {file_cmd.path}: {str(e)}"
                self.logger.error(error_msg)
                result.errors.append(error_msg)
                result.success = False
                
        return result
    
    def _execute_single_operation(self, file_cmd: FileCommand, result: FileOperationResult):
        """Execute a single file operation."""
        safe_path = self.validate_and_resolve_path(file_cmd.path)
        
        if file_cmd.operation == FileOperation.CREATE:
            self._handle_create(file_cmd, safe_path, result)
        elif file_cmd.operation == FileOperation.UPDATE:
            self._handle_update(file_cmd, safe_path, result)
        elif file_cmd.operation == FileOperation.DELETE:
            self._handle_delete(file_cmd, safe_path, result)
            
    def _handle_create(self, file_cmd: FileCommand, safe_path: Path, result: FileOperationResult):
        """Handle file creation."""
        if safe_path.exists() and not file_cmd.overwrite:
            raise ValueError(f"File already exists: {file_cmd.path}")
            
        if not file_cmd.content:
            raise ValueError("Content is required for create operation")
            
        # Check content size
        if len(file_cmd.content.encode('utf-8')) > self.max_file_size:
            raise ValueError(f"File content exceeds maximum size of {self.max_file_size} bytes")
            
        # Create directories if needed
        safe_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file
        safe_path.write_text(file_cmd.content, encoding='utf-8')
        
        self.logger.info(f"Created file: {file_cmd.path}")
        result.files_created.append(file_cmd.path)
        result.operations_performed.append({
            'operation': 'create',
            'path': file_cmd.path,
            'description': file_cmd.description
        })
        
    def _handle_update(self, file_cmd: FileCommand, safe_path: Path, result: FileOperationResult):
        """Handle file update."""
        if not safe_path.exists():
            raise ValueError(f"File does not exist: {file_cmd.path}")
            
        if not file_cmd.content:
            raise ValueError("Content is required for update operation")
            
        # Check content size
        if len(file_cmd.content.encode('utf-8')) > self.max_file_size:
            raise ValueError(f"File content exceeds maximum size of {self.max_file_size} bytes")
            
        # Backup existing content (in memory)
        original_content = safe_path.read_text(encoding='utf-8')
        
        # Write new content
        safe_path.write_text(file_cmd.content, encoding='utf-8')
        
        self.logger.info(f"Updated file: {file_cmd.path}")
        result.files_updated.append(file_cmd.path)
        result.operations_performed.append({
            'operation': 'update',
            'path': file_cmd.path,
            'description': file_cmd.description,
            'original_size': len(original_content),
            'new_size': len(file_cmd.content)
        })
        
    def _handle_delete(self, file_cmd: FileCommand, safe_path: Path, result: FileOperationResult):
        """Handle file deletion."""
        if not safe_path.exists():
            raise ValueError(f"File does not exist: {file_cmd.path}")
            
        # Safety check - don't delete directories
        if safe_path.is_dir():
            raise ValueError(f"Cannot delete directory: {file_cmd.path}")
            
        # Delete the file
        safe_path.unlink()
        
        self.logger.info(f"Deleted file: {file_cmd.path}")
        result.files_deleted.append(file_cmd.path)
        result.operations_performed.append({
            'operation': 'delete',
            'path': file_cmd.path,
            'description': file_cmd.description
        })


def detect_file_operation_request(user_question: str) -> bool:
    """Detect if the user is asking for file creation/modification."""
    keywords = [
        'create file', 'make file', 'generate file',
        'write file', 'add file', 'new file',
        'create documentation', 'generate documentation',
        'write readme', 'make readme', 'create readme',
        'update file', 'modify file', 'change file',
        'delete file', 'remove file',
        'generate config', 'create config',
        'write test', 'create test', 'generate test',
        'create script', 'write script', 'generate script'
    ]
    
    question_lower = user_question.lower()
    return any(keyword in question_lower for keyword in keywords)
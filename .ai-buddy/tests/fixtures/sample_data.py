"""Sample data for testing AI Buddy."""

# Sample Gemini API responses
SAMPLE_GEMINI_RESPONSES = {
    "simple": "This is a simple response from Gemini.",
    
    "code_suggestion": """I see the issue in your authentication code. Here's the fix:

```python
def authenticate_user(username, password):
    # Validate inputs first
    if not username or not password:
        raise ValueError("Username and password required")
    
    # Hash password before comparison
    hashed_pw = hash_password(password)
    user = db.get_user(username)
    
    if user and user.password_hash == hashed_pw:
        return generate_token(user)
    return None
```

This ensures proper validation and secure password handling.""",
    
    "file_operation": {
        "summary": "Creating configuration files for the project",
        "operations": [
            {
                "operation": "create",
                "path": "config/settings.py",
                "content": """# Application settings
DEBUG = False
SECRET_KEY = 'your-secret-key'
DATABASE_URL = 'postgresql://localhost/myapp'
""",
                "description": "Main settings file",
                "overwrite": False
            },
            {
                "operation": "create",
                "path": "config/__init__.py",
                "content": "# Config module",
                "description": "Make config a package",
                "overwrite": False
            }
        ],
        "warnings": ["Remember to update SECRET_KEY before deployment"]
    },
    
    "error_response": "I encountered an error processing your request. Please try again."
}

# Sample file contents for testing
SAMPLE_FILE_CONTENTS = {
    "python_simple": """def hello_world():
    print("Hello, World!")

if __name__ == "__main__":
    hello_world()
""",
    
    "python_class": """class UserService:
    def __init__(self, database):
        self.db = database
    
    def get_user(self, user_id):
        return self.db.query(User).filter_by(id=user_id).first()
    
    def create_user(self, username, email):
        user = User(username=username, email=email)
        self.db.add(user)
        self.db.commit()
        return user
""",
    
    "javascript": """export class AuthManager {
    constructor(apiClient) {
        this.apiClient = apiClient;
        this.token = null;
    }
    
    async login(username, password) {
        try {
            const response = await this.apiClient.post('/auth/login', {
                username,
                password
            });
            this.token = response.data.token;
            return response.data;
        } catch (error) {
            console.error('Login failed:', error);
            throw error;
        }
    }
}
""",
    
    "markdown": """# Project Documentation

## Overview
This project implements a robust authentication system.

## Features
- User registration and login
- JWT token-based authentication
- Password hashing with bcrypt
- Session management

## Installation
```bash
pip install -r requirements.txt
python setup.py install
```

## Usage
```python
from auth import AuthManager

auth = AuthManager()
token = auth.login(username, password)
```
""",
    
    "json_config": """{
    "app": {
        "name": "AI Buddy Test",
        "version": "1.0.0",
        "debug": true
    },
    "database": {
        "host": "localhost",
        "port": 5432,
        "name": "testdb"
    },
    "features": {
        "authentication": true,
        "logging": true,
        "monitoring": false
    }
}
""",
    
    "test_file": """import pytest
from auth import authenticate_user

def test_authenticate_valid_user():
    result = authenticate_user("testuser", "password123")
    assert result is not None
    assert "token" in result

def test_authenticate_invalid_user():
    result = authenticate_user("invalid", "wrong")
    assert result is None

def test_authenticate_empty_credentials():
    with pytest.raises(ValueError):
        authenticate_user("", "")
"""
}

# Sample conversation histories
SAMPLE_CONVERSATIONS = [
    {
        "basic": [
            {
                "timestamp": "2025-01-12T10:00:00",
                "user": "How do I implement user authentication?",
                "assistant": "To implement user authentication, you'll need to: 1) Set up a user model, 2) Implement password hashing, 3) Create login/logout endpoints, 4) Generate and verify JWT tokens."
            },
            {
                "timestamp": "2025-01-12T10:05:00",
                "user": "Can you show me an example?",
                "assistant": "Here's a basic example:\n```python\nfrom flask import Flask, request\nfrom werkzeug.security import check_password_hash\nimport jwt\n\n@app.route('/login', methods=['POST'])\ndef login():\n    username = request.json['username']\n    password = request.json['password']\n    # Verify credentials and return token\n```"
            }
        ]
    },
    {
        "debugging": [
            {
                "timestamp": "2025-01-12T11:00:00",
                "user": "I'm getting a KeyError in my login function",
                "assistant": "A KeyError usually means you're trying to access a dictionary key that doesn't exist. Check if the request data contains all expected fields. You can use .get() with a default value to avoid the error."
            },
            {
                "timestamp": "2025-01-12T11:02:00",
                "user": "It works now! The issue was missing 'username' in the request",
                "assistant": "Great! For better error handling, consider validating request data before processing:\n```python\nif not all(k in request.json for k in ['username', 'password']):\n    return jsonify({'error': 'Missing required fields'}), 400\n```"
            }
        ]
    }
]

# Sample session logs
SAMPLE_SESSION_LOGS = {
    "normal": """Script started on 2025-01-12 10:00:00 -0500
$ claude "Help me implement user authentication"

I'll help you implement user authentication. Let me create a basic authentication module.

First, let's install the required dependencies:
$ pip install bcrypt pyjwt

Now, let's create the authentication module:
$ cat > auth.py << 'EOF'
import bcrypt
import jwt
from datetime import datetime, timedelta

class AuthManager:
    def __init__(self, secret_key):
        self.secret_key = secret_key
    
    def hash_password(self, password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
    def verify_password(self, password, hashed):
        return bcrypt.checkpw(password.encode('utf-8'), hashed)
    
    def generate_token(self, user_id):
        payload = {
            'user_id': user_id,
            'exp': datetime.utcnow() + timedelta(hours=24)
        }
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
EOF

$ echo "Authentication module created successfully!"
Authentication module created successfully!

Script done on 2025-01-12 10:05:00 -0500
""",
    
    "with_errors": """Script started on 2025-01-12 14:00:00 -0500
$ python app.py
Traceback (most recent call last):
  File "app.py", line 5, in <module>
    from auth import AuthManager
ImportError: cannot import name 'AuthManager' from 'auth'

$ ls -la auth.py
-rw-r--r-- 1 user user 0 Jan 12 13:00 auth.py

$ echo "File is empty, let me fix that"
File is empty, let me fix that

$ claude "The auth.py file is empty, can you help me implement it?"

I see the issue. Let me help you implement the auth.py file properly:

$ cat > auth.py << 'EOF'
class AuthManager:
    def __init__(self):
        self.users = {}
    
    def register(self, username, password):
        if username in self.users:
            raise ValueError("User already exists")
        self.users[username] = password
        return True
EOF

$ python app.py
Server starting on port 5000...

Script done on 2025-01-12 14:10:00 -0500
"""
}

# Sample project structures
SAMPLE_PROJECT_STRUCTURES = {
    "minimal": [
        "main.py",
        "requirements.txt",
        "README.md"
    ],
    
    "web_app": [
        "app.py",
        "requirements.txt",
        "config.py",
        "models/",
        "models/__init__.py",
        "models/user.py",
        "models/post.py",
        "routes/",
        "routes/__init__.py",
        "routes/auth.py",
        "routes/api.py",
        "templates/",
        "templates/index.html",
        "templates/login.html",
        "static/",
        "static/css/style.css",
        "static/js/app.js",
        "tests/",
        "tests/test_auth.py",
        "tests/test_models.py",
        ".gitignore",
        "README.md"
    ],
    
    "cli_tool": [
        "setup.py",
        "requirements.txt",
        "README.md",
        "LICENSE",
        "cli_tool/",
        "cli_tool/__init__.py",
        "cli_tool/__main__.py",
        "cli_tool/commands.py",
        "cli_tool/utils.py",
        "cli_tool/config.py",
        "tests/",
        "tests/test_commands.py",
        "tests/test_utils.py",
        ".gitignore"
    ]
}

# Sample error messages
SAMPLE_ERRORS = {
    "api_error": "Error: Failed to connect to Gemini API. Please check your API key.",
    "file_not_found": "Error: File 'config.json' not found in project directory.",
    "permission_denied": "Error: Permission denied when trying to write to '/etc/config'.",
    "syntax_error": "SyntaxError: invalid syntax (line 42)",
    "import_error": "ImportError: No module named 'missing_module'",
    "timeout_error": "TimeoutError: Request timed out after 60 seconds"
}

# Sample API keys (for testing - not real keys)
SAMPLE_API_KEYS = {
    "valid_format": "AIzaSyD-1234567890abcdefghijklmnopqrstuv",
    "invalid_format": "invalid-key-format",
    "empty": "",
    "placeholder": "YOUR_GEMINI_KEY_GOES_HERE"
}
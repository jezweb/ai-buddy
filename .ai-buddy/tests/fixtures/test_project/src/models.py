"""Database models."""

from datetime import datetime

# Simplified models for testing (no actual database)
class Model:
    """Base model class."""
    def __init__(self):
        self.id = None
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

class User(Model):
    """User model."""
    def __init__(self, username, email):
        super().__init__()
        self.username = username
        self.email = email
        self.password_hash = None
        self.is_active = True
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(Model):
    """Post model."""
    def __init__(self, title, content, author_id):
        super().__init__()
        self.title = title
        self.content = content
        self.author_id = author_id
        self.published = False
    
    def __repr__(self):
        return f'<Post {self.title}>'

# Mock database object
class MockDB:
    def __init__(self):
        self.users = {}
        self.posts = {}
    
    def init_app(self, app):
        """Initialize with Flask app."""
        app.db = self

db = MockDB()
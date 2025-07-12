"""Authentication module."""

from flask import Blueprint, request, jsonify
import bcrypt
import jwt
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

class AuthManager:
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.users = {}  # In-memory storage for demo
    
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
    
    def verify_token(self, token):
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload['user_id']
        except jwt.InvalidTokenError:
            return None

# Global auth manager instance
auth_manager = AuthManager('test-secret-key')

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if username in auth_manager.users:
        return jsonify({'error': 'User already exists'}), 409
    
    hashed_pw = auth_manager.hash_password(password)
    auth_manager.users[username] = hashed_pw
    
    return jsonify({'message': 'User created successfully'}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400
    
    if username not in auth_manager.users:
        return jsonify({'error': 'Invalid credentials'}), 401
    
    if not auth_manager.verify_password(password, auth_manager.users[username]):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    token = auth_manager.generate_token(username)
    return jsonify({'token': token}), 200
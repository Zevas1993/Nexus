# backend/app/api/auth_routes.py
from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
# Adjust import paths assuming this file is in backend/app/api/
from app import db, bcrypt, login_manager # Import login_manager to use the unauthorized handler
from app.models.user import User

auth_bp = Blueprint('api_auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({"error": "Missing required fields (username, email, password)"}), 400

    existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
    if existing_user:
        return jsonify({"error": "Username or email already exists"}), 409

    try:
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user) # Optionally log in user immediately after signup
        # Ensure user.to_dict() exists and works
        return jsonify({"message": "User created successfully", "user": user.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error during signup: {e}") # Log error
        return jsonify({"error": "Failed to create user"}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    identifier = data.get('identifier') # Can be username or email
    password = data.get('password')

    if not identifier or not password:
        return jsonify({"error": "Missing identifier or password"}), 400

    user = User.query.filter((User.username == identifier) | (User.email == identifier)).first()

    if user and user.check_password(password):
        login_user(user, remember=True) # Add remember=True if needed
        # Ensure user.to_dict() exists and works
        return jsonify({"message": "Login successful", "user": user.to_dict()}), 200
    else:
        # Generic error for security
        return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/logout', methods=['POST'])
@login_required # Ensures user is logged in before they can log out
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route('/check_auth', methods=['GET'])
@login_required # The decorator handles the check
def check_auth():
    # If @login_required passes, user is authenticated
    # Ensure current_user.to_dict() exists and works
    return jsonify({"message": "Authenticated", "user": current_user.to_dict()}), 200

# Note: The @login_manager.unauthorized_handler should be defined in
# the main app factory (__init__.py) where login_manager is initialized,
# not typically within a blueprint file itself.
# It was correctly placed in the provided backend/app/__init__.py snippet.

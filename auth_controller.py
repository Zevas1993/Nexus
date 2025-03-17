"""
Authentication controller for Nexus AI Assistant.

This module provides authentication-related API endpoints.
"""

from typing import Dict, Any
import logging
from flask import Blueprint, request, jsonify, session, redirect, url_for
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from ....infrastructure.context import ApplicationContext
from ....infrastructure.security.auth import JwtAuthenticationService
from ....infrastructure.security.oauth import OAuthService
from ....application.services.user_service import UserService

logger = logging.getLogger(__name__)

# Create blueprint
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def create_auth_routes(app_context: ApplicationContext) -> Blueprint:
    """Create authentication routes.
    
    Args:
        app_context: Application context
        
    Returns:
        Flask Blueprint with authentication routes
    """
    # Get services
    auth_service = app_context.get_service(JwtAuthenticationService)
    oauth_service = app_context.get_service(OAuthService)
    user_service = app_context.get_service(UserService)
    
    @auth_bp.route('/google/callback', methods=['POST'])
    def google_callback():
        """Handle Google OAuth callback."""
        id_token_str = request.form.get('id_token')
        if not id_token_str:
            return jsonify({"status": "error", "message": "No token provided"}), 400
        
        try:
            # Verify token
            user_info = oauth_service.verify_google_token(id_token_str)
            if not user_info:
                return jsonify({"status": "error", "message": "Invalid token"}), 401
            
            # Get or create user
            email = user_info['email']
            user = user_service.get_user_by_email(email)
            
            if not user:
                # Create new user
                user = user_service.create_user({
                    'email': email,
                    'name': user_info.get('name', ''),
                    'picture': user_info.get('picture', ''),
                    'google_id': user_info['sub']
                })
            
            # Generate JWT token
            token = auth_service.generate_token(user['id'], {
                'email': email,
                'name': user.get('name', '')
            })
            
            # Set session variables
            session['user_id'] = user['id']
            session['user_email'] = email
            session['google_id_token'] = id_token_str
            
            return jsonify({
                "status": "success",
                "message": "Logged in successfully",
                "token": token,
                "user": {
                    "id": user['id'],
                    "email": email,
                    "name": user.get('name', '')
                }
            })
        except Exception as e:
            logger.error(f"Google login failed: {str(e)}")
            return jsonify({"status": "error", "message": f"Login failed: {str(e)}"}), 401
    
    @auth_bp.route('/logout', methods=['POST'])
    def logout():
        """Log out user."""
        # Clear session
        session.pop('user_id', None)
        session.pop('user_email', None)
        session.pop('google_id_token', None)
        session.pop('session_id', None)
        
        return jsonify({
            "status": "success",
            "message": "Logged out successfully"
        })
    
    @auth_bp.route('/user', methods=['GET'])
    def get_current_user():
        """Get current user information."""
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Not authenticated"}), 401
        
        user_id = session['user_id']
        user = user_service.get_user(user_id)
        
        if not user:
            # Clear invalid session
            session.pop('user_id', None)
            session.pop('user_email', None)
            return jsonify({"status": "error", "message": "User not found"}), 404
        
        return jsonify({
            "status": "success",
            "user": {
                "id": user['id'],
                "email": user.get('email', ''),
                "name": user.get('name', '')
            }
        })
    
    return auth_bp

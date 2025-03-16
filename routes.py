"""
Web routes for Nexus AI Assistant.

This module defines the web interface routes.
"""

from typing import Dict, Any
import logging
from flask import Blueprint, render_template, session, redirect, url_for, request
from ...infrastructure.context import ApplicationContext
from ...application.services.session_service import SessionService

logger = logging.getLogger(__name__)

# Create blueprint
web_bp = Blueprint('web', __name__, template_folder='templates', static_folder='static')

def create_web_routes(app_context: ApplicationContext) -> Blueprint:
    """Create web interface routes.
    
    Args:
        app_context: Application context
        
    Returns:
        Flask Blueprint with web routes
    """
    # Get services
    session_service = app_context.get_service(SessionService)
    
    @web_bp.route('/', methods=['GET'])
    def index():
        """Render index page."""
        # Check if user is logged in
        logged_in = 'user_id' in session
        
        # Get current session title if logged in
        current_title = "Untitled"
        if logged_in and 'session_id' in session:
            user_id = session['user_id']
            session_id = session['session_id']
            session_data = session_service.get_session(session_id, user_id)
            if session_data:
                current_title = session_data.get('title', 'Untitled')
        
        # Render template
        return render_template(
            'index.html',
            logged_in=logged_in,
            current_title=current_title,
            google_client_id=app_context.config.get('GOOGLE_CLIENT_ID', '')
        )
    
    @web_bp.route('/sessions', methods=['GET'])
    def sessions():
        """Render sessions page."""
        # Check if user is logged in
        if 'user_id' not in session:
            return redirect(url_for('web.index'))
        
        # Get user sessions
        user_id = session['user_id']
        user_sessions = session_service.get_user_sessions(user_id)
        
        # Render template
        return render_template(
            'sessions.html',
            sessions=user_sessions
        )
    
    @web_bp.route('/session/<session_id>', methods=['GET'])
    def view_session(session_id):
        """Render session view page."""
        # Check if user is logged in
        if 'user_id' not in session:
            return redirect(url_for('web.index'))
        
        # Get session data
        user_id = session['user_id']
        session_data = session_service.get_session(session_id, user_id)
        
        if not session_data:
            return redirect(url_for('web.sessions'))
        
        # Update Flask session
        session['session_id'] = session_id
        
        # Render template
        return render_template(
            'session.html',
            session_data=session_data
        )
    
    @web_bp.route('/plugins', methods=['GET'])
    def plugins():
        """Render plugins page."""
        # Check if user is logged in
        if 'user_id' not in session:
            return redirect(url_for('web.index'))
        
        # Render template
        return render_template('plugins.html')
    
    @web_bp.route('/settings', methods=['GET'])
    def settings():
        """Render settings page."""
        # Check if user is logged in
        if 'user_id' not in session:
            return redirect(url_for('web.index'))
        
        # Render template
        return render_template('settings.html')
    
    return web_bp

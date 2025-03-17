"""
API routes for Nexus AI Assistant.

This module defines the API routes and endpoints.
"""

from typing import Dict, Any
import logging
from flask import Blueprint, request, jsonify, session, Response
import time
import json
from ...infrastructure.context import ApplicationContext
from ...application.orchestrator import Orchestrator
from ...application.services.user_service import UserService
from ...application.services.session_service import SessionService
from ...application.services.system_service import SystemService
from ...domain.plugins.loader import PluginLoaderService
from ...domain.voice.recognition import RecognitionService
from ...domain.voice.synthesis import SynthesisService
from ...application.tasks.celery_app import celery_app, long_running_task

logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')

# Event queue for SSE
event_queue = []

def add_event(event: str):
    """Add event to event queue.
    
    Args:
        event: Event string
    """
    timestamp = time.strftime('%H:%M:%S')
    event_queue.append(f"{timestamp} - {event}")
    logger.info(f"Event added: {event}")

def create_api_routes(app_context: ApplicationContext) -> Blueprint:
    """Create API routes.
    
    Args:
        app_context: Application context
        
    Returns:
        Flask Blueprint with API routes
    """
    # Get services
    orchestrator = Orchestrator(app_context)
    user_service = app_context.get_service(UserService)
    session_service = app_context.get_service(SessionService)
    system_service = app_context.get_service(SystemService)
    plugin_loader = app_context.get_service(PluginLoaderService)
    
    # Initialize services
    user_service.initialize()
    session_service.initialize()
    system_service.initialize()
    
    @api_bp.route('/process', methods=['POST'])
    def process_request():
        """Process user request."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get request data
        data = request.get_json()
        if not data or "request" not in data:
            return jsonify({"status": "error", "message": "Invalid request"}), 400
        
        # Process request
        user_id = session['user_id']
        session_id = session.get('session_id', 'default')
        result = orchestrator.process_request(
            data["request"], 
            user_id, 
            session_id, 
            data.get("params", {})
        )
        
        # Add message to session if successful
        if result.get("status") == "success" and session_id != 'default':
            session_service.add_message(
                session_id,
                user_id,
                {
                    "role": "user",
                    "content": data["request"]
                }
            )
            
            session_service.add_message(
                session_id,
                user_id,
                {
                    "role": "assistant",
                    "content": result.get("response", "")
                }
            )
        
        return jsonify(result)
    
    @api_bp.route('/status', methods=['GET'])
    def system_status():
        """Get system status."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get system stats
        stats = system_service.get_system_stats()
        health = system_service.check_health()
        
        return jsonify({
            "status": "success",
            "system_stats": stats,
            "health": health
        })
    
    @api_bp.route('/monitor', methods=['GET'])
    def monitor_stream():
        """Monitor event stream."""
        # Check authentication
        if 'user_id' not in session:
            return Response("Unauthorized", status=401)
        
        def event_stream():
            """Generate SSE events."""
            while True:
                if event_queue:
                    event = event_queue.pop(0)
                    yield f"data: {event}\n\n"
                else:
                    time.sleep(0.1)
        
        return Response(event_stream(), mimetype="text/event-stream")
    
    @api_bp.route('/session', methods=['POST'])
    def create_session():
        """Create new session."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get request data
        data = request.get_json() or {}
        title = data.get("title", "Untitled")
        
        # Create session
        user_id = session['user_id']
        session_data = session_service.create_session(user_id, title)
        
        # Update Flask session
        session['session_id'] = session_data["id"]
        
        return jsonify({
            "status": "success",
            "session": session_data
        })
    
    @api_bp.route('/session/<session_id>', methods=['GET'])
    def get_session(session_id):
        """Get session by ID."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get session
        user_id = session['user_id']
        session_data = session_service.get_session(session_id, user_id)
        
        if not session_data:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        return jsonify({
            "status": "success",
            "session": session_data
        })
    
    @api_bp.route('/session/<session_id>', methods=['PUT'])
    def update_session(session_id):
        """Update session."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get request data
        data = request.get_json() or {}
        
        # Update session
        user_id = session['user_id']
        session_data = session_service.update_session(session_id, user_id, data)
        
        if not session_data:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        return jsonify({
            "status": "success",
            "session": session_data
        })
    
    @api_bp.route('/session/<session_id>', methods=['DELETE'])
    def delete_session(session_id):
        """Delete session."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Delete session
        user_id = session['user_id']
        deleted = session_service.delete_session(session_id, user_id)
        
        if not deleted:
            return jsonify({"status": "error", "message": "Session not found"}), 404
        
        # Update Flask session if current session was deleted
        if session.get('session_id') == session_id:
            session.pop('session_id', None)
        
        return jsonify({
            "status": "success",
            "message": "Session deleted"
        })
    
    @api_bp.route('/sessions', methods=['GET'])
    def get_sessions():
        """Get all sessions for user."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get sessions
        user_id = session['user_id']
        sessions = session_service.get_user_sessions(user_id)
        
        return jsonify({
            "status": "success",
            "sessions": sessions
        })
    
    @api_bp.route('/plugins', methods=['GET'])
    def get_plugins():
        """Get available plugins."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get plugins
        plugins = plugin_loader.registry.get_all_plugin_info()
        
        return jsonify({
            "status": "success",
            "plugins": plugins
        })
    
    @api_bp.route('/voice/listen', methods=['POST'])
    def listen():
        """Listen for speech."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get recognition service
        recognition_service = app_context.get_service(RecognitionService)
        
        # Listen for speech
        result = recognition_service.process("")
        
        if result.get("status") == "error" or not result.get("success", False):
            return jsonify({
                "status": "error",
                "message": result.get("error", "Could not understand audio")
            }), 400
        
        return jsonify({
            "status": "success",
            "text": result.get("text", "")
        })
    
    @api_bp.route('/voice/speak', methods=['POST'])
    def speak():
        """Synthesize speech."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get request data
        data = request.get_json() or {}
        text = data.get("text")
        
        if not text:
            return jsonify({"status": "error", "message": "No text provided"}), 400
        
        # Get synthesis service
        synthesis_service = app_context.get_service(SynthesisService)
        
        # Synthesize speech
        result = synthesis_service.process(text, wait=False)
        
        if result.get("status") == "error" or not result.get("success", False):
            return jsonify({
                "status": "error",
                "message": result.get("error", "Could not synthesize speech")
            }), 400
        
        return jsonify({
            "status": "success",
            "message": "Speaking..."
        })
    
    @api_bp.route('/task', methods=['POST'])
    def create_task():
        """Create background task."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get request data
        data = request.get_json() or {}
        
        # Create task
        task = long_running_task.delay(data)
        
        return jsonify({
            "status": "success",
            "task_id": task.id
        })
    
    @api_bp.route('/task_status/<task_id>', methods=['GET'])
    def get_task_status(task_id):
        """Get task status."""
        # Check authentication
        if 'user_id' not in session:
            return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
        # Get task
        task = celery_app.AsyncResult(task_id)
        
        if task.state == 'PENDING':
            response = {
                'status': task.state,
                'result': None
            }
        elif task.state == 'FAILURE':
            response = {
                'status': task.state,
                'result': str(task.info)
            }
        else:
            response = {
                'status': task.state,
                'result': task.info
            }
        
        return jsonify(response)
    
    return api_bp

"""
Main application file for Nexus AI Assistant with improved architecture.

Features:
- Google OAuth login
- Session title review and session management
- Hybrid local/cloud AI processing
- Enhanced RAG system for improved context handling
- Dynamic plugin controls
"""
from flask import Flask, request, jsonify, render_template, Response, redirect, url_for, session
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import asyncio
import os
import logging
import time
from collections import deque
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
import json

# Nexus imports
from nexus.infrastructure.context import ApplicationContext
from nexus.infrastructure.security.auth import JwtAuthenticationService
from nexus.infrastructure.performance.caching import RedisCacheService
from nexus.application.orchestrator import Orchestrator
from nexus.domain.language.language_model_service import LanguageModelService
from nexus.domain.system.system_service import SystemManagementService
from nexus.domain.capability import CapabilityService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "sqlite:///app.db")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "default_secret_key")
app.config['GOOGLE_CLIENT_ID'] = os.getenv("GOOGLE_CLIENT_ID", "YOUR_GOOGLE_CLIENT_ID.apps.googleusercontent.com")
app.config['HF_API_TOKEN'] = os.getenv("HF_API_TOKEN", "YOUR_HF_TOKEN")
app.config['CORS_ALLOWED_ORIGINS'] = os.getenv("CORS_ALLOWED_ORIGINS", "*")

# Create extensions
db = SQLAlchemy(app)
limiter = Limiter(lambda: session.get('user_email', get_remote_address()), app=app, default_limits=["10 per minute"])
CORS(app)

# Initialize application context with Flask config
app_context = ApplicationContext(app.config)

# Import configuration
from config import Config
config = Config()

# Event queue for monitoring
event_queue = deque(maxlen=100)

def add_event(event: str):
    """Add an event to the event queue."""
    event_queue.append(f"{time.strftime('%H:%M:%S')} - {event}")
    logger.info(f"Event added: {event}")

# Event loop for async operations
def get_or_create_event_loop():
    """Get the current event loop or create a new one."""
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

# Application initialization
with app.app_context():
    # Initialize database
    db.create_all()
    
    # Initialize application context
    app_context.initialize()
    
    # Get core services
    auth_service = app_context.get_service(JwtAuthenticationService)
    
    # Initialize Manus AI capabilities
    capability_config = {
        "anthropic": {
            "api_key": config.get("ANTHROPIC_API_KEY", ""),
            "default_model": "claude-3-5-sonnet"
        },
        "openai": {
            "api_key": config.get("OPENAI_API_KEY", ""),
            "default_model": "gpt-4o"
        },
        "browserless": {
            "api_key": config.get("BROWSERLESS_API_KEY", "")
        },
        "pinecone": {
            "api_key": config.get("PINECONE_API_KEY", ""),
            "environment": config.get("PINECONE_ENVIRONMENT", ""),
            "index_name": config.get("PINECONE_INDEX_NAME", "nexus-embeddings")
        },
        "default_text_provider": config.get("DEFAULT_TEXT_PROVIDER", ""),
        "default_code_provider": config.get("DEFAULT_CODE_PROVIDER", ""),
        "default_web_provider": config.get("DEFAULT_WEB_PROVIDER", ""),
        "default_vector_provider": config.get("DEFAULT_VECTOR_PROVIDER", ""),
        "enable_local_puppeteer": config.get("ENABLE_LOCAL_PUPPETEER", True),
        "enable_chroma": config.get("ENABLE_CHROMA", True)
    }
    
    capability_service = CapabilityService(capability_config)
    app_context.register_service(CapabilityService, capability_service)
    
    # Create and initialize orchestrator
    orchestrator = Orchestrator(app_context)
    
    # Initialize services asynchronously
    loop = get_or_create_event_loop()
    loop.run_until_complete(asyncio.gather(
        capability_service.initialize(),
        orchestrator.initialize()
    ))
    
    add_event("Application initialized with Manus AI capabilities")

@app.route('/', methods=['GET'])
def index():
    """Render the main index page."""
    if 'google_id_token' not in session:
        return render_template('index.html', logged_in=False, config=app.config)
    return render_template('index.html', logged_in=True, current_title=session.get('session_title', 'Untitled'))

@app.route('/auth/google/callback', methods=['POST'])
def google_callback():
    """Handle Google OAuth callback."""
    id_token_str = request.form.get('id_token')
    try:
        idinfo = id_token.verify_oauth2_token(id_token_str, google_requests.Request(), app.config['GOOGLE_CLIENT_ID'])
        
        # Store user info in session
        session['google_id_token'] = id_token_str
        session['user_email'] = idinfo['email']
        session['user_name'] = idinfo.get('name', '')
        session['session_id'] = str(hash(time.time()))
        session['session_title'] = "Untitled"
        
        add_event(f"User {idinfo['email']} logged in with Google")
        return jsonify({"status": "success", "message": "Logged in successfully"})
    except ValueError as e:
        add_event(f"Google login failed: {str(e)}")
        return jsonify({"status": "error", "message": "Invalid token"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    """Log out the user."""
    session.pop('google_id_token', None)
    session.pop('user_email', None)
    session.pop('user_name', None)
    session.pop('session_id', None)
    session.pop('session_title', None)
    add_event("User logged out")
    return redirect(url_for('index'))

@app.route('/api/v1/process', methods=['POST'])
@limiter.limit("10 per minute")
async def process_request():
    """Process a user request."""
    if 'google_id_token' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data or "request" not in data:
        return jsonify({"status": "error", "message": "Invalid request"}), 400
        
    user_request = data["request"]
    user_email = session['user_email']
    session_id = session.get('session_id', str(hash(time.time())))
    params = data.get("params", {})
    
    add_event(f"Processing request: {user_request[:50]}...")
    
    try:
        # Process request using orchestrator
        result = await orchestrator.process_request(
            user_request, 
            user_email, 
            session_id, 
            params
        )
        
        add_event("Request processed successfully")
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        add_event(f"Error processing request: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error processing request: {str(e)}"
        }), 500

@app.route('/api/v1/status', methods=['GET'])
async def system_status():
    """Get system status information."""
    if 'google_id_token' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    try:
        # Get system management service and check status
        system_service = app_context.get_service(SystemManagementService)
        status = await system_service.process("check status", task="hardware_check")
        
        # Get capability service status
        capability_service = app_context.get_service(CapabilityService)
        capabilities = {}
        
        for cap_type in capability_service.manager.default_providers:
            provider = capability_service.get_default_provider(cap_type)
            capabilities[cap_type.value] = {
                "default_provider": provider,
                "available_providers": capability_service.get_available_providers(cap_type)
            }
        
        return jsonify({
            "status": "success",
            "system_stats": status.get("system_stats", {}),
            "capabilities": capabilities
        })
    except Exception as e:
        logger.error(f"Error getting system status: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error getting system status: {str(e)}"
        }), 500

@app.route('/api/v1/monitor', methods=['GET'])
def monitor_stream():
    """Stream monitoring events using Server-Sent Events."""
    if 'google_id_token' not in session:
        return Response("Unauthorized", status=401)
        
    def event_stream():
        """Generate SSE events from the event queue."""
        while True:
            if event_queue:
                event = event_queue.popleft()
                yield f"data: {event}\n\n"
            else:
                time.sleep(0.1)
                
    return Response(event_stream(), mimetype="text/event-stream")

@app.route('/api/v1/session_titles', methods=['GET'])
def get_session_titles():
    """Get all session titles for the current user."""
    if 'google_id_token' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    try:
        cache_service = app_context.get_service(RedisCacheService)
        user_email = session['user_email']
        
        # Get all session keys for this user
        keys = cache_service.keys(f"session:*:{user_email}")
        
        # Extract titles from keys
        titles = []
        for key in keys:
            parts = key.split(':')
            if len(parts) >= 2:
                title = parts[1]
                if title not in titles:
                    titles.append(title)
                    
        return jsonify({
            "status": "success", 
            "titles": titles
        })
    except Exception as e:
        logger.error(f"Error getting session titles: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error getting session titles: {str(e)}"
        }), 500

@app.route('/api/v1/set_session_title', methods=['POST'])
def set_session_title():
    """Set the title for the current session."""
    if 'google_id_token' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    data = request.get_json()
    if not data or "title" not in data:
        return jsonify({"status": "error", "message": "Title required"}), 400
        
    new_title = data["title"]
    session['session_title'] = new_title
    add_event(f"Session title set to: {new_title}")
    
    return jsonify({
        "status": "success", 
        "message": f"Session title set to {new_title}"
    })

@app.route('/api/v1/capabilities', methods=['GET'])
async def get_capabilities():
    """Get all available AI capabilities and providers."""
    if 'google_id_token' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    try:
        capability_service = app_context.get_service(CapabilityService)
        
        # Get available capabilities
        capabilities = {}
        
        for cap_type in capability_service.manager.default_providers:
            provider = capability_service.get_default_provider(cap_type)
            capabilities[cap_type.value] = {
                "default_provider": provider,
                "available_providers": capability_service.get_available_providers(cap_type)
            }
            
        return jsonify({
            "status": "success",
            "capabilities": capabilities
        })
    except Exception as e:
        logger.error(f"Error getting capabilities: {str(e)}")
        return jsonify({
            "status": "error", 
            "message": f"Error getting capabilities: {str(e)}"
        }), 500

@app.route('/api/v1/plugins', methods=['GET'])
def get_plugins():
    """Get all available plugins."""
    if 'google_id_token' not in session:
        return jsonify({"status": "error", "message": "Unauthorized"}), 401
        
    plugins_dir = os.path.join(os.getcwd(), "plugins")
    plugins = []
    
    # Check if plugins directory exists
    if os.path.exists(plugins_dir):
        for plugin_folder in os.listdir(plugins_dir):
            manifest_path = os.path.join(plugins_dir, plugin_folder, "manifest.json")
            if os.path.exists(manifest_path):
                with open(manifest_path, "r") as f:
                    try:
                        manifest = json.load(f)
                        plugins.append({
                            "name": manifest.get("name", plugin_folder),
                            "description": manifest.get("description", f"{manifest.get('name', plugin_folder)} plugin"),
                            "default_prompt": manifest.get("default_prompt", f"Use {manifest.get('name', plugin_folder)} plugin"),
                            "inputs": manifest.get("inputs", [])
                        })
                    except json.JSONDecodeError:
                        logger.error(f"Invalid JSON in manifest file: {manifest_path}")
    
    return jsonify({
        "status": "success", 
        "plugins": plugins
    })

@app.errorhandler(429)
def ratelimit_handler(e):
    """Handle rate limit errors."""
    add_event(f"Rate limit exceeded: {str(e)}")
    return jsonify({
        "status": "error", 
        "message": "Rate limit exceeded. Please try again later."
    }), 429

@app.errorhandler(500)
def internal_error(e):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(e)}")
    add_event(f"Internal server error: {str(e)}")
    return jsonify({
        "status": "error", 
        "message": "Internal server error. Please try again later."
    }), 500

async def run_update_scheduler():
    """Run periodic tasks such as model and plugin updates."""
    while True:
        try:
            # Optimize resources
            system_service = app_context.get_service(SystemManagementService)
            await system_service.process("optimize resources", task="optimize_resources")
            
            # Update plugins if needed
            if hasattr(orchestrator, 'plugin_loader') and orchestrator.plugin_loader:
                try:
                    await orchestrator.plugin_loader.refresh()
                    add_event("Plugins refreshed")
                except Exception as e:
                    logger.error(f"Error refreshing plugins: {str(e)}")
        except Exception as e:
            logger.error(f"Error in update scheduler: {str(e)}")
            
        # Run once a day
        await asyncio.sleep(86400)

if __name__ == "__main__":
    logger.info(f"Starting Nexus AI Assistant on http://localhost:5000")
    
    # Start update scheduler in background
    loop = get_or_create_event_loop()
    loop.create_task(run_update_scheduler())
    
    # Run the app
    app.run(debug=False, host="localhost", port=5000)

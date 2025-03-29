# backend/run.py
import os
from dotenv import load_dotenv

# Ensure .env is loaded if using 'python run.py'
# Look for .env in the same directory as run.py (which is backend/)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path)
else:
    # Also check parent directory for compatibility if .env is at root
    dotenv_path_root = os.path.join(os.path.dirname(__file__), '..', '.env')
    if os.path.exists(dotenv_path_root):
        load_dotenv(dotenv_path_root)


from app import create_app, app_config # Import from the app package

# Create app instance using the appropriate config
# Ensure FLASK_ENV is considered if set externally, otherwise default
flask_env = os.getenv('FLASK_ENV', 'development')
app = create_app(flask_env) # Pass env to factory if needed, though config loads it

if __name__ == '__main__':
    # Run with Uvicorn for async capabilities if needed later
    # import uvicorn
    # uvicorn.run(app, host="0.0.0.0", port=5000, log_level="info")

    # Or run with Flask's built-in server (good for basic dev)
    # Note: host='0.0.0.0' makes it accessible on your local network
    # Use debug flag from the loaded app_config
    app.run(host='0.0.0.0', port=5000, debug=app_config.DEBUG)

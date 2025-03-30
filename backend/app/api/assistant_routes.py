# backend/app/api/assistant_routes.py
from flask import Blueprint, request, jsonify, Response, current_app # Add Response for streaming later
from flask_login import login_required, current_user
# Import your orchestrator logic (adjust path as needed)
# Assuming assistant_routes.py is in backend/app/api/ and orchestrator is in backend/app/assistant/
from app.assistant.orchestrator import run_assistant_pipeline
import json # For streaming data format

assistant_bp = Blueprint('api_assistant', __name__)

@assistant_bp.route('/chat', methods=['POST'])
@login_required
def chat():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON payload"}), 400

    message = data.get('message')
    session_id = data.get('session_id') # Optional: manage conversation sessions
    stream = data.get('stream', False) # Optional: client can request streaming

    if not message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Call the main orchestrator function/method
        # Pass user info and potentially conversation history/session ID
        response_data = run_assistant_pipeline(
            user_id=current_user.id,
            user_message=message,
            session_id=session_id,
            stream=stream # Pass stream preference to pipeline
            # Add conversation_history if managing it here
        )

        if stream:
            # --- Implement Streaming Response ---
            # If run_assistant_pipeline returns a generator:
            def generate():
                try:
                    for chunk in response_data: # Assuming response_data is the generator
                        # Format chunk according to desired streaming protocol (e.g., SSE)
                        yield f"data: {json.dumps({'response_chunk': chunk})}\n\n"
                    # Optionally send a final 'done' message
                    yield f"data: {json.dumps({'status': 'done'})}\n\n"
                except Exception as e:
                    # Log error during streaming
                    current_app.logger.error(f"Error during assistant response streaming: {e}")
                    # Send an error message through the stream if possible
                    yield f"data: {json.dumps({'error': 'Streaming failed'})}\n\n"

            return Response(generate(), mimetype='text/event-stream')
        else:
            # Simple non-streaming response
            return jsonify({"response": response_data}), 200

    except Exception as e:
        # Log the exception properly in a real app
        current_app.logger.error(f"Error in assistant chat endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred processing your request"}), 500

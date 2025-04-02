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
            # run_assistant_pipeline now returns (generator, initial_turn_object)
            if not isinstance(response_data, tuple) or len(response_data) != 2:
                 current_app.logger.error("Orchestrator did not return expected tuple for streaming.")
                 return jsonify({"error": "Internal error during streaming setup"}), 500

            response_generator, initial_turn = response_data

            # --- Implement Streaming Response & DB Save ---
            def generate():
                full_response = ""
                try:
                    for chunk in response_generator:
                        full_response += chunk
                        # Format chunk according to desired streaming protocol (e.g., SSE)
                        yield f"data: {json.dumps({'response_chunk': chunk})}\n\n"
                    # Optionally send a final 'done' message
                    yield f"data: {json.dumps({'status': 'done'})}\n\n"

                    # --- Save full response to DB after streaming is complete ---
                    # We need app context to interact with the DB
                    with current_app.app_context():
                        try:
                            if initial_turn:
                                initial_turn.assistant_response = full_response
                                db.session.add(initial_turn) # Add the updated turn object
                                db.session.commit()
                                current_app.logger.info(f"Saved streamed conversation turn ID {initial_turn.id} to DB.")
                            else:
                                current_app.logger.error("Initial turn object was None, cannot save streamed response.")
                        except Exception as db_err:
                            current_app.logger.error(f"Failed to save streamed conversation turn to DB: {db_err}", exc_info=True)
                            db.session.rollback()
                    # --- End DB Save ---

                except Exception as e:
                    # Log error during streaming generation
                    current_app.logger.error(f"Error during assistant response streaming generation: {e}", exc_info=True)
                    # Send an error message through the stream if possible
                    yield f"data: {json.dumps({'error': 'Streaming failed during generation'})}\n\n"
                    # Also attempt to rollback DB if initial_turn exists but saving failed before this point
                    with current_app.app_context():
                        db.session.rollback()


            return Response(generate(), mimetype='text/event-stream')
        else:
            # Simple non-streaming response (orchestrator already saved to DB)
            return jsonify({"response": response_data}), 200

    except Exception as e:
        # Log the exception properly in a real app
        current_app.logger.error(f"Error in assistant chat endpoint: {e}", exc_info=True)
        return jsonify({"error": "An internal error occurred processing your request"}), 500

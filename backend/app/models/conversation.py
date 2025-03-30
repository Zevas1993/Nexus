# backend/app/models/conversation.py
# Adjust import path for db
from app import db
import datetime

class ConversationTurn(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Ensure 'user.id' matches the table name (usually lowercase class name) and primary key column
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    session_id = db.Column(db.String(128), index=True, nullable=True) # Allow null session IDs
    user_message = db.Column(db.Text, nullable=False)
    assistant_response = db.Column(db.Text, nullable=True) # Response might not exist yet
    # Optional fields for debugging/analysis
    retrieved_context = db.Column(db.Text, nullable=True)
    tool_used = db.Column(db.String(100), nullable=True)
    tool_input = db.Column(db.Text, nullable=True)
    tool_output = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f'<ConversationTurn {self.id} by User {self.user_id}>'

    def to_dict(self):
         return {
            'id': self.id,
            'user_id': self.user_id,
            'session_id': self.session_id,
            'user_message': self.user_message,
            'assistant_response': self.assistant_response,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
            # Add other fields if needed for API responses
        }

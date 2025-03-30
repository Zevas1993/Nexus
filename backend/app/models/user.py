# backend/app/models/user.py
# Need to adjust import path for db, bcrypt from the app factory file
# Assuming user.py is in backend/app/models/ and __init__.py is in backend/app/
from app import db, bcrypt # Removed login_manager as it's not directly used here
from flask_login import UserMixin
import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    email = db.Column(db.String(120), index=True, unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg') # Example field
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    # Relationship to conversation history
    # Ensure 'ConversationTurn' matches the class name in conversation.py
    conversation_turns = db.relationship('ConversationTurn', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        # Ensure password_hash is not None before checking
        if self.password_hash is None:
            return False
        return bcrypt.check_password_hash(self.password_hash, password)

    def to_dict(self):
        # Simple representation, exclude sensitive info like password hash
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'image_file': self.image_file,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<User {self.username}>'

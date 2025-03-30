# backend/app/api/user_routes.py
from flask import Blueprint, jsonify
from flask_login import login_required, current_user

user_bp = Blueprint('api_users', __name__)

@user_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    # Assuming User model has a to_dict method that excludes sensitive info
    if hasattr(current_user, 'to_dict'):
        return jsonify(current_user.to_dict()), 200
    else:
        # Fallback or error if to_dict is missing
        print(f"Warning: User model (ID: {current_user.id}) missing to_dict method.")
        return jsonify({"error": "User data format error"}), 500

# Add routes for updating profile, etc. later

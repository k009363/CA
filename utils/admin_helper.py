import jwt
from functools import wraps
from flask import request, jsonify, current_app
from bson import ObjectId
from extensions import mongo
from utils.auth_helper import decode_token


def admin_required(f):
    """JWT must be valid AND user.role must be 'admin'."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if not token:
            return jsonify({"error": "Token required"}), 401
        try:
            data = decode_token(token)
            request.user_id = data["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401

        user = mongo.db.users.find_one({"_id": ObjectId(request.user_id)})
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)

    return decorated

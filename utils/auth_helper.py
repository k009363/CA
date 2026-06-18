import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify, current_app


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


def generate_token(user_id: str, is_decoy: bool = False) -> str:
    payload = {
        "user_id": str(user_id),
        "is_decoy": is_decoy,
        "exp": datetime.now(timezone.utc) + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET"], algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, current_app.config["JWT_SECRET"], algorithms=["HS256"])


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        token = auth_header.replace("Bearer ", "").strip()
        if not token:
            return jsonify({"error": "Token required"}), 401
        try:
            data = decode_token(token)
            request.user_id = data["user_id"]
            request.is_decoy = data.get("is_decoy", False)
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)

    return decorated

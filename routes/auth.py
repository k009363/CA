import re
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from extensions import mongo
from utils.auth_helper import hash_password, verify_password, generate_token, token_required
from utils.settings_helper import get_settings

auth_bp = Blueprint("auth", __name__)


def _avatar_url(phone: str, gender: str) -> str:
    from urllib.parse import quote
    s = quote(phone)
    base = "https://api.dicebear.com/7.x"
    if gender == "male":
        return (
            f"{base}/avataaars/svg?seed=m_{s}"
            "&top[]=shortHairShortFlat&top[]=shortHairShortWaved"
            "&top[]=shortHairDreads01&top[]=shortHairFrizzle"
            "&facialHairChance=30&backgroundColor=b6e3f4,c0aede,d1d4f9"
        )
    if gender == "female":
        return (
            f"{base}/avataaars/svg?seed=f_{s}"
            "&top[]=longHairStraight&top[]=longHairBun"
            "&top[]=longHairCurlyFrizz&top[]=longHairBigHair"
            "&facialHairChance=0&backgroundColor=ffdfbf,ffd5dc,ffb7b2"
        )
    return f"{base}/avataaars-neutral/svg?seed={s}&backgroundColor=c0aede,b6e3f4,d1fae5"


def _user_to_dict(user: dict) -> dict:
    return {
        "id": str(user["_id"]),
        "name": user["name"],
        "phone": user["phone"],
        "avatar": user.get("avatar", ""),
        "role": user.get("role", "user"),
    }


@auth_bp.route("/register", methods=["POST"])
def register():
    settings = get_settings()
    if not settings.get("registration_enabled", True):
        return jsonify({"error": "Registrations are currently disabled"}), 503

    data = request.get_json() or {}
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    gender = data.get("gender", "other").strip().lower()
    if gender not in ("male", "female", "other"):
        gender = "other"

    if not all([name, phone, password]):
        return jsonify({"error": "All fields are required"}), 400
    if not re.match(r"^\d{10,15}$", phone):
        return jsonify({"error": "Phone must be 10–15 digits"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if mongo.db.users.find_one({"phone": phone}):
        return jsonify({"error": "Phone number already registered"}), 409

    user_id = mongo.db.users.insert_one(
        {
            "name": name,
            "phone": phone,
            "password": hash_password(password),
            "avatar": _avatar_url(phone, gender),
            "gender": gender,
            "role": "user",
            "banned": False,
            "created_at": datetime.now(timezone.utc),
        }
    ).inserted_id

    return jsonify({"message": "Registered successfully", "user_id": str(user_id)}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    phone = data.get("phone", "").strip()
    password = data.get("password", "")

    if not phone or not password:
        return jsonify({"error": "Phone and password required"}), 400

    user = mongo.db.users.find_one({"phone": phone})
    if not user:
        return jsonify({"error": "Invalid phone or password"}), 401

    is_admin = user.get("role") == "admin"

    # Non-admins are blocked when login is disabled (maintenance mode)
    if not is_admin:
        settings = get_settings()
        if not settings.get("login_enabled", True):
            return jsonify({"error": "Login is temporarily disabled. Please try again later."}), 503

    # Banned users always get decoy
    if user.get("banned", False):
        token = generate_token(user["_id"], is_decoy=True)
        return jsonify({"decoy": True, "token": token, "user": _user_to_dict(user)}), 200

    is_decoy = not verify_password(password, user["password"])
    token = generate_token(user["_id"], is_decoy=is_decoy)

    return jsonify(
        {
            "decoy": is_decoy,
            "token": token,
            "user": _user_to_dict(user),
        }
    ), 200


@auth_bp.route("/search", methods=["GET"])
@token_required
def search_user():
    if request.is_decoy:
        return jsonify({"found": False, "message": "User not found"}), 404

    phone = request.args.get("phone", "").strip()
    if not phone:
        return jsonify({"error": "Phone required"}), 400

    user = mongo.db.users.find_one({"phone": phone})
    if not user or user.get("banned", False):
        return jsonify({"found": False, "message": "User not found"}), 404

    if str(user["_id"]) == request.user_id:
        return jsonify({"found": False, "message": "Cannot chat with yourself"}), 400

    return jsonify({"found": True, "user": _user_to_dict(user)}), 200


@auth_bp.route("/me", methods=["GET"])
@token_required
def get_me():
    user = mongo.db.users.find_one({"_id": ObjectId(request.user_id)})
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(_user_to_dict(user)), 200

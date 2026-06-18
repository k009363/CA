from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, render_template, send_from_directory
from bson import ObjectId
from extensions import mongo
from utils.admin_helper import admin_required
from utils.settings_helper import get_settings, update_settings

admin_bp = Blueprint("admin", __name__)


# ── Serve the admin HTML page ─────────────────────────────────────────────────

@admin_bp.route("", methods=["GET"])
@admin_bp.route("/", methods=["GET"])
def admin_page():
    return render_template("admin.html")


# ── Settings API ─────────────────────────────────────────────────────────────

@admin_bp.route("/api/settings", methods=["GET"])
@admin_required
def get_app_settings():
    s = get_settings()
    return jsonify({
        "registration_enabled": s.get("registration_enabled", True),
        "login_enabled": s.get("login_enabled", True),
        "messaging_enabled": s.get("messaging_enabled", True),
    }), 200


@admin_bp.route("/api/settings", methods=["PUT"])
@admin_required
def update_app_settings():
    data = request.get_json() or {}
    result = update_settings(data)
    return jsonify({
        "registration_enabled": result.get("registration_enabled", True),
        "login_enabled": result.get("login_enabled", True),
        "messaging_enabled": result.get("messaging_enabled", True),
    }), 200


# ── Users API ─────────────────────────────────────────────────────────────────

def _user_row(u: dict) -> dict:
    return {
        "id": str(u["_id"]),
        "name": u.get("name", ""),
        "phone": u.get("phone", ""),
        "role": u.get("role", "user"),
        "banned": bool(u.get("banned", False)),
        "created_at": u.get("created_at", datetime.now(timezone.utc)).isoformat()
        if hasattr(u.get("created_at"), "isoformat")
        else str(u.get("created_at", "")),
    }


@admin_bp.route("/api/users", methods=["GET"])
@admin_required
def list_users():
    users = list(mongo.db.users.find({}, sort=[("created_at", -1)]))
    return jsonify([_user_row(u) for u in users]), 200


@admin_bp.route("/api/users/<user_id>/ban", methods=["PUT"])
@admin_required
def ban_user(user_id):
    data = request.get_json() or {}
    banned = bool(data.get("banned", True))
    try:
        result = mongo.db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"banned": banned}},
        )
    except Exception:
        return jsonify({"error": "Invalid user id"}), 400
    if result.matched_count == 0:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"banned": banned}), 200


@admin_bp.route("/api/users/<user_id>", methods=["DELETE"])
@admin_required
def delete_user(user_id):
    try:
        oid = ObjectId(user_id)
    except Exception:
        return jsonify({"error": "Invalid user id"}), 400

    # Prevent self-delete
    if str(oid) == request.user_id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    result = mongo.db.users.delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"error": "User not found"}), 404

    # Cascade: remove their chats and messages
    mongo.db.chats.delete_many({"participants": str(oid)})
    mongo.db.messages.delete_many({"sender_id": str(oid)})

    return jsonify({"message": "User deleted"}), 200


# ── Stats API ─────────────────────────────────────────────────────────────────

@admin_bp.route("/api/stats", methods=["GET"])
@admin_required
def get_stats():
    return jsonify({
        "total_users": mongo.db.users.count_documents({}),
        "active_chats": mongo.db.chats.count_documents({"status": "accepted"}),
        "pending_chats": mongo.db.chats.count_documents({"status": "pending"}),
        "total_messages": mongo.db.messages.count_documents({}),
        "banned_users": mongo.db.users.count_documents({"banned": True}),
    }), 200

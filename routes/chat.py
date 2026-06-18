from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from extensions import mongo
from utils.auth_helper import token_required
from utils.settings_helper import get_settings

chat_bp = Blueprint("chat", __name__)


def _build_chat_response(chat: dict, current_user_id: str) -> dict:
    participants = chat.get("participants", [])
    other_id = next((p for p in participants if p != current_user_id), None)

    other_user = None
    if other_id:
        raw = mongo.db.users.find_one({"_id": ObjectId(other_id)})
        if raw:
            is_pending = chat.get("status") == "pending"
            initiated_by = chat.get("initiated_by")
            show_full = not is_pending or initiated_by != current_user_id
            other_user = {
                "id": str(raw["_id"]),
                "name": raw["name"],
                "phone": raw["phone"],
                "avatar": raw.get("avatar", "") if show_full else "",
            }

    last_msg = mongo.db.messages.find_one(
        {"chat_id": str(chat["_id"])}, sort=[("created_at", -1)]
    )

    return {
        "id": str(chat["_id"]),
        "other_user": other_user,
        "status": chat.get("status", "pending"),
        "initiated_by": chat.get("initiated_by"),
        "last_message": last_msg.get("content", "") if last_msg else "",
        "last_message_time": last_msg["created_at"].isoformat() if last_msg else chat["created_at"].isoformat(),
        "created_at": chat["created_at"].isoformat(),
    }


@chat_bp.route("", methods=["GET"])
@token_required
def get_chats():
    if request.is_decoy:
        return jsonify([]), 200

    chats = list(
        mongo.db.chats.find({"participants": request.user_id}, sort=[("updated_at", -1)])
    )
    return jsonify([_build_chat_response(c, request.user_id) for c in chats]), 200


@chat_bp.route("", methods=["POST"])
@token_required
def create_chat():
    if request.is_decoy:
        return jsonify({"error": "Unauthorized"}), 403

    settings = get_settings()
    if not settings.get("messaging_enabled", True):
        return jsonify({"error": "Messaging is currently disabled"}), 503

    data = request.get_json() or {}
    receiver_id = data.get("receiver_id", "").strip()
    initial_message = data.get("message", "").strip()

    if not receiver_id:
        return jsonify({"error": "receiver_id required"}), 400
    if not initial_message:
        return jsonify({"error": "initial message required"}), 400

    try:
        receiver = mongo.db.users.find_one({"_id": ObjectId(receiver_id)})
    except Exception:
        return jsonify({"error": "Invalid receiver"}), 400

    if not receiver:
        return jsonify({"error": "Receiver not found"}), 404

    existing = mongo.db.chats.find_one(
        {"participants": {"$all": [request.user_id, receiver_id]}}
    )
    if existing:
        return jsonify(_build_chat_response(existing, request.user_id)), 200

    now = datetime.now(timezone.utc)
    chat_id = mongo.db.chats.insert_one(
        {
            "participants": [request.user_id, receiver_id],
            "status": "pending",
            "initiated_by": request.user_id,
            "created_at": now,
            "updated_at": now,
        }
    ).inserted_id

    mongo.db.messages.insert_one(
        {
            "chat_id": str(chat_id),
            "sender_id": request.user_id,
            "content": initial_message,
            "file": None,
            "created_at": now,
        }
    )

    chat = mongo.db.chats.find_one({"_id": chat_id})
    return jsonify(_build_chat_response(chat, request.user_id)), 201


@chat_bp.route("/<chat_id>/accept", methods=["PUT"])
@token_required
def accept_chat(chat_id):
    if request.is_decoy:
        return jsonify({"error": "Unauthorized"}), 403

    try:
        chat = mongo.db.chats.find_one({"_id": ObjectId(chat_id)})
    except Exception:
        return jsonify({"error": "Invalid chat id"}), 400

    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    if chat.get("initiated_by") == request.user_id:
        return jsonify({"error": "Cannot accept your own request"}), 400
    if request.user_id not in chat.get("participants", []):
        return jsonify({"error": "Not a participant"}), 403

    mongo.db.chats.update_one(
        {"_id": ObjectId(chat_id)},
        {"$set": {"status": "accepted", "updated_at": datetime.now(timezone.utc)}},
    )

    chat = mongo.db.chats.find_one({"_id": ObjectId(chat_id)})
    return jsonify(_build_chat_response(chat, request.user_id)), 200


@chat_bp.route("/<chat_id>", methods=["GET"])
@token_required
def get_chat(chat_id):
    if request.is_decoy:
        return jsonify({"error": "Not found"}), 404

    try:
        chat = mongo.db.chats.find_one({"_id": ObjectId(chat_id)})
    except Exception:
        return jsonify({"error": "Invalid chat id"}), 400

    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    if request.user_id not in chat.get("participants", []):
        return jsonify({"error": "Forbidden"}), 403

    return jsonify(_build_chat_response(chat, request.user_id)), 200

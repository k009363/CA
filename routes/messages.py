from datetime import datetime, timezone
from flask import Blueprint, request, jsonify
from bson import ObjectId
from extensions import mongo
from utils.auth_helper import token_required
from utils.settings_helper import get_settings

messages_bp = Blueprint("messages", __name__)


def _msg_to_dict(msg: dict) -> dict:
    return {
        "id": str(msg["_id"]),
        "chat_id": msg["chat_id"],
        "sender_id": msg["sender_id"],
        "content": msg.get("content", ""),
        "file": msg.get("file"),
        "created_at": msg["created_at"].isoformat(),
    }


@messages_bp.route("/<chat_id>", methods=["GET"])
@token_required
def get_messages(chat_id):
    if request.is_decoy:
        return jsonify([]), 200

    try:
        chat = mongo.db.chats.find_one({"_id": ObjectId(chat_id)})
    except Exception:
        return jsonify({"error": "Invalid chat id"}), 400

    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    if request.user_id not in chat.get("participants", []):
        return jsonify({"error": "Forbidden"}), 403

    msgs = list(mongo.db.messages.find({"chat_id": chat_id}, sort=[("created_at", 1)]))
    return jsonify([_msg_to_dict(m) for m in msgs]), 200


@messages_bp.route("/<chat_id>", methods=["POST"])
@token_required
def send_message(chat_id):
    if request.is_decoy:
        return jsonify({"error": "Unauthorized"}), 403

    settings = get_settings()
    if not settings.get("messaging_enabled", True):
        return jsonify({"error": "Messaging is currently disabled"}), 503

    try:
        chat = mongo.db.chats.find_one({"_id": ObjectId(chat_id)})
    except Exception:
        return jsonify({"error": "Invalid chat id"}), 400

    if not chat:
        return jsonify({"error": "Chat not found"}), 404
    if request.user_id not in chat.get("participants", []):
        return jsonify({"error": "Forbidden"}), 403

    data = request.get_json() or {}
    content = data.get("content", "").strip()
    file_data = data.get("file")

    if not content and not file_data:
        return jsonify({"error": "Message content or file required"}), 400

    now = datetime.now(timezone.utc)
    msg_id = mongo.db.messages.insert_one(
        {
            "chat_id": chat_id,
            "sender_id": request.user_id,
            "content": content,
            "file": file_data,
            "created_at": now,
        }
    ).inserted_id

    mongo.db.chats.update_one({"_id": ObjectId(chat_id)}, {"$set": {"updated_at": now}})

    msg = mongo.db.messages.find_one({"_id": msg_id})
    return jsonify(_msg_to_dict(msg)), 201

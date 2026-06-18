from flask import Blueprint, request, jsonify
from utils.auth_helper import token_required
from utils.cloudinary_helper import upload_file

files_bp = Blueprint("files", __name__)

ALLOWED_MIME_PREFIXES = ("image/", "video/", "audio/", "application/pdf", "application/")
MAX_BYTES = 25 * 1024 * 1024  # 25 MB


@files_bp.route("/upload", methods=["POST"])
@token_required
def upload():
    if request.is_decoy:
        return jsonify({"error": "Unauthorized"}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    file.seek(0, 2)
    size = file.tell()
    file.seek(0)

    if size > MAX_BYTES:
        return jsonify({"error": "File too large (max 25 MB)"}), 413

    mime = file.content_type or ""
    original_name = file.filename

    try:
        result = upload_file(file.stream, original_name)
    except Exception as e:
        return jsonify({"error": f"Upload failed: {str(e)}"}), 500

    return jsonify(
        {
            "url": result["url"],
            "format": result["format"],
            "resource_type": result["resource_type"],
            "name": original_name,
            "mime": mime,
            "bytes": result["bytes"],
        }
    ), 200

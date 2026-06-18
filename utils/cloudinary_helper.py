import cloudinary
import cloudinary.uploader
from flask import current_app


def init_cloudinary():
    cloudinary.config(
        cloud_name=current_app.config["CLOUDINARY_CLOUD_NAME"],
        api_key=current_app.config["CLOUDINARY_API_KEY"],
        api_secret=current_app.config["CLOUDINARY_API_SECRET"],
        secure=True,
    )


def upload_file(file_stream, original_filename: str, folder: str = "chatapp") -> dict:
    init_cloudinary()
    result = cloudinary.uploader.upload(
        file_stream,
        folder=folder,
        resource_type="auto",
        use_filename=True,
        unique_filename=True,
    )
    return {
        "url": result["secure_url"],
        "public_id": result["public_id"],
        "format": result.get("format", ""),
        "resource_type": result["resource_type"],
        "original_filename": original_filename,
        "bytes": result.get("bytes", 0),
    }

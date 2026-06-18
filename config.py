import os
import certifi
from urllib.parse import urlparse, urlunparse
from dotenv import load_dotenv

load_dotenv()


def _ensure_db_name(uri: str, db: str = "chatapp") -> str:
    """
    Flask-PyMongo requires the database name in the URI path.
    Atlas URIs often omit it (path is just '/').  This adds it if missing.
    e.g. 'mongodb+srv://user:pw@host/?opts'  →  'mongodb+srv://user:pw@host/chatapp?opts'
    """
    if not uri:
        return uri
    parsed = urlparse(uri)
    if not parsed.path.strip("/"):           # path is '' or '/'
        parsed = parsed._replace(path=f"/{db}")
        return urlunparse(parsed)
    return uri


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-prod")
    MONGO_URI  = _ensure_db_name(
        os.getenv("MONGO_URI", "mongodb://localhost:27017/chatapp")
    )
    MONGO_TLS_CA_FILE = certifi.where()
    JWT_SECRET          = os.getenv("JWT_SECRET", "jwt-dev-secret")
    JWT_EXPIRY_HOURS    = 24
    CLOUDINARY_CLOUD_NAME   = os.getenv("CLOUDINARY_CLOUD_NAME", "")
    CLOUDINARY_API_KEY      = os.getenv("CLOUDINARY_API_KEY", "")
    CLOUDINARY_API_SECRET   = os.getenv("CLOUDINARY_API_SECRET", "")

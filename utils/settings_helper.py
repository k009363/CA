"""
App-level feature flags stored in MongoDB.
A single document with _id="main" holds all toggles.
"""
from extensions import mongo

_DOC_ID = "main"

_DEFAULTS = {
    "_id": _DOC_ID,
    "registration_enabled": True,
    "login_enabled": True,
    "messaging_enabled": True,
}


def get_settings() -> dict:
    doc = mongo.db.app_settings.find_one({"_id": _DOC_ID})
    if not doc:
        mongo.db.app_settings.insert_one(dict(_DEFAULTS))
        return dict(_DEFAULTS)
    return doc


def update_settings(updates: dict) -> dict:
    allowed = {"registration_enabled", "login_enabled", "messaging_enabled"}
    safe = {k: bool(v) for k, v in updates.items() if k in allowed}
    mongo.db.app_settings.update_one({"_id": _DOC_ID}, {"$set": safe}, upsert=True)
    return get_settings()

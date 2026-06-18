"""
Promote a registered user to admin by phone number.
Usage:
    source venv/bin/activate
    python make_admin.py 9876543210
"""
import sys
from app import create_app
from extensions import mongo

if len(sys.argv) != 2:
    print("Usage: python make_admin.py <phone_number>")
    sys.exit(1)

phone = sys.argv[1].strip()

app = create_app()
with app.app_context():
    result = mongo.db.users.update_one({"phone": phone}, {"$set": {"role": "admin"}})
    if result.matched_count == 0:
        print(f"No user found with phone: {phone}")
        sys.exit(1)
    print(f"✓ User {phone} is now an admin. They can log in at /admin")

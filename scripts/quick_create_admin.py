"""
Quick script to create admin user with default credentials
Run: python scripts/quick_create_admin.py
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_supabase_client
from app.core.security import get_password_hash
from datetime import datetime


def create_default_admin():
    """Create default admin user"""

    # Default credentials
    email = "admin@githaf.com"
    password = "admin123"
    full_name = "Admin User"

    print("Creating default admin user...")
    print(f"Email: {email}")
    print(f"Password: {password}")
    print()

    try:
        client = get_supabase_client()

        # Check if user already exists
        existing = client.table("users").select("*").eq("email", email).execute()

        if existing.data and len(existing.data) > 0:
            print(f"[INFO] User with email {email} already exists")
            print(f"[INFO] You can login with: {email} / {password}")
            return True

        # Hash password
        password_hash = get_password_hash(password)

        # Create admin user
        data = {
            "email": email,
            "password_hash": password_hash,
            "full_name": full_name,
            "is_active": True,
            "is_admin": True,
            "created_at": datetime.utcnow().isoformat()
        }

        response = client.table("users").insert(data).execute()

        if not response.data:
            print("[ERROR] Failed to create user")
            return False

        print("[SUCCESS] Admin user created!")
        print()
        print("=" * 60)
        print("Login Credentials:")
        print(f"  Email: {email}")
        print(f"  Password: {password}")
        print()
        print("Login at: http://localhost:5173/login")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"[ERROR] Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        create_default_admin()
    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

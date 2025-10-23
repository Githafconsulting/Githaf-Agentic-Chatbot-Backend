"""
Bootstrap script to create the first admin user
Run this once during initial setup
"""
import sys
import os
from pathlib import Path
import getpass
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_supabase_client
from app.core.security import get_password_hash


def create_admin_user():
    """Interactive script to create admin user"""

    print("=" * 60)
    print("  Githaf Chatbot - Admin User Creation")
    print("=" * 60)
    print()

    # Get user input
    print("Create your first admin account:\n")

    email = input("Email address: ").strip()
    if not email:
        print("[ERROR] Email is required")
        return False

    full_name = input("Full name (optional): ").strip() or None

    # Get password securely
    password = getpass.getpass("Password (min 8 characters): ")
    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters")
        return False

    password_confirm = getpass.getpass("Confirm password: ")
    if password != password_confirm:
        print("[ERROR] Passwords do not match")
        return False

    print("\nCreating admin user...")

    try:
        client = get_supabase_client()

        # Check if user already exists
        existing = client.table("users").select("*").eq("email", email).execute()

        if existing.data and len(existing.data) > 0:
            print(f"[ERROR] User with email {email} already exists")
            return False

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

        user = response.data[0]

        print("\n" + "=" * 60)
        print("[SUCCESS] Admin user created successfully!")
        print("=" * 60)
        print(f"\nEmail: {user['email']}")
        print(f"Name: {user.get('full_name', 'N/A')}")
        print(f"Role: Admin")
        print(f"Status: Active")
        print("\nYou can now login at: http://localhost:5173/login")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n[ERROR] Failed to create admin user: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    try:
        success = create_admin_user()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Admin creation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

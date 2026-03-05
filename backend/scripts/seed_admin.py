"""
Seed default admin user
Run this script after migrations to create the default admin account
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.crud.admin import get_admin_by_email, create_admin
from app.schemas.admin import AdminCreate

def seed_default_admin():
    db = SessionLocal()
    try:
        default_email = "lalit@gmail.com"
        default_password = "Lalit@123"
        
        existing_admin = get_admin_by_email(db, default_email)
        
        if existing_admin:
            print(f"✓ Admin user '{default_email}' already exists")
            return
        
        admin_data = AdminCreate(
            email=default_email,
            password=default_password,
            full_name="Lalit (Super Admin)",
            is_super_admin=True
        )
        
        admin = create_admin(db, admin_data)
        print(f"✓ Created default admin user: {admin.email}")
        print(f"  Email: {default_email}")
        print(f"  Password: {default_password}")
        print(f"  Super Admin: {admin.is_super_admin}")
        
    except Exception as e:
        print(f"✗ Error creating admin: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_default_admin()

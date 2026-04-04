from sqlalchemy import select

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.utils.enums import AUTH_PROVIDER_LOCAL, ROLE_ADMIN


ADMIN_EMAIL = "admin@daptrax.local"
ADMIN_USERNAME = "admin"
ADMIN_FULL_NAME = "DAPTrax Admin"
ADMIN_PASSWORD = "xxx"


def main():
    db = SessionLocal()
    try:
        existing = db.execute(
            select(User).where(User.email == ADMIN_EMAIL)
        ).scalar_one_or_none()

        if existing:
            print("Admin already exists.")
            return

        admin = User(
            email=ADMIN_EMAIL,
            username=ADMIN_USERNAME,
            full_name=ADMIN_FULL_NAME,
            role=ROLE_ADMIN,
            auth_provider=AUTH_PROVIDER_LOCAL,
            password_hash=hash_password(ADMIN_PASSWORD),
            is_active=True,
        )

        db.add(admin)
        db.commit()
        print("Admin created successfully.")
        print(f"Email: {ADMIN_EMAIL}")
        print(f"Username: {ADMIN_USERNAME}")
        print(f"Password: {ADMIN_PASSWORD}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
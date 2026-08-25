from getpass import getpass

from app.core.database import SessionLocal
from app.schemas.user_schema import CreateUserSchema
from app.services.user_service import UserService

email = input("Admin email: ").strip()
username = input("Admin username: ").strip()
password = getpass("Admin password (minimum 8 characters): ")

with SessionLocal() as db:
    user = UserService(db).create(
        CreateUserSchema(
            email=email,
            username=username,
            password=password,
            first_name="Admin",
            role="admin",
            is_active=True,
        )
    )
    print(f"Created admin: {user.email}")

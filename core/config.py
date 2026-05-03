from dotenv import load_dotenv
import os


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY", "cambia-esto")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "")
SUPERADMIN_USERNAME = os.getenv("SUPERADMIN_USERNAME", "")
SUPERADMIN_PASSWORD_HASH = os.getenv("SUPERADMIN_PASSWORD_HASH", "")


def superadmin_configurado() -> bool:
    return bool(SUPERADMIN_USERNAME and SUPERADMIN_PASSWORD_HASH)

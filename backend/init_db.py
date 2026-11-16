import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database import engine, SessionLocal
from app.models import Base, User
from app.auth import get_password_hash

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            print("Creating default admin user...")
            admin = User(
                username="admin",
                hashed_password=get_password_hash("admin123"),
                role="admin",
                phone="",
                real_name="管理员",
                station_id=None,
            )
            db.add(admin)
            db.commit()
            print("Default admin user created: username=admin, password=admin123")
            logger.warning(
                "默认管理员使用弱口令 admin/admin123，仅供首次登录引导，"
                "请立即调用 PUT /api/v1/auth/password 修改密码后再投入生产使用！"
            )
        else:
            print("Default admin user already exists.")
    finally:
        db.close()


if __name__ == "__main__":
    init_db()

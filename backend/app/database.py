from sqlmodel import SQLModel, Session, create_engine
from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def init_db() -> None:
    # Import models so SQLModel.metadata sees them before create_all
    from .models import user, course, card, booking, order, studio, audit, coupon, evaluation  # noqa: F401
    SQLModel.metadata.create_all(engine)
    if settings.database_url.startswith("sqlite"):
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA foreign_keys=ON")
    _migrate_existing()


def _migrate_existing() -> None:
    """SQLite 没有 alembic — 这里手动 ALTER TABLE 给老库加新字段（幂等）。"""
    if not settings.database_url.startswith("sqlite"):
        return
    with engine.connect() as conn:
        def cols(table: str) -> set:
            rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
            return {r[1] for r in rows}

        # user: 紧急联系人 + 健康备注（P0-7）
        existing = cols("user")
        for col, sql_type in [
            ("emergency_contact_name", "VARCHAR(64)"),
            ("emergency_contact_phone", "VARCHAR(20)"),
            ("health_note", "VARCHAR(2000)"),
        ]:
            if col not in existing:
                conn.exec_driver_sql(f"ALTER TABLE user ADD COLUMN {col} {sql_type}")

        # paymentorder: 退款字段（P0-2）
        existing = cols("paymentorder")
        if "refund_amount" not in existing:
            conn.exec_driver_sql("ALTER TABLE paymentorder ADD COLUMN refund_amount INTEGER DEFAULT 0 NOT NULL")
        if "refunded_at" not in existing:
            conn.exec_driver_sql("ALTER TABLE paymentorder ADD COLUMN refunded_at DATETIME")

        # course: 难度 + 标签 + 适合人群（P2 视觉丰富）
        existing = cols("course")
        if "difficulty" not in existing:
            conn.exec_driver_sql("ALTER TABLE course ADD COLUMN difficulty INTEGER DEFAULT 2 NOT NULL")
        if "tags" not in existing:
            conn.exec_driver_sql("ALTER TABLE course ADD COLUMN tags VARCHAR(255)")
        if "suitable_for" not in existing:
            conn.exec_driver_sql("ALTER TABLE course ADD COLUMN suitable_for VARCHAR(200)")

        # user: tags 字段（会员标签 - P2）
        existing = cols("user")
        if "tags" not in existing:
            conn.exec_driver_sql("ALTER TABLE user ADD COLUMN tags VARCHAR(255)")

        conn.commit()


def get_session():
    with Session(engine) as session:
        yield session

"""
База данных SyntaxVPN
SQLite — хранит пользователей, подписки, платежи
"""

import sqlite3
import os
import uuid
from datetime import datetime, timedelta
from contextlib import contextmanager

from config import DATABASE_PATH


def init_db():
    """Создаёт таблицы при первом запуске"""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                vpn_uuid TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                starts_at TIMESTAMP NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                traffic_limit_bytes INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                plan_id TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'RUB',
                yukassa_payment_id TEXT UNIQUE,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS trials (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)


@contextmanager
def get_db():
    """Контекстный менеджер для работы с БД"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ==================
# Users
# ==================

def get_or_create_user(telegram_id: int, username: str = None) -> dict:
    """Получает или создаёт пользователя, возвращает dict"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        if row:
            return dict(row)

        vpn_uuid = str(uuid.uuid4())
        db.execute(
            "INSERT INTO users (telegram_id, username, vpn_uuid) VALUES (?, ?, ?)",
            (telegram_id, username, vpn_uuid),
        )
        row = db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row)


def get_user_by_uuid(vpn_uuid: str) -> dict | None:
    """Ищет пользователя по VPN UUID"""
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE vpn_uuid = ?", (vpn_uuid,)
        ).fetchone()
        return dict(row) if row else None


def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return dict(row) if row else None


# ==================
# Subscriptions
# ==================

def create_subscription(user_id: int, plan_id: str, duration_days: int, traffic_gb: int = 0) -> dict:
    """Создаёт подписку"""
    now = datetime.utcnow()
    expires = now + timedelta(days=duration_days)
    traffic_bytes = traffic_gb * 1024 * 1024 * 1024 if traffic_gb > 0 else 0

    with get_db() as db:
        db.execute(
            """INSERT INTO subscriptions (user_id, plan_id, starts_at, expires_at, traffic_limit_bytes)
               VALUES (?, ?, ?, ?, ?)""",
            (user_id, plan_id, now.isoformat(), expires.isoformat(), traffic_bytes),
        )
        row = db.execute(
            "SELECT * FROM subscriptions WHERE user_id = ? ORDER BY id DESC LIMIT 1",
            (user_id,),
        ).fetchone()
        return dict(row)


def get_active_subscription(user_id: int) -> dict | None:
    """Возвращает активную подписку пользователя"""
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        row = db.execute(
            """SELECT * FROM subscriptions
               WHERE user_id = ? AND is_active = 1 AND expires_at > ?
               ORDER BY expires_at DESC LIMIT 1""",
            (user_id, now),
        ).fetchone()
        return dict(row) if row else None


def get_all_active_subscriptions() -> list[dict]:
    """Все активные подписки"""
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        rows = db.execute(
            """SELECT s.*, u.telegram_id, u.vpn_uuid
               FROM subscriptions s JOIN users u ON s.user_id = u.id
               WHERE s.is_active = 1 AND s.expires_at > ?""",
            (now,),
        ).fetchall()
        return [dict(r) for r in rows]


def deactivate_subscription(sub_id: int):
    with get_db() as db:
        db.execute("UPDATE subscriptions SET is_active = 0 WHERE id = ?", (sub_id,))


# ==================
# Trials
# ==================

def has_used_trial(telegram_id: int) -> bool:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM trials WHERE telegram_id = ?", (telegram_id,)
        ).fetchone()
        return row is not None


def mark_trial_used(telegram_id: int):
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO trials (telegram_id) VALUES (?)", (telegram_id,)
        )


# ==================
# Payments
# ==================

def create_payment(user_id: int, plan_id: str, amount: float, yukassa_payment_id: str) -> dict:
    with get_db() as db:
        db.execute(
            """INSERT INTO payments (user_id, plan_id, amount, yukassa_payment_id, status)
               VALUES (?, ?, ?, ?, 'pending')""",
            (user_id, plan_id, amount, yukassa_payment_id),
        )
        row = db.execute(
            "SELECT * FROM payments WHERE yukassa_payment_id = ?",
            (yukassa_payment_id,),
        ).fetchone()
        return dict(row)


def confirm_payment(yukassa_payment_id: str):
    with get_db() as db:
        db.execute(
            "UPDATE payments SET status = 'confirmed' WHERE yukassa_payment_id = ?",
            (yukassa_payment_id,),
        )


def get_payment_by_yukassa_id(yukassa_payment_id: str) -> dict | None:
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM payments WHERE yukassa_payment_id = ?",
            (yukassa_payment_id,),
        ).fetchone()
        return dict(row) if row else None


def get_all_users_count() -> int:
    with get_db() as db:
        row = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()
        return row["cnt"]


def get_active_subs_count() -> int:
    now = datetime.utcnow().isoformat()
    with get_db() as db:
        row = db.execute(
            "SELECT COUNT(*) as cnt FROM subscriptions WHERE is_active = 1 AND expires_at > ?",
            (now,),
        ).fetchone()
        return row["cnt"]

"""
Oz-Lek loyihasi uchun ma'lumotlar bazasi (SQLite).
Admin bot ham, mijozlar boti ham, API ham shu faylni ishlatadi —
shuning uchun barcha uchtasida ma'lumot bir xil bo'ladi.
"""

import os
import sqlite3
from contextlib import contextmanager
import db_backup

# Railway'da Volume ulanganda DB_PATH=/data/oz_lek.db deb Variables'ga qo'shasiz —
# shunda ma'lumotlar har qanday qayta deploy qilishda ham saqlanib qoladi.
# Agar Variable qo'shilmagan bo'lsa, standart holatda konteyner ichida saqlanadi (vaqtinchalik).
DB_PATH = os.getenv("DB_PATH", "oz_lek.db")


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    db_backup.pull_from_github(DB_PATH)
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medicines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                photo_file_id TEXT,   -- Telegram bot orqali botga yuborish uchun
                photo_url TEXT        -- Saytda ko'rsatish uchun (rasm linki)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS company_info (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                text TEXT NOT NULL
            )
        """)
        # Standart "Oz-Lek haqida" matni — admin keyin o'zgartirishi mumkin
        conn.execute("""
            INSERT OR IGNORE INTO company_info (id, text) VALUES (1, ?)
        """, (""""OZ-LEK" MCHJ — Xorazm viloyati, Urganch shahrida joylashgan farmatsevtika kompaniyasi.
Kompaniya Belarusiyadagi "Lekpharm" korxonasi bilan shartnoma asosida dori vositalarini olib kiradi va O'zbekiston bozoriga yetkazib beradi.

STIR: 310043123
Manzil: Xorazm viloyati, Urganch shahri, Ashxobod MFY, Sanoatchilar ko'chasi, 85J-uy
Telefon: +998 99 001 01 01
Faoliyat turi: Farmatsevtika tovarlari ulgurji savdosi
Ro'yxatdan o'tgan sana: 25.11.2022
Rahbar: Bazarboyev Otabek Nuraddinovich""",))
        conn.commit()


# ---------- Dorilar bilan ishlash ----------

def add_medicine(name: str, description: str, photo_file_id: str = None, photo_url: str = None) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO medicines (name, description, photo_file_id, photo_url) VALUES (?, ?, ?, ?)",
            (name, description, photo_file_id, photo_url),
        )
        conn.commit()
        medicine_id = cur.lastrowid
    db_backup.push_to_github(DB_PATH)
    return medicine_id


def list_medicines():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM medicines ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_medicine(medicine_id: int):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM medicines WHERE id = ?", (medicine_id,)).fetchone()
        return dict(row) if row else None


def search_medicine_by_name(query: str):
    """Nom bo'yicha qisman moslikni qidirish (katta-kichik harfga sezgir emas)."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM medicines WHERE LOWER(name) LIKE ?",
            (f"%{query.lower()}%",),
        ).fetchall()
        return [dict(r) for r in rows]


def update_medicine(medicine_id: int, name: str = None, description: str = None,
                     photo_file_id: str = None, photo_url: str = None):
    current = get_medicine(medicine_id)
    if not current:
        return False
    with get_conn() as conn:
        conn.execute(
            "UPDATE medicines SET name=?, description=?, photo_file_id=?, photo_url=? WHERE id=?",
            (
                name or current["name"],
                description or current["description"],
                photo_file_id or current["photo_file_id"],
                photo_url or current["photo_url"],
                medicine_id,
            ),
        )
        conn.commit()
    db_backup.push_to_github(DB_PATH)
    return True


def delete_medicine(medicine_id: int) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM medicines WHERE id = ?", (medicine_id,))
        conn.commit()
        deleted = cur.rowcount > 0
    if deleted:
        db_backup.push_to_github(DB_PATH)
    return deleted


# ---------- Kompaniya haqida ma'lumot ----------

def get_company_info() -> str:
    with get_conn() as conn:
        row = conn.execute("SELECT text FROM company_info WHERE id = 1").fetchone()
        return row["text"] if row else ""


def set_company_info(text: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO company_info (id, text) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET text = excluded.text",
            (text,),
        )
        conn.commit()
    db_backup.push_to_github(DB_PATH)

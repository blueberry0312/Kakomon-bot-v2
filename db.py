import datetime
import aiosqlite

DB_PATH = "kakomon.db"

# 実際のサーバー構成に合わせたタグ・学科の選択肢
EXAM_TYPES = ["前期中間", "前期期末", "後期中間", "後期期末", "夏休み明け", "冬休み明け", "その他"]
DEPARTMENTS = ["M", "EE", "EC", "MB", "CI"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS exams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year TEXT NOT NULL,          -- 年度 (例: 2026)
    grade TEXT,                  -- 学年 (例: 2年)
    department TEXT,             -- 学科 (M / EE / EC / MB / CI)
    subject TEXT NOT NULL,       -- 科目名
    exam_type TEXT NOT NULL,     -- 前期中間 / 前期期末 / 後期中間 / 後期期末 / 夏休み明け / 冬休み明け / その他
    file_url TEXT NOT NULL,      -- Discord CDN上のURLのみ保持(自前複製しない)
    message_link TEXT,           -- 元投稿へのジャンプリンク
    submitted_by TEXT,           -- 投稿者のDiscordユーザー名のみ
    posted_at TEXT NOT NULL,     -- 登録日時(ISO文字列)
    is_deleted INTEGER DEFAULT 0 -- 削除依頼が通った場合は論理削除
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.commit()


async def find_duplicate(year, subject, exam_type, department=None):
    """同一の 年度+科目+試験区分(+学科) が既に存在するか確認"""
    query = """SELECT id FROM exams
               WHERE year = ? AND subject = ? AND exam_type = ? AND is_deleted = 0"""
    params = [year, subject, exam_type]
    if department:
        query += " AND department = ?"
        params.append(department)
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            row = await cursor.fetchone()
            return row is not None


async def add_exam(year, grade, department, subject, exam_type, file_url, message_link, submitted_by):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO exams
               (year, grade, department, subject, exam_type, file_url, message_link, submitted_by, posted_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (year, grade, department, subject, exam_type, file_url, message_link,
             submitted_by, datetime.datetime.utcnow().isoformat()),
        )
        await db.commit()


async def search_exams(subject=None, year=None, exam_type=None, department=None, limit=10):
    query = """SELECT id, year, grade, department, subject, exam_type, message_link
               FROM exams WHERE is_deleted = 0"""
    params = []
    if subject:
        query += " AND subject LIKE ?"
        params.append(f"%{subject}%")
    if year:
        query += " AND year = ?"
        params.append(year)
    if exam_type:
        query += " AND exam_type = ?"
        params.append(exam_type)
    if department:
        query += " AND department = ?"
        params.append(department)
    query += " ORDER BY id DESC LIMIT ?"
    params.append(limit)

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(query, params) as cursor:
            return await cursor.fetchall()


async def latest_exams(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            """SELECT id, year, grade, department, subject, exam_type, message_link
               FROM exams WHERE is_deleted = 0 ORDER BY id DESC LIMIT ?""",
            (limit,),
        ) as cursor:
            return await cursor.fetchall()


async def soft_delete_exam(exam_id):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "UPDATE exams SET is_deleted = 1 WHERE id = ?", (exam_id,)
        )
        await db.commit()
        return cursor.rowcount > 0


async def edit_exam(exam_id, **fields):
    """subject / exam_type / year / grade / department のいずれかを更新"""
    allowed = {"subject", "exam_type", "year", "grade", "department"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    params = list(updates.values()) + [exam_id]
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(f"UPDATE exams SET {set_clause} WHERE id = ?", params)
        await db.commit()
        return cursor.rowcount > 0

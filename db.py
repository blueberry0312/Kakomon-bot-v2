import os
import datetime
import asyncpg

DATABASE_URL = os.getenv("DATABASE_URL")

# 実際のサーバー構成に合わせたタグ・学科の選択肢
EXAM_TYPES = ["前期中間", "前期期末", "後期中間", "後期期末", "夏休み明け", "冬休み明け", "その他"]
DEPARTMENTS = ["M", "EE", "EC", "MB", "CI"]

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS exams (
    id SERIAL PRIMARY KEY,
    year TEXT NOT NULL,          -- 年度 (例: 2026)
    grade TEXT,                  -- 学年 (例: 2年)
    department TEXT,             -- 学科 (M / EE / EC / MB / CI)
    subject TEXT NOT NULL,       -- 科目名
    exam_type TEXT NOT NULL,     -- 前期中間 / 前期期末 / 後期中間 / 後期期末 / 夏休み明け / 冬休み明け / その他
    file_url TEXT NOT NULL,      -- Discord CDN上のURLのみ保持(自前複製しない)
    message_link TEXT,           -- 元投稿へのジャンプリンク
    submitted_by TEXT,           -- 投稿者のDiscordユーザー名のみ
    posted_at TIMESTAMP NOT NULL,-- 登録日時
    is_deleted BOOLEAN DEFAULT FALSE  -- 削除依頼が通った場合は論理削除
);
"""

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URLが設定されていません。"
                "RailwayでPostgreSQLサービスを追加し、環境変数を紐付けてください。"
            )
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
    return _pool


async def init_db():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)


async def find_duplicate(year, subject, exam_type, department=None):
    pool = await get_pool()
    query = """SELECT id FROM exams
               WHERE year = $1 AND subject = $2 AND exam_type = $3 AND is_deleted = FALSE"""
    params = [year, subject, exam_type]
    if department:
        query += " AND department = $4"
        params.append(department)
    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        return row is not None


async def add_exam(year, grade, department, subject, exam_type, file_url, message_link, submitted_by):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """INSERT INTO exams
               (year, grade, department, subject, exam_type, file_url, message_link, submitted_by, posted_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
            year, grade, department, subject, exam_type, file_url, message_link,
            submitted_by, datetime.datetime.utcnow(),
        )


async def search_exams(subject=None, year=None, exam_type=None, department=None, limit=10):
    pool = await get_pool()
    conditions = ["is_deleted = FALSE"]
    params = []

    if subject:
        params.append(f"%{subject}%")
        conditions.append(f"subject ILIKE ${len(params)}")
    if year:
        params.append(year)
        conditions.append(f"year = ${len(params)}")
    if exam_type:
        params.append(exam_type)
        conditions.append(f"exam_type = ${len(params)}")
    if department:
        params.append(department)
        conditions.append(f"department = ${len(params)}")

    params.append(limit)
    query = f"""SELECT id, year, grade, department, subject, exam_type, message_link
                FROM exams WHERE {' AND '.join(conditions)}
                ORDER BY id DESC LIMIT ${len(params)}"""

    async with pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [tuple(r) for r in rows]


async def latest_exams(limit=10):
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """SELECT id, year, grade, department, subject, exam_type, message_link
               FROM exams WHERE is_deleted = FALSE ORDER BY id DESC LIMIT $1""",
            limit,
        )
        return [tuple(r) for r in rows]


async def get_exam(exam_id):
    """/report で指定されたIDの内容を1件取得する(存在しなければNone)"""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """SELECT id, year, grade, department, subject, exam_type, file_url, submitted_by
               FROM exams WHERE id = $1""",
            exam_id,
        )
        return tuple(row) if row else None


async def soft_delete_exam(exam_id):
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            "UPDATE exams SET is_deleted = TRUE WHERE id = $1", exam_id
        )
        return result.endswith("1")  # "UPDATE 1" なら成功


async def edit_exam(exam_id, **fields):
    """subject / exam_type / year / grade / department のいずれかを更新"""
    allowed = {"subject", "exam_type", "year", "grade", "department"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if not updates:
        return False

    pool = await get_pool()
    set_parts = []
    params = []
    for i, (k, v) in enumerate(updates.items(), start=1):
        set_parts.append(f"{k} = ${i}")
        params.append(v)
    params.append(exam_id)

    query = f"UPDATE exams SET {', '.join(set_parts)} WHERE id = ${len(params)}"
    async with pool.acquire() as conn:
        result = await conn.execute(query, *params)
        return result.endswith("1")
from datetime import datetime, timezone
from pathlib import Path
import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS news (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, content TEXT NOT NULL,
 category TEXT NOT NULL CHECK(category IN ('Update','Release','Security','Announcement')),
 image_url TEXT, created_at TEXT NOT NULL, published_at TEXT,
 expires_at TEXT, status TEXT NOT NULL CHECK(status IN ('draft','published','expired','deleted'))
);
CREATE INDEX IF NOT EXISTS idx_news_public ON news(status, published_at, expires_at);
"""

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def iso(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z") if value else None

class Storage:
    def __init__(self, path: Path):
        self.path = path

    async def init(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self.path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def create(self, title: str, content: str, category: str, image_url: str | None, expires_at: datetime | None) -> str:
        created = now_utc()
        post_id = f"news_{created.strftime('%Y%m%d%H%M%S%f')}"
        async with aiosqlite.connect(self.path) as db:
            await db.execute("INSERT INTO news VALUES (?,?,?,?,?,?,?,?,?)", (post_id, title, content, category, image_url, iso(created), iso(created), iso(expires_at), "published"))
            await db.commit()
        return post_id

    async def public_posts(self, limit: int = 50, offset: int = 0) -> list[dict]:
        current = iso(now_utc())
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT id,title,content,category,published_at,expires_at,image_url FROM news WHERE status='published' AND published_at <= ? AND (expires_at IS NULL OR expires_at > ?) ORDER BY published_at DESC LIMIT ? OFFSET ?", (current, current, limit, offset))
            return [dict(row) for row in await cursor.fetchall()]

    async def posts(self, limit: int = 10, offset: int = 0) -> list[dict]:
        async with aiosqlite.connect(self.path) as db:
            current = iso(now_utc())
            await db.execute("UPDATE news SET status='expired' WHERE status='published' AND expires_at IS NOT NULL AND expires_at <= ?", (current,))
            await db.commit()
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM news WHERE status != 'deleted' ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
            return [dict(row) for row in await cursor.fetchall()]

    async def get(self, post_id: str) -> dict | None:
        async with aiosqlite.connect(self.path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM news WHERE id=?", (post_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def delete(self, post_id: str) -> bool:
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("UPDATE news SET status='deleted' WHERE id=? AND status != 'deleted'", (post_id,))
            await db.commit()
            return cursor.rowcount == 1

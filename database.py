import aiosqlite
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Optional


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Ma'lumotlar bazasiga ulanish va row_factory sozlash."""
        conn = await aiosqlite.connect(self.db_path)
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        try:
            yield conn
        finally:
            await conn.close()

    async def init_db(self) -> None:
        """Baza jadvallarini yaratish va indekslarni sozlash."""
        db_file = Path(self.db_path)
        if db_file.parent:
            db_file.parent.mkdir(parents=True, exist_ok=True)

        async with self.get_connection() as conn:
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS movies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    category TEXT NOT NULL,
                    year INTEGER,
                    description TEXT,
                    source_chat_id INTEGER NOT NULL,
                    source_message_id INTEGER NOT NULL,
                    poster_file_id TEXT,
                    is_active INTEGER DEFAULT 1 NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )

            # Migratsiya: Mavjud bazada poster_file_id ustuni bo'lmasa, uni qo'shish (ma'lumotlar saqlanadi)
            async with conn.execute("PRAGMA table_info(movies);") as cursor:
                columns = [row["name"] for row in await cursor.fetchall()]
                if "poster_file_id" not in columns:
                    await conn.execute("ALTER TABLE movies ADD COLUMN poster_file_id TEXT;")

            # Tezroq qidirish uchun indekslar
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_movies_code ON movies(code);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_movies_category ON movies(category);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_movies_is_active ON movies(is_active);")
            await conn.commit()

    # --- USER METODLARI ---

    async def add_user(self, user_id: int) -> bool:
        """Yangi foydalanuvchini ro'yxatga olish."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
                (user_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def get_user_count(self) -> int:
        """Jami foydalanuvchilar soni."""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT COUNT(*) AS total FROM users") as cursor:
                row = await cursor.fetchone()
                return row["total"] if row else 0

    # --- KINO CRUD METODLARI ---

    async def add_movie(
        self,
        code: str,
        title: str,
        category: str,
        source_chat_id: int,
        source_message_id: int,
        year: Optional[int] = None,
        description: Optional[str] = None,
        poster_file_id: Optional[str] = None,
        is_active: int = 1,
    ) -> int:
        """Yangi kino qo'shish."""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                """
                INSERT INTO movies (
                    code, title, category, year, description,
                    source_chat_id, source_message_id, poster_file_id, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code.strip(),
                    title.strip(),
                    category.strip(),
                    year,
                    description.strip() if description else None,
                    source_chat_id,
                    source_message_id,
                    poster_file_id.strip() if poster_file_id else None,
                    is_active,
                ),
            )
            await conn.commit()
            return cursor.lastrowid

    async def code_exists(self, code: str) -> bool:
        """Kino kodi mavjudligini tekshirish."""
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT 1 FROM movies WHERE code = ? LIMIT 1",
                (code.strip(),)
            ) as cursor:
                row = await cursor.fetchone()
                return row is not None

    async def generate_unique_code(self) -> str:
        """Mavjud bo'lmagan raqamli unikal kino kodini yaratish."""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT code FROM movies") as cursor:
                rows = await cursor.fetchall()
                existing_codes = set()
                for r in rows:
                    c = r["code"]
                    if c.isdigit():
                        existing_codes.add(int(c))

                candidate = 1001
                while candidate in existing_codes:
                    candidate += 1
                return str(candidate)

    async def get_movie_by_code(self, code: str, active_only: bool = True) -> Optional[dict[str, Any]]:
        """Kino kodi bo'yicha olish."""
        sql = "SELECT * FROM movies WHERE code = ?"
        params: list[Any] = [code.strip()]
        if active_only:
            sql += " AND is_active = 1"

        async with self.get_connection() as conn:
            async with conn.execute(sql, tuple(params)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_movie_by_id(self, movie_id: int) -> Optional[dict[str, Any]]:
        """ID bo'yicha kinoni olish."""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT * FROM movies WHERE id = ?", (movie_id,)) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def get_movies_by_category(
        self, category: str, page: int = 1, page_size: int = 10, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """Janr bo'yicha sahifalangan kinolar ro'yxati."""
        offset = max(0, (page - 1) * page_size)
        sql = "SELECT * FROM movies WHERE category = ?"
        params: list[Any] = [category.strip()]
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        async with self.get_connection() as conn:
            async with conn.execute(sql, tuple(params)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def count_movies_by_category(self, category: str, active_only: bool = True) -> int:
        """Janr bo'yicha kinolar soni."""
        sql = "SELECT COUNT(*) AS total FROM movies WHERE category = ?"
        params: list[Any] = [category.strip()]
        if active_only:
            sql += " AND is_active = 1"

        async with self.get_connection() as conn:
            async with conn.execute(sql, tuple(params)) as cursor:
                row = await cursor.fetchone()
                return row["total"] if row else 0

    async def search_movies(
        self, query: str, page: int = 1, page_size: int = 10, active_only: bool = True
    ) -> list[dict[str, Any]]:
        """Nomi bo'yicha qidirish."""
        offset = max(0, (page - 1) * page_size)
        sql = "SELECT * FROM movies WHERE title LIKE ?"
        params: list[Any] = [f"%{query.strip()}%"]
        if active_only:
            sql += " AND is_active = 1"
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        async with self.get_connection() as conn:
            async with conn.execute(sql, tuple(params)) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def count_search_movies(self, query: str, active_only: bool = True) -> int:
        """Qidiruv natijalari soni."""
        sql = "SELECT COUNT(*) AS total FROM movies WHERE title LIKE ?"
        params: list[Any] = [f"%{query.strip()}%"]
        if active_only:
            sql += " AND is_active = 1"

        async with self.get_connection() as conn:
            async with conn.execute(sql, tuple(params)) as cursor:
                row = await cursor.fetchone()
                return row["total"] if row else 0

    async def get_all_movies(self, page: int = 1, page_size: int = 10) -> list[dict[str, Any]]:
        """Admin uchun barcha kinolarning sahifalangan ro'yxati."""
        offset = max(0, (page - 1) * page_size)
        async with self.get_connection() as conn:
            async with conn.execute(
                "SELECT * FROM movies ORDER BY id DESC LIMIT ? OFFSET ?",
                (page_size, offset),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def count_all_movies(self) -> int:
        """Admin uchun barcha kinolar soni."""
        async with self.get_connection() as conn:
            async with conn.execute("SELECT COUNT(*) AS total FROM movies") as cursor:
                row = await cursor.fetchone()
                return row["total"] if row else 0

    async def update_movie(self, movie_id: int, **fields: Any) -> bool:
        """Kino ma'lumotlarini qisman yoki to'liq yangilash."""
        allowed_fields = {
            "code",
            "title",
            "category",
            "year",
            "description",
            "source_chat_id",
            "source_message_id",
            "poster_file_id",
            "is_active",
        }
        updates = []
        params = []
        for key, val in fields.items():
            if key in allowed_fields:
                updates.append(f"{key} = ?")
                params.append(val)

        if not updates:
            return False

        params.append(movie_id)
        sql = f"UPDATE movies SET {', '.join(updates)} WHERE id = ?"

        async with self.get_connection() as conn:
            cursor = await conn.execute(sql, tuple(params))
            await conn.commit()
            return cursor.rowcount > 0

    async def delete_movie(self, movie_id: int) -> bool:
        """Kinoni ma'lumotlar bazasidan o'chirish."""
        async with self.get_connection() as conn:
            cursor = await conn.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            await conn.commit()
            return cursor.rowcount > 0

    async def get_stats(self) -> dict[str, Any]:
        """Bot statistikasi."""
        async with self.get_connection() as conn:
            # Jami kinolar
            async with conn.execute("SELECT COUNT(*) AS total FROM movies") as cursor:
                total_movies = (await cursor.fetchone())["total"]

            # Faol kinolar
            async with conn.execute("SELECT COUNT(*) AS total FROM movies WHERE is_active = 1") as cursor:
                active_movies = (await cursor.fetchone())["total"]

            # Jami foydalanuvchilar
            async with conn.execute("SELECT COUNT(*) AS total FROM users") as cursor:
                total_users = (await cursor.fetchone())["total"]

            # Janrlar bo'yicha taqsimot
            async with conn.execute(
                """
                SELECT category, COUNT(*) AS count
                FROM movies
                GROUP BY category
                ORDER BY count DESC
                """
            ) as cursor:
                rows = await cursor.fetchall()
                genres_stat = {r["category"]: r["count"] for r in rows}

            return {
                "total_movies": total_movies,
                "active_movies": active_movies,
                "total_users": total_users,
                "genres_stat": genres_stat,
            }

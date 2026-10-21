import os
import pytest
import aiosqlite
from database import Database


@pytest.fixture
def test_db_path(tmp_path):
    """Vaqtinchalik test ma'lumotlar bazasi fayli yo'li."""
    return str(tmp_path / "test_minotv.db")


@pytest.fixture
async def db(test_db_path):
    """Initsializatsiya qilingan Database instansi."""
    database = Database(test_db_path)
    await database.init_db()
    return database


@pytest.mark.asyncio
async def test_init_db_creates_tables(db, test_db_path):
    """Baza va jadvallar to'g'ri yaratilishini tekshirish."""
    async with aiosqlite.connect(test_db_path) as conn:
        async with conn.execute("SELECT name FROM sqlite_master WHERE type='table'") as cursor:
            tables = [row[0] for row in await cursor.fetchall()]
            assert "movies" in tables
            assert "users" in tables


@pytest.mark.asyncio
async def test_users_operations(db):
    """Foydalanuvchi qo'shish va sonini hisoblash."""
    assert await db.get_user_count() == 0

    # Birinchi marta qo'shish
    added = await db.add_user(111222333)
    assert added is True
    assert await db.get_user_count() == 1

    # Takroriy qo'shish (IGNORE bo'lishi kerak)
    added_again = await db.add_user(111222333)
    assert added_again is False
    assert await db.get_user_count() == 1

    # Boshqa foydalanuvchi
    await db.add_user(444555666)
    assert await db.get_user_count() == 2


@pytest.mark.asyncio
async def test_add_and_get_movie_by_code(db):
    """Kino qo'shish va kodi bo'yicha topish."""
    movie_id = await db.add_movie(
        code="1001",
        title="Qasoskorlar",
        category="Fantastika",
        source_chat_id=-1001234567890,
        source_message_id=45,
        year=2019,
        description="Superqahramonlar jangi",
        is_active=1,
    )
    assert movie_id > 0

    movie = await db.get_movie_by_code("1001", active_only=True)
    assert movie is not None
    assert movie["id"] == movie_id
    assert movie["title"] == "Qasoskorlar"
    assert movie["code"] == "1001"
    assert movie["source_chat_id"] == -1001234567890
    assert movie["source_message_id"] == 45


@pytest.mark.asyncio
async def test_duplicate_code_rejected(db):
    """Takroriy kod kiritilganda IntegrityError yuz berishi."""
    await db.add_movie(
        code="2002",
        title="Kino 1",
        category="Jangari",
        source_chat_id=-1001,
        source_message_id=1,
    )
    assert await db.code_exists("2002") is True

    with pytest.raises(Exception):
        await db.add_movie(
            code="2002",
            title="Kino 2",
            category="Drama",
            source_chat_id=-1001,
            source_message_id=2,
        )


@pytest.mark.asyncio
async def test_generate_unique_code(db):
    """Avtomatik unikal kod generatsiya qilish."""
    code1 = await db.generate_unique_code()
    assert code1.isdigit()

    await db.add_movie(
        code=code1,
        title="Avto Kino",
        category="Komediya",
        source_chat_id=-100,
        source_message_id=10,
    )

    code2 = await db.generate_unique_code()
    assert code2.isdigit()
    assert code1 != code2


@pytest.mark.asyncio
async def test_filter_by_category_and_pagination(db):
    """Janr bo'yicha filtrlash va pagination."""
    for i in range(15):
        await db.add_movie(
            code=f"fant_{i}",
            title=f"Fantastika Kino {i}",
            category="Fantastika",
            source_chat_id=-100,
            source_message_id=i,
        )
    for i in range(5):
        await db.add_movie(
            code=f"com_{i}",
            title=f"Komediya Kino {i}",
            category="Komediya",
            source_chat_id=-100,
            source_message_id=100 + i,
        )

    # Jami soni
    assert await db.count_movies_by_category("Fantastika") == 15
    assert await db.count_movies_by_category("Komediya") == 5
    assert await db.count_movies_by_category("Anime") == 0

    # 1-sahifa (10 ta)
    page1 = await db.get_movies_by_category("Fantastika", page=1, page_size=10)
    assert len(page1) == 10

    # 2-sahifa (5 ta)
    page2 = await db.get_movies_by_category("Fantastika", page=2, page_size=10)
    assert len(page2) == 5


@pytest.mark.asyncio
async def test_search_movies_by_title(db):
    """Kino nomi bo'yicha qidirish."""
    await db.add_movie(code="s1", title="Gladiator 2", category="Tarixiy", source_chat_id=-1, source_message_id=1)
    await db.add_movie(code="s2", title="Qora Pantera", category="Fantastika", source_chat_id=-1, source_message_id=2)
    await db.add_movie(code="s3", title="Pantera Izidan", category="Detektiv", source_chat_id=-1, source_message_id=3)

    results = await db.search_movies("Pantera")
    assert len(results) == 2
    assert {r["code"] for r in results} == {"s2", "s3"}

    empty_results = await db.search_movies("MavjudEmasSoz")
    assert len(empty_results) == 0


@pytest.mark.asyncio
async def test_inactive_movies_hidden_from_users(db):
    """Nofaol kinolar oddiy foydalanuvchilarga berilmasligi kerak."""
    movie_id = await db.add_movie(
        code="hidden_1",
        title="Yashirin Kino",
        category="Dahshat",
        source_chat_id=-1,
        source_message_id=1,
        is_active=0,  # nofaol
    )

    # active_only=True bo'lganda topilmasligi kerak
    assert await db.get_movie_by_code("hidden_1", active_only=True) is None
    # active_only=False bo'lganda (admin uchun) topilishi kerak
    assert await db.get_movie_by_code("hidden_1", active_only=False) is not None

    # Qidiruvda ham ko'rinmasligi kerak
    assert len(await db.search_movies("Yashirin", active_only=True)) == 0
    assert len(await db.search_movies("Yashirin", active_only=False)) == 1

    # Janr ro'yxatida ham ko'rinmasligi kerak
    assert await db.count_movies_by_category("Dahshat", active_only=True) == 0
    assert await db.count_movies_by_category("Dahshat", active_only=False) == 1


@pytest.mark.asyncio
async def test_update_and_delete_movie(db):
    """Kino tahrirlash va o'chirish."""
    m_id = await db.add_movie(
        code="old_code",
        title="Eski Nom",
        category="Drama",
        source_chat_id=-1,
        source_message_id=1,
    )

    # Yangilash
    updated = await db.update_movie(m_id, title="Yangi Nom", code="new_code", is_active=0)
    assert updated is True

    movie = await db.get_movie_by_id(m_id)
    assert movie["title"] == "Yangi Nom"
    assert movie["code"] == "new_code"
    assert movie["is_active"] == 0

    # O'chirish
    deleted = await db.delete_movie(m_id)
    assert deleted is True
    assert await db.get_movie_by_id(m_id) is None


@pytest.mark.asyncio
async def test_stats(db):
    """Statistika to'g'ri hisoblanishi."""
    await db.add_user(101)
    await db.add_user(102)

    await db.add_movie(code="st1", title="M1", category="Komediya", source_chat_id=-1, source_message_id=1, is_active=1)
    await db.add_movie(code="st2", title="M2", category="Komediya", source_chat_id=-1, source_message_id=2, is_active=1)
    await db.add_movie(code="st3", title="M3", category="Drama", source_chat_id=-1, source_message_id=3, is_active=0)

    stats = await db.get_stats()
    assert stats["total_users"] == 2
    assert stats["total_movies"] == 3
    assert stats["active_movies"] == 2
    assert stats["genres_stat"]["Komediya"] == 2
    assert stats["genres_stat"]["Drama"] == 1

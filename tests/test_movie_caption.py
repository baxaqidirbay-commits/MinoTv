import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.exceptions import TelegramBadRequest
from database import Database
from handlers.user import format_movie_info, send_movie_to_user


def test_format_movie_info_complete():
    """Kino ma'lumotlari to'liq va qalin sarlavhalar bilan formatlanishini tekshirish."""
    movie = {
        "title": "Titanik <3 & 'Okean'",
        "code": "1001",
        "category": "Drama",
        "year": 1997,
        "description": "Kema cho'kishi va sevgi tarixi.",
    }

    formatted = format_movie_info(movie, include_description=True)

    # HTML xavfsiz escape qilinishi va sarlavhalar qalin bo'lishi kerak
    assert "&lt;3" in formatted
    assert "&amp;" in formatted
    assert "🎬 <b>Titanik &lt;3 &amp; &#x27;Okean&#x27;</b>" in formatted
    assert "🔢 <b>Kino kodi:</b> 1001" in formatted
    assert "🎭 <b>Janr:</b> Drama" in formatted
    assert "📅 <b>Yil:</b> 1997" in formatted
    assert "📝 <b>KINO HAQIDA:</b>\nKema cho&#x27;kishi va sevgi tarixi." in formatted


def test_format_movie_info_missing_optional_fields():
    """Yil yoki tavsif bo'lmaganda ham to'g'ri ishlashi."""
    movie = {
        "title": "Nomsiz Film",
        "code": "2002",
        "category": "Jangari",
        "year": None,
        "description": None,
    }

    formatted = format_movie_info(movie, include_description=True)

    assert "🎬 <b>Nomsiz Film</b>" in formatted
    assert "🔢 <b>Kino kodi:</b> 2002" in formatted
    assert "🎭 <b>Janr:</b> Jangari" in formatted
    assert "📅 <b>Yil:</b> Ko'rsatilmagan" in formatted
    assert "📝 <b>KINO HAQIDA:</b>\nKo'rsatilmagan" in formatted


@pytest.mark.asyncio
async def test_send_movie_standard_caption_without_poster():
    """Muqovasiz kinoni 1024 gacha caption bilan yuborish."""
    bot_mock = AsyncMock()
    movie = {
        "id": 10,
        "code": "1010",
        "title": "Avatar",
        "category": "Fantastika",
        "year": 2009,
        "description": "Pandora sayyorasidagi sarguzashtlar.",
        "poster_file_id": None,
        "source_chat_id": -100111,
        "source_message_id": 55,
    }

    success = await send_movie_to_user(bot_mock, chat_id=12345, movie=movie)

    assert success is True
    # send_photo chaqirilmaydi
    bot_mock.send_photo.assert_not_awaited()
    # To'g'ridan-to'g'ri copy_message caption bilan chaqirilishi kerak
    bot_mock.copy_message.assert_awaited_once()
    _, kwargs = bot_mock.copy_message.call_args
    assert kwargs["chat_id"] == 12345
    assert kwargs["from_chat_id"] == -100111
    assert kwargs["message_id"] == 55
    assert "Avatar" in kwargs["caption"]
    assert "Pandora" in kwargs["caption"]
    assert kwargs["parse_mode"] == "HTML"
    bot_mock.send_message.assert_not_awaited()


@pytest.mark.asyncio
async def test_send_movie_with_poster_success():
    """Muqovali kino: avval send_photo (caption bilan), so'ng copy_message orqali video."""
    bot_mock = AsyncMock()
    movie = {
        "id": 15,
        "code": "1515",
        "title": "O'rgimchak odam",
        "category": "Fantastika",
        "year": 2021,
        "description": "Piter Parker sarguzashtlari.",
        "poster_file_id": "AgACAgIAAxkBAAI...",
        "source_chat_id": -100333,
        "source_message_id": 99,
    }

    success = await send_movie_to_user(bot_mock, chat_id=12345, movie=movie)

    assert success is True
    # 1. send_photo chaqirilgan
    bot_mock.send_photo.assert_awaited_once()
    _, photo_kwargs = bot_mock.send_photo.call_args
    assert photo_kwargs["chat_id"] == 12345
    assert photo_kwargs["photo"] == "AgACAgIAAxkBAAI..."
    assert "O&#x27;rgimchak odam" in photo_kwargs["caption"]
    assert "KINO HAQIDA" in photo_kwargs["caption"]
    assert photo_kwargs["parse_mode"] == "HTML"

    # 2. copy_message chaqirilgan (original video)
    bot_mock.copy_message.assert_awaited_once_with(
        chat_id=12345,
        from_chat_id=-100333,
        message_id=99,
    )


@pytest.mark.asyncio
async def test_send_movie_with_poster_long_description():
    """Muqovali kino va uzun tavsif (1024 dan oshiq): send_photo qisqa caption bilan + send_message + copy_message."""
    bot_mock = AsyncMock()
    long_desc = "Tavsif matni " * 90  # 1200+ belgi

    movie = {
        "id": 16,
        "code": "1616",
        "title": "Uzun Tavsifli Poster Kino",
        "category": "Drama",
        "year": 2023,
        "description": long_desc,
        "poster_file_id": "poster_photo_id_123",
        "source_chat_id": -100444,
        "source_message_id": 105,
    }

    success = await send_movie_to_user(bot_mock, chat_id=12345, movie=movie)

    assert success is True
    # 1. send_photo qisqa caption bilan
    bot_mock.send_photo.assert_awaited_once()
    _, photo_kwargs = bot_mock.send_photo.call_args
    assert len(photo_kwargs["caption"]) <= 1024
    assert "Uzun Tavsifli Poster Kino" in photo_kwargs["caption"]

    # 2. send_message orqali to'liq ma'lumot
    bot_mock.send_message.assert_awaited_once()
    _, msg_kwargs = bot_mock.send_message.call_args
    assert long_desc.strip() in msg_kwargs["text"]

    # 3. copy_message orqali video
    bot_mock.copy_message.assert_awaited_once_with(
        chat_id=12345,
        from_chat_id=-100444,
        message_id=105,
    )


@pytest.mark.asyncio
async def test_send_movie_poster_fails_falls_back_to_video():
    """Muqova yuborishda xatolik yuz berganda, video uzatilishi to'xtab qolmasligi kerak."""
    bot_mock = AsyncMock()
    bot_mock.send_photo.side_effect = TelegramBadRequest(
        method=MagicMock(),
        message="Bad Request: photo file_id is invalid"
    )

    movie = {
        "id": 17,
        "code": "1717",
        "title": "Buzuq Muqovali Kino",
        "category": "Jangari",
        "year": 2022,
        "description": "Muqova ruxsatsiz yoki o'chirilgan.",
        "poster_file_id": "invalid_file_id",
        "source_chat_id": -100555,
        "source_message_id": 200,
    }

    success = await send_movie_to_user(bot_mock, chat_id=12345, movie=movie)

    assert success is True
    # send_photo chaqirilgan va xato bergan
    bot_mock.send_photo.assert_awaited_once()
    # Video muqovasiz funksiya orqali (caption bilan copy_message) yuborilgan
    bot_mock.copy_message.assert_awaited_once()
    _, copy_kwargs = bot_mock.copy_message.call_args
    assert copy_kwargs["chat_id"] == 12345
    assert "Buzuq Muqovali Kino" in copy_kwargs["caption"]


@pytest.mark.asyncio
async def test_database_poster_crud_and_migration(tmp_path):
    """Bazaga poster_file_id bilan saqlash, tahrirlash va migratsiyani tekshirish."""
    db_file = str(tmp_path / "test_migration.db")
    db = Database(db_file)
    await db.init_db()

    # 1. Posterli yangi kino qo'shish
    m_id = await db.add_movie(
        code="post_1",
        title="Posterli Kino",
        category="Anime",
        source_chat_id=-1001,
        source_message_id=5,
        poster_file_id="my_poster_id",
    )
    assert m_id > 0

    movie = await db.get_movie_by_id(m_id)
    assert movie["poster_file_id"] == "my_poster_id"

    # 2. Posterni tahrirlash (yangi poster)
    await db.update_movie(m_id, poster_file_id="new_poster_id")
    movie = await db.get_movie_by_id(m_id)
    assert movie["poster_file_id"] == "new_poster_id"

    # 3. Posterni olib tashlash (None)
    await db.update_movie(m_id, poster_file_id=None)
    movie = await db.get_movie_by_id(m_id)
    assert movie["poster_file_id"] is None

    # 4. Qayta init_db() chaqirilganda migratsiya mavjud ma'lumotlarni buzmasligi kerak
    await db.init_db()
    movie = await db.get_movie_by_id(m_id)
    assert movie is not None
    assert movie["title"] == "Posterli Kino"

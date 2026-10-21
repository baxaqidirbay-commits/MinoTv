import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.exceptions import TelegramBadRequest
from config import Config, parse_admin_ids, parse_channel_id
from filters import IsAdminFilter
from handlers.user import send_movie_to_user


def test_parse_admin_ids():
    """Admin IDlarini parse qilish xavfsizligini tekshirish."""
    assert parse_admin_ids(None) == []
    assert parse_admin_ids("") == []
    assert parse_admin_ids("12345") == [12345]
    assert parse_admin_ids("123, 456, 789") == [123, 456, 789]
    # Noto'g'ri qiymatlar e'tiborsiz qoldirilishi kerak
    assert parse_admin_ids("123, abc, 456, , xyz") == [123, 456]


def test_parse_channel_id():
    """Kanal ID larini parse qilish."""
    assert parse_channel_id(None) is None
    assert parse_channel_id("-1001234567890") == -1001234567890
    assert parse_channel_id("invalid") is None


def test_config_missing_token_raises_error(monkeypatch):
    """BOT_TOKEN bo'lmasa xato berishi."""
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(ValueError) as excinfo:
        Config(validate_token=True)
    assert "BOT_TOKEN topilmadi" in str(excinfo.value)


def test_config_is_admin(monkeypatch):
    """Config.is_admin tekshiruvi."""
    monkeypatch.setenv("BOT_TOKEN", "fake_token_for_test")
    monkeypatch.setenv("ADMIN_IDS", "111, 222")

    config = Config(validate_token=True)
    assert config.is_admin(111) is True
    assert config.is_admin(222) is True
    assert config.is_admin(333) is False


@pytest.mark.asyncio
async def test_is_admin_filter(monkeypatch):
    """IsAdminFilter ishlashini tekshirish."""
    monkeypatch.setenv("BOT_TOKEN", "fake_token_for_test")
    monkeypatch.setenv("ADMIN_IDS", "999")
    config = Config(validate_token=True)

    filter_instance = IsAdminFilter()

    # Admin foydalanuvchi
    admin_message = MagicMock()
    admin_message.from_user.id = 999
    assert await filter_instance(admin_message, config=config) is True

    # Oddiy foydalanuvchi
    regular_message = MagicMock()
    regular_message.from_user.id = 123
    assert await filter_instance(regular_message, config=config) is False

    # from_user None bo'lganda
    no_user_message = MagicMock()
    no_user_message.from_user = None
    assert await filter_instance(no_user_message, config=config) is False


@pytest.mark.asyncio
async def test_send_movie_to_user_handles_telegram_error():
    """Telegram API xatosi yuz berganda xavfsiz boshqarish."""
    bot_mock = AsyncMock()
    bot_mock.copy_message.side_effect = TelegramBadRequest(
        method=MagicMock(),
        message="Bad Request: message to copy not found"
    )

    movie = {
        "id": 1,
        "source_chat_id": -100123,
        "source_message_id": 999,
        "title": "Test Kino",
    }

    success = await send_movie_to_user(bot_mock, chat_id=12345, movie=movie)
    assert success is False
    # Caption bilan va fallback sifatida jami 2 marta urinib ko'riladi
    assert bot_mock.copy_message.await_count == 2


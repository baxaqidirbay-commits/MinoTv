import pytest
from unittest.mock import AsyncMock, MagicMock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.base import StorageKey
from aiogram.types import Chat, Message, MessageOriginChannel, User

from config import Config
from database import Database
from handlers.admin import (
    handle_receive_code,
    handle_receive_forward,
    handle_receive_title,
    handle_start_add_movie,
)
from handlers.user import handle_prompt_movie_code, handle_receive_movie_code, handle_start
from states import AddMovieState, UserMovieState


@pytest.fixture
def fsm_context():
    storage = MemoryStorage()
    key = StorageKey(bot_id=123, chat_id=456, user_id=789)
    return FSMContext(storage=storage, key=key)


@pytest.fixture
async def memory_db(tmp_path):
    db_path = str(tmp_path / "fsm_test.db")
    db = Database(db_path)
    await db.init_db()
    return db


@pytest.mark.asyncio
async def test_user_start_handler(fsm_context, memory_db):
    """Start buyrug'i foydalanuvchini bazaga qo'shishi va javob qaytarishi."""
    message = MagicMock(spec=Message)
    message.from_user = User(id=789, is_bot=False, first_name="Ali")
    message.answer = AsyncMock()

    await handle_start(message, state=fsm_context, db=memory_db)

    assert await memory_db.get_user_count() == 1
    message.answer.assert_awaited_once()
    args, kwargs = message.answer.call_args
    assert "MinoTV kino botiga xush kelibsiz!" in args[0]


@pytest.mark.asyncio
async def test_user_movie_code_fsm(fsm_context, memory_db):
    """Kino kodi kiritish bosqichi va topilmagan holat."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()

    # 1. Kod kiritishni so'rash
    await handle_prompt_movie_code(message, state=fsm_context)
    current_state = await fsm_context.get_state()
    assert current_state == UserMovieState.waiting_for_code.state

    # 2. Mavjud bo'lmagan kod yuborish
    message.text = "99999"
    message.chat = Chat(id=456, type="private")
    bot = AsyncMock()

    await handle_receive_movie_code(message, state=fsm_context, bot=bot, db=memory_db)
    # FSM tozalangan bo'lishi kerak
    assert await fsm_context.get_state() is None

    # Bot kino topilmadi xabarini berishi kerak
    last_call = message.answer.call_args
    assert "Bunday ID bilan kino topilmadi" in last_call[0][0]


@pytest.mark.asyncio
async def test_admin_add_movie_forward_validation(fsm_context):
    """Forward qilingan xabar MessageOriginChannel bo'lmasa rad etilishi."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()
    message.forward_origin = None  # Forward qilinmagan

    await fsm_context.set_state(AddMovieState.waiting_for_forward)
    await handle_receive_forward(message, state=fsm_context)

    # State o'zgarmasligi kerak (chunki xato xabar beriladi)
    assert await fsm_context.get_state() == AddMovieState.waiting_for_forward.state
    args, _ = message.answer.call_args
    assert "Bu kanaldan to'g'ri forward qilingan post emas" in args[0]


@pytest.mark.asyncio
async def test_admin_add_movie_forward_success(fsm_context):
    """MessageOriginChannel to'g'ri kelganda channel ID va msg ID olinishi."""
    message = MagicMock(spec=Message)
    message.answer = AsyncMock()

    origin = MagicMock(spec=MessageOriginChannel)
    origin.chat = MagicMock()
    origin.chat.id = -100987654321
    origin.chat.title = "Premyeralar Kanali"
    origin.message_id = 120

    message.forward_origin = origin

    await fsm_context.set_state(AddMovieState.waiting_for_forward)
    await handle_receive_forward(message, state=fsm_context)

    # State waiting_for_title ga o'tishi kerak
    assert await fsm_context.get_state() == AddMovieState.waiting_for_title.state
    data = await fsm_context.get_data()
    assert data["source_chat_id"] == -100987654321
    assert data["source_message_id"] == 120


@pytest.mark.asyncio
async def test_admin_add_movie_auto_code(fsm_context, memory_db):
    """Admin /auto yuborganda avtomatik unikal kod yaratilishi."""
    await fsm_context.set_state(AddMovieState.waiting_for_code)

    message = MagicMock(spec=Message)
    message.text = "/auto"
    message.answer = AsyncMock()

    await handle_receive_code(message, state=fsm_context, db=memory_db)

    assert await fsm_context.get_state() == AddMovieState.waiting_for_category.state
    data = await fsm_context.get_data()
    assert "code" in data
    assert data["code"].isdigit()


@pytest.mark.asyncio
async def test_admin_add_movie_poster_photo(fsm_context):
    """Admin rasm yuborganda poster_file_id olinishi va confirm ga o'tishi."""
    from handlers.admin import handle_receive_poster_photo
    from aiogram.types import PhotoSize

    await fsm_context.set_state(AddMovieState.waiting_for_poster)

    message = MagicMock(spec=Message)
    photo1 = PhotoSize(file_id="small_photo", file_unique_id="u1", width=100, height=100)
    photo2 = PhotoSize(file_id="large_photo_xyz", file_unique_id="u2", width=800, height=800)
    message.photo = [photo1, photo2]
    message.answer = AsyncMock()

    await handle_receive_poster_photo(message, state=fsm_context)

    assert await fsm_context.get_state() == AddMovieState.waiting_for_confirm.state
    data = await fsm_context.get_data()
    assert data["poster_file_id"] == "large_photo_xyz"


@pytest.mark.asyncio
async def test_admin_add_movie_poster_skip(fsm_context):
    """Admin /skip yuborganda poster_file_id None bo'lishi."""
    from handlers.admin import handle_skip_poster

    await fsm_context.set_state(AddMovieState.waiting_for_poster)

    message = MagicMock(spec=Message)
    message.text = "/skip"
    message.answer = AsyncMock()

    await handle_skip_poster(message, state=fsm_context)

    assert await fsm_context.get_state() == AddMovieState.waiting_for_confirm.state
    data = await fsm_context.get_data()
    assert data["poster_file_id"] is None


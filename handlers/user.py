import html
import logging
from math import ceil
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest

from config import GENRES
from database import Database
from keyboards import (
    CategoryNavCallback,
    MovieSelectCallback,
    SearchNavCallback,
    get_cancel_reply_keyboard,
    get_genres_keyboard,
    get_main_reply_keyboard,
    get_movies_pagination_keyboard,
    get_search_results_keyboard,
)
from states import UserMovieState

logger = logging.getLogger(__name__)

router = Router(name="user_router")


def format_movie_info(movie: dict, include_description: bool = True) -> str:
    """Kino ma'lumotlarini xavfsiz HTML formatda tayyorlash."""
    title = html.escape(str(movie.get("title") or "Noma'lum"))
    code = html.escape(str(movie.get("code") or ""))
    category = html.escape(str(movie.get("category") or ""))
    year = movie.get("year")
    year_str = html.escape(str(year)) if year else "Ko'rsatilmagan"

    text = (
        f"🎬 <b>{title}</b>\n\n"
        f"🔢 <b>Kino kodi:</b> {code}\n"
        f"🎭 <b>Janr:</b> {category}\n"
        f"📅 <b>Yil:</b> {year_str}"
    )

    if include_description:
        desc = movie.get("description")
        desc_str = html.escape(str(desc).strip()) if desc else "Ko'rsatilmagan"
        text += f"\n\n📝 <b>KINO HAQIDA:</b>\n{desc_str}"

    return text


async def send_movie_to_user(bot: Bot, chat_id: int, movie: dict) -> bool:
    """Kinoni va uning ma'lumotlarini (agar bo'lsa muqova bilan) copyMessage orqali xavfsiz yuborish."""
    full_info = format_movie_info(movie, include_description=True)
    short_info = format_movie_info(movie, include_description=False)

    source_chat_id = movie["source_chat_id"]
    source_message_id = movie["source_message_id"]
    poster_file_id = movie.get("poster_file_id")

    # --- 1-HOLAT: AGAR MUQOVA MAVJUD BO'LSA ---
    if poster_file_id:
        poster_sent = False
        try:
            if len(full_info) <= 1024:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=poster_file_id,
                    caption=full_info,
                    parse_mode="HTML",
                )
            else:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=poster_file_id,
                    caption=short_info,
                    parse_mode="HTML",
                )
                await bot.send_message(chat_id=chat_id, text=full_info, parse_mode="HTML")
            poster_sent = True
        except TelegramBadRequest as e:
            logger.warning(
                "send_photo with poster failed for movie ID %s: %s. Falling back to video without poster...",
                movie.get("id"),
                e,
            )
        except Exception as e:
            logger.warning(
                "Unexpected error sending poster for movie ID %s: %s. Falling back to video without poster...",
                movie.get("id"),
                e,
            )

        if poster_sent:
            # Muqova muvaffaqiyatli ketdi, endi original kino videosini kanal manbasidan uzatamiz
            try:
                await bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=source_chat_id,
                    message_id=source_message_id,
                )
                return True
            except TelegramBadRequest as e:
                error_msg = str(e).lower()
                logger.error(
                    "TelegramBadRequest while copying movie ID %s after poster (from %s msg %s): %s",
                    movie.get("id"),
                    source_chat_id,
                    source_message_id,
                    e,
                )
                return False
            except Exception as e:
                logger.exception("Unexpected error copying movie after poster: %s", e)
                return False

    # --- 2-HOLAT: MUQOVA BO'LMAGANDA (YOKI MUQOVA YUBORISHDA XATO BO'LGANDA FALLBACK) ---
    if len(full_info) <= 1024:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
                caption=full_info,
                parse_mode="HTML",
            )
            return True
        except TelegramBadRequest as e:
            logger.warning(
                "copy_message with full caption failed for movie ID %s: %s. Trying fallback...",
                movie.get("id"),
                e,
            )
        except Exception as e:
            logger.warning(
                "Unexpected error with full caption for movie ID %s: %s. Trying fallback...",
                movie.get("id"),
                e,
            )
    else:
        # Uzun tavsif bo'lsa: qisqa caption bilan videoni nusxalash
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=source_chat_id,
                message_id=source_message_id,
                caption=short_info,
                parse_mode="HTML",
            )
            # Qolgan to'liq ma'lumotlarni alohida xabar qilib yuborish
            await bot.send_message(chat_id=chat_id, text=full_info, parse_mode="HTML")
            return True
        except TelegramBadRequest as e:
            logger.warning(
                "copy_message with short caption failed for movie ID %s: %s. Trying original copy...",
                movie.get("id"),
                e,
            )
        except Exception as e:
            logger.warning(
                "Unexpected error with short caption for movie ID %s: %s. Trying original copy...",
                movie.get("id"),
                e,
            )

    # 3. Fallback: Videoni caption'siz original holatda nusxalash va ma'lumotlarni alohida yuborish
    try:
        await bot.copy_message(
            chat_id=chat_id,
            from_chat_id=source_chat_id,
            message_id=source_message_id,
        )
        try:
            await bot.send_message(chat_id=chat_id, text=full_info, parse_mode="HTML")
        except Exception as msg_err:
            logger.error("Failed to send separate movie metadata message: %s", msg_err)
        return True
    except TelegramBadRequest as e:
        error_msg = str(e).lower()
        logger.error(
            "TelegramBadRequest while copying movie ID %s (from %s msg %s): %s",
            movie.get("id"),
            source_chat_id,
            source_message_id,
            e,
        )
        if "message to copy not found" in error_msg:
            return False
        elif "chat not found" in error_msg:
            logger.error("Source channel chat not found or bot lacks access!")
            return False
        elif "protected" in error_msg or "copying" in error_msg:
            logger.error("Content is protected from copying in source channel!")
            return False
        return False
    except TelegramAPIError as e:
        logger.error("TelegramAPIError when copying movie: %s", e)
        return False
    except Exception as e:
        logger.exception("Unexpected error sending movie: %s", e)
        return False


# --- START BUYRUG'I ---

@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext, db: Database) -> None:
    """/start buyrug'i va foydalanuvchini ro'yxatga olish."""
    await state.clear()
    if message.from_user:
        await db.add_user(message.from_user.id)

    welcome_text = (
        "🎬 MinoTV kino botiga xush kelibsiz!\n\n"
        "Kino ID raqamini yuboring yoki quyidagi menyudan kerakli bo'limni tanlang."
    )
    await message.answer(welcome_text, reply_markup=get_main_reply_keyboard())


# --- BEKOR QILISH (CANCEL) ---

@router.message(F.text == "❌ Bekor qilish")
async def handle_cancel(message: Message, state: FSMContext) -> None:
    """Amalni bekor qilish va bosh menyuga qaytish."""
    await state.clear()
    await message.answer(
        "Bosh menyuga qaytdingiz.",
        reply_markup=get_main_reply_keyboard(),
    )


# --- YORDAM (HELP) ---

@router.message(F.text == "ℹ️ Yordam")
@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    """Foydalanish bo'yicha sodda yo'riqnoma."""
    help_text = (
        "ℹ️ <b>MinoTV botidan foydalanish yo'riqnomasi:</b>\n\n"
        "1️⃣ <b>Kino kodini kiritish:</b>\n"
        "Menyudagi «🔢 Kino kodini kiritish» tugmasini bosing yoki to'g'ridan-to'g'ri "
        "kino kodini (masalan: <code>1025</code>) botga yuboring.\n\n"
        "2️⃣ <b>Janrlar:</b>\n"
        "«🎭 Janrlar» tugmasi orqali o'zingiz xohlagan janrni tanlab, kinolar katalogini ko'rishingiz mumkin.\n\n"
        "3️⃣ <b>Kino qidirish:</b>\n"
        "«🔍 Kino qidirish» tugmasini bosing va kino nomini yozing. Bot mos keluvchi kinolarni topib beradi.\n\n"
        "<i>Eslatma: Barcha kinolar yuqori sifatda rasmiy Telegram kanallarimiz orqali uzatiladi.</i>"
    )
    await message.answer(help_text, parse_mode="HTML", reply_markup=get_main_reply_keyboard())


# --- KINO KODI ORQALI QIDIRISH ---

@router.message(F.text == "🔢 Kino kodini kiritish")
async def handle_prompt_movie_code(message: Message, state: FSMContext) -> None:
    """Kino kodini so'rash."""
    await state.set_state(UserMovieState.waiting_for_code)
    await message.answer(
        "🔢 Iltimos, kino kodini (ID raqamini) yuboring:\n"
        "<i>(Masalan: 1001)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_reply_keyboard(),
    )


@router.message(UserMovieState.waiting_for_code)
async def handle_receive_movie_code(message: Message, state: FSMContext, bot: Bot, db: Database) -> None:
    """FSM holatida kiritilgan kino kodini tekshirish."""
    code = (message.text or "").strip()
    if not code:
        await message.answer("Iltimos, kino kodini matn yoki raqam ko'rinishida yuboring.")
        return

    await state.clear()
    await process_movie_search_by_code(message, bot, db, code)


@router.message(F.text.regexp(r"^\d+$"))
async def handle_direct_code(message: Message, bot: Bot, db: Database) -> None:
    """Foydalanuvchi FSM statesiz to'g'ridan-to'g'ri raqam yuborganda kino qidirish."""
    code = (message.text or "").strip()
    await process_movie_search_by_code(message, bot, db, code)


async def process_movie_search_by_code(message: Message, bot: Bot, db: Database, code: str) -> None:
    """Kino kodi bo'yicha qidirish va natijani yuborish."""
    movie = await db.get_movie_by_code(code, active_only=True)
    if not movie:
        await message.answer(
            f"❌ <b>Bunday ID bilan kino topilmadi:</b> <code>{code}</code>\n"
            "Kodni qayta tekshirib ko'ring yoki «🔍 Kino qidirish» orqali nomini izlang.",
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(),
        )
        return

    # Kinoni yuborish
    success = await send_movie_to_user(bot, message.chat.id, movie)
    if not success:
        await message.answer(
            "⚠️ <b>Kechirasiz, kinoni uzatishda xatolik yuz berdi.</b>\n\n"
            "Mumkin bo'lgan sabablar:\n"
            "• Manba kanaldagi xabar o'chirilgan yoki ko'chirilgan;\n"
            "• Manba kanalda kontentni ko'chirish taqiqlangan (Content Protection);\n"
            "• Bot kanalga kirish ruxsatiga ega emas.\n"
            "Iltimos, administratorga murojaat qiling.",
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(),
        )


# --- JANRLAR BO'LIMI ---

@router.message(F.text == "🎭 Janrlar")
async def handle_genres_menu(message: Message, state: FSMContext) -> None:
    """Janrlar ro'yxatini ko'rsatish."""
    await state.clear()
    await message.answer(
        "🎭 O'zingiz qiziqqan janrni tanlang:",
        reply_markup=get_genres_keyboard(),
    )


@router.callback_query(F.data == "back_to_genres")
async def handle_back_to_genres(callback: CallbackQuery) -> None:
    """Janrlar ro'yxatiga qaytish."""
    await callback.message.edit_text(
        "🎭 O'zingiz qiziqqan janrni tanlang:",
        reply_markup=get_genres_keyboard(),
    )
    await callback.answer()


@router.callback_query(CategoryNavCallback.filter())
async def handle_category_page(
    callback: CallbackQuery,
    callback_data: CategoryNavCallback,
    db: Database,
) -> None:
    """Tanlangan janr bo'yicha sahifalangan kinolar ro'yxati."""
    genre_idx = callback_data.genre_idx
    if 0 <= genre_idx < len(GENRES):
        genre_name = GENRES[genre_idx]
    else:
        genre_name = "Boshqa"

    page = callback_data.page
    page_size = 10

    total_count = await db.count_movies_by_category(genre_name, active_only=True)
    total_pages = max(1, ceil(total_count / page_size))

    if total_count == 0:
        await callback.message.edit_text(
            f"🎭 <b>{genre_name}</b> janrida hozircha faol kinolar mavjud emas.",
            parse_mode="HTML",
            reply_markup=get_genres_keyboard(),
        )
        await callback.answer()
        return

    # Sahifani chegaralash
    page = max(1, min(page, total_pages))
    movies = await db.get_movies_by_category(genre_name, page=page, page_size=page_size, active_only=True)

    text = (
        f"🎬 <b>{genre_name}</b> janridagi kinolar:\n"
        f"Jami: {total_count} ta kino (Sahifa: {page}/{total_pages})\n\n"
        "Kinoni tomosha qilish uchun uning nomini bosing:"
    )

    keyboard = get_movies_pagination_keyboard(
        movies=movies,
        current_page=page,
        total_pages=total_pages,
        genre_idx=genre_idx,
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


# --- KINO TANLANGANDA (INLINE LISTDAN) ---

@router.callback_query(MovieSelectCallback.filter())
async def handle_movie_select(
    callback: CallbackQuery,
    callback_data: MovieSelectCallback,
    bot: Bot,
    db: Database,
) -> None:
    """Inline ro'yxatdan tanlangan kinoni yuborish."""
    movie = await db.get_movie_by_id(callback_data.movie_id)
    if not movie or movie.get("is_active") == 0:
        await callback.answer("❌ Ushbu kino mavjud emas yoki faolsizlantirilgan.", show_alert=True)
        return

    await callback.answer("🎬 Kino yuklanmoqda...")
    success = await send_movie_to_user(bot, callback.message.chat.id, movie)
    if not success:
        await callback.message.answer(
            f"⚠️ <b>«{movie['title']}»</b> kinosini uzatishda xatolik yuz berdi.\n"
            "Manba post o'chirilgan yoki kanal kirish ruxsati cheklangan bo'lishi mumkin.",
            parse_mode="HTML",
        )


# --- KINO QIDIRISH (SEARCH) ---

@router.message(F.text == "🔍 Kino qidirish")
async def handle_prompt_search(message: Message, state: FSMContext) -> None:
    """Kino qidirish uchun so'rov so'rash."""
    await state.set_state(UserMovieState.waiting_for_query)
    await message.answer(
        "🔍 Qidirmoqchi bo'lgan kino nomini yoki uning bir qismini kiriting:\n"
        "<i>(Masalan: Avatar yoki O'rgimchak)</i>",
        parse_mode="HTML",
        reply_markup=get_cancel_reply_keyboard(),
    )


@router.message(UserMovieState.waiting_for_query)
async def handle_execute_search(message: Message, state: FSMContext, db: Database) -> None:
    """Kino nomi bo'yicha qidiruvni amalga oshirish."""
    query = (message.text or "").strip()
    if not query:
        await message.answer("Iltimos, qidiruv matnini kiriting.")
        return

    # FSM ma'lumotlariga queryni saqlash (pagination uchun kerak bo'lsa)
    await state.update_data(search_query=query)

    page_size = 10
    total_count = await db.count_search_movies(query, active_only=True)
    if total_count == 0:
        await state.clear()
        await message.answer(
            f"🔍 Kechirasiz, «<b>{query}</b>» so'rovi bo'yicha hech qanday kino topilmadi.\n\n"
            "Boshqa nom bilan qidirib ko'ring yoki «🎭 Janrlar» bo'limini ko'ring.",
            parse_mode="HTML",
            reply_markup=get_main_reply_keyboard(),
        )
        return

    total_pages = max(1, ceil(total_count / page_size))
    movies = await db.search_movies(query, page=1, page_size=page_size, active_only=True)

    text = (
        f"🔍 «<b>{query}</b>» bo'yicha topilgan kinolar:\n"
        f"Jami: {total_count} ta natija (Sahifa: 1/{total_pages})\n\n"
        "Kerakli kinoni tanlang:"
    )

    await message.answer(
        text,
        parse_mode="HTML",
        reply_markup=get_search_results_keyboard(movies, current_page=1, total_pages=total_pages),
    )
    # Qidiruv natijalari ko'rsatilgandan keyin reply klaviaturani tiklaymiz
    await message.answer("Amalni davom ettirish uchun menyudan foydalanishingiz mumkin:", reply_markup=get_main_reply_keyboard())


@router.callback_query(SearchNavCallback.filter())
async def handle_search_pagination(
    callback: CallbackQuery,
    callback_data: SearchNavCallback,
    state: FSMContext,
    db: Database,
) -> None:
    """Qidiruv natijalari paginationini boshqarish."""
    data = await state.get_data()
    query = data.get("search_query")
    if not query:
        await callback.answer("Qidiruv muddati tugagan. Iltimos, qaytadan qidiring.", show_alert=True)
        return

    page = callback_data.page
    page_size = 10
    total_count = await db.count_search_movies(query, active_only=True)
    total_pages = max(1, ceil(total_count / page_size))
    page = max(1, min(page, total_pages))

    movies = await db.search_movies(query, page=page, page_size=page_size, active_only=True)

    text = (
        f"🔍 «<b>{query}</b>» bo'yicha topilgan kinolar:\n"
        f"Jami: {total_count} ta natija (Sahifa: {page}/{total_pages})\n\n"
        "Kerakli kinoni tanlang:"
    )

    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_search_results_keyboard(movies, current_page=page, total_pages=total_pages),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def handle_noop(callback: CallbackQuery) -> None:
    """Bosilmaydigan tugmalar (masalan sahifa raqami) uchun bo'sh handler."""
    await callback.answer()

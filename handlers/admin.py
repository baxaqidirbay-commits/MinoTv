import logging
from math import ceil
from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    Message,
    MessageOriginChannel,
    ReplyKeyboardRemove,
)

from config import Config, GENRES
from database import Database
from filters import IsAdminFilter
from keyboards import (
    AdminEditFieldCallback,
    AdminMovieCallback,
    get_admin_edit_fields_keyboard,
    get_admin_genre_selection_keyboard,
    get_admin_main_keyboard,
    get_admin_movie_detail_keyboard,
    get_admin_movies_list_keyboard,
    get_admin_reply_keyboard,
    get_confirm_add_movie_keyboard,
    get_delete_confirmation_keyboard,
    get_main_reply_keyboard,
)
from states import AddMovieState, EditMovieState

logger = logging.getLogger(__name__)

router = Router(name="admin_router")

# Butun routerga admin filtrini o'rnatamiz
router.message.filter(IsAdminFilter())
router.callback_query.filter(IsAdminFilter())


# --- ADMIN ASOSIY MENYUSI ---

@router.message(Command("admin"))
async def handle_admin_start(message: Message, state: FSMContext) -> None:
    """Admin panelini ochish."""
    await state.clear()
    text = (
        "👑 <b>MinoTV Boshqaruv Paneli (Admin)</b>\n\n"
        "Quyidagi amallardan birini tanlang:"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=get_admin_reply_keyboard())
    await message.answer("Boshqaruv tugmalari:", reply_markup=get_admin_main_keyboard())


@router.callback_query(F.data == "admin_menu")
async def handle_admin_menu_callback(callback: CallbackQuery, state: FSMContext) -> None:
    """Inline tugma orqali admin bosh menyusiga qaytish."""
    await state.clear()
    text = (
        "👑 <b>MinoTV Boshqaruv Paneli (Admin)</b>\n\n"
        "Quyidagi amallardan birini tanlang:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_close")
async def handle_admin_close(callback: CallbackQuery, state: FSMContext) -> None:
    """Admin menyusini yopish."""
    await state.clear()
    await callback.message.delete()
    await callback.answer("Admin paneli yopildi.")


@router.callback_query(F.data == "cancel_action")
async def handle_cancel_inline(callback: CallbackQuery, state: FSMContext) -> None:
    """Joriy amalni bekor qilish."""
    await state.clear()
    await callback.message.edit_text(
        "❌ Amal bekor qilindi.",
        reply_markup=get_admin_main_keyboard(),
    )
    await callback.answer("Bekor qilindi.")


# --- KINO QO'SHISH JARAYONI ---

@router.message(F.text == "➕ Kino qo'shish")
@router.callback_query(F.data == "admin_add_movie")
async def handle_start_add_movie(event: Message | CallbackQuery, state: FSMContext) -> None:
    """Kino qo'shish jarayonini boshlash - kanal postini so'rash."""
    await state.clear()
    await state.set_state(AddMovieState.waiting_for_forward)

    text = (
        "📥 <b>1-Qadam: Kanal postini forward qiling</b>\n\n"
        "Kinolar saqlanadigan kanaldan kino videosi/posti xabarini ushbu botga «Forward» (Uzatish) qilib yuboring.\n\n"
        "<i>Eslatma: Xabar kanal manbasi ko'rinadigan bo'lishi shart!</i>"
    )

    if isinstance(event, CallbackQuery):
        await event.message.answer(text, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML")


@router.message(AddMovieState.waiting_for_forward)
async def handle_receive_forward(message: Message, state: FSMContext) -> None:
    """Forward qilingan xabarni tahlil qilish (aiogram 3 forward_origin orqali)."""
    origin = message.forward_origin

    if not origin or not isinstance(origin, MessageOriginChannel):
        await message.answer(
            "❌ <b>Bu kanaldan to'g'ri forward qilingan post emas!</b>\n\n"
            "Sabablar:\n"
            "• Xabar kanaldan forward qilinmagan;\n"
            "• Kanaldagi nusxalash/uzatish cheklovi tufayli kanal manbasi yashirilgan;\n"
            "• Matn shunchaki ko'chirib yozilgan.\n\n"
            "Iltimos, haqiqiy kanal postini forward qilib qayta yuboring yoki bekor qilish uchun /admin yozing.",
            parse_mode="HTML",
        )
        return

    source_chat_id = origin.chat.id
    source_message_id = origin.message_id

    await state.update_data(
        source_chat_id=source_chat_id,
        source_message_id=source_message_id,
        source_chat_title=origin.chat.title or "Kanal",
    )

    await state.set_state(AddMovieState.waiting_for_title)
    await message.answer(
        f"✅ Kanal xabari qabul qilindi!\n"
        f"• Kanal: <b>{origin.chat.title}</b> (ID: <code>{source_chat_id}</code>)\n"
        f"• Xabar ID: <code>{source_message_id}</code>\n\n"
        "📝 <b>2-Qadam: Kino nomini kiriting:</b>",
        parse_mode="HTML",
    )


@router.message(AddMovieState.waiting_for_title)
async def handle_receive_title(message: Message, state: FSMContext) -> None:
    """Kino nomini qabul qilish."""
    title = (message.text or "").strip()
    if not title:
        await message.answer("Iltimos, kino nomini matn ko'rinishida kiriting:")
        return

    await state.update_data(title=title)
    await state.set_state(AddMovieState.waiting_for_code)

    await message.answer(
        f"Kino nomi: <b>{title}</b>\n\n"
        "🔢 <b>3-Qadam: Kino kodini kiriting:</b>\n"
        "Raqamli kod yozing yoki avtomatik kod generatsiya qilish uchun /auto buyrug'ini yuboring.",
        parse_mode="HTML",
    )


@router.message(AddMovieState.waiting_for_code)
async def handle_receive_code(message: Message, state: FSMContext, db: Database) -> None:
    """Kino kodini qabul qilish yoki avto-generatsiya."""
    text = (message.text or "").strip()

    if text.lower() == "/auto":
        code = await db.generate_unique_code()
    else:
        if not text.isdigit():
            await message.answer(
                "❌ Kino kodi faqat raqamlardan iborat bo'lishi kerak!\n"
                "Raqam kiriting yoki avtomatik kod uchun /auto yuboring:"
            )
            return

        code = text
        if await db.code_exists(code):
            await message.answer(
                f"❌ <b>{code}</b> kodi bilan boshqa kino allaqachon mavjud!\n"
                "Iltimos, boshqa kod kiriting yoki /auto buyrug'idan foydalaning:",
                parse_mode="HTML",
            )
            return

    await state.update_data(code=code)
    await state.set_state(AddMovieState.waiting_for_category)

    await message.answer(
        f"Kino kodi: <code>{code}</code>\n\n"
        "🎭 <b>4-Qadam: Janrni tanlang:</b>",
        parse_mode="HTML",
        reply_markup=get_admin_genre_selection_keyboard(prefix="adm_add_cat"),
    )


@router.callback_query(F.data.startswith("adm_add_cat:"))
async def handle_receive_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Janrni qabul qilish."""
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(AddMovieState.waiting_for_year)

    await callback.message.edit_text(
        f"Tanlangan janr: <b>{category}</b>\n\n"
        "📅 <b>5-Qadam: Kino chiqarilgan yilini kiriting:</b>\n"
        "<i>(Masalan: 2023 yoki o'tkazib yuborish uchun /skip yuboring)</i>",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(AddMovieState.waiting_for_year)
async def handle_receive_year(message: Message, state: FSMContext) -> None:
    """Kino yilini qabul qilish."""
    text = (message.text or "").strip()
    year = None

    if text.lower() != "/skip":
        if not text.isdigit() or len(text) != 4 or not (1900 <= int(text) <= 2100):
            await message.answer(
                "❌ Iltimos, to'g'ri 4 xonali yil kiriting (masalan: 2024) yoki o'tkazib yuborish uchun /skip yozing:"
            )
            return
        year = int(text)

    await state.update_data(year=year)
    await state.set_state(AddMovieState.waiting_for_description)

    await message.answer(
        "📝 <b>6-Qadam: Kino tavsifini (qisqacha ma'lumot) kiriting:</b>\n"
        "<i>(Tavsif kiritishni xohlamasangiz /skip yuboring)</i>",
        parse_mode="HTML",
    )


@router.message(AddMovieState.waiting_for_description)
async def handle_receive_description(message: Message, state: FSMContext) -> None:
    """Kino tavsifini qabul qilish va muqova so'rash."""
    text = (message.text or "").strip()
    description = None if text.lower() == "/skip" else text

    await state.update_data(description=description)
    await state.set_state(AddMovieState.waiting_for_poster)

    await message.answer(
        "🖼 <b>7-Qadam: Kino muqovasini (poster) yuboring:</b>\n\n"
        "Kino posteri rasmini (foto) yuboring yoki muqovasiz davom etish uchun /skip buyrug'ini yuboring.",
        parse_mode="HTML",
    )


@router.message(AddMovieState.waiting_for_poster, F.photo)
async def handle_receive_poster_photo(message: Message, state: FSMContext) -> None:
    """Kino posteri rasmini qabul qilish (eng katta o'lchamli rasm file_id olinadi)."""
    poster_file_id = message.photo[-1].file_id
    await state.update_data(poster_file_id=poster_file_id)
    await state.set_state(AddMovieState.waiting_for_confirm)
    await show_add_movie_confirmation(message, state)


@router.message(AddMovieState.waiting_for_poster, F.text.lower() == "/skip")
async def handle_skip_poster(message: Message, state: FSMContext) -> None:
    """Muqova qo'shishni o'tkazib yuborish."""
    await state.update_data(poster_file_id=None)
    await state.set_state(AddMovieState.waiting_for_confirm)
    await show_add_movie_confirmation(message, state)


@router.message(AddMovieState.waiting_for_poster)
async def handle_invalid_poster(message: Message) -> None:
    """Noto'g'ri poster yuborilganda."""
    await message.answer(
        "❌ Iltimos, kino posteri rasmini (foto) yuboring yoki muqovasiz davom etish uchun /skip deb yozing:"
    )


async def show_add_movie_confirmation(message: Message, state: FSMContext) -> None:
    """Tasdiqlash kartochkasini chiqarish."""
    data = await state.get_data()
    poster_status = "✅ Biriktirilgan" if data.get("poster_file_id") else "❌ Yo'q"

    card_text = (
        "📋 <b>Kino ma'lumotlarini tasdiqlang:</b>\n\n"
        f"• <b>Nomi:</b> {data.get('title')}\n"
        f"• <b>Kodi:</b> <code>{data.get('code')}</code>\n"
        f"• <b>Janri:</b> {data.get('category')}\n"
        f"• <b>Yili:</b> {data.get('year') or 'Ko\'rsatilmagan'}\n"
        f"• <b>Tavsif:</b> {data.get('description') or 'Yo\'q'}\n"
        f"• <b>Muqova:</b> {poster_status}\n"
        f"• <b>Manba:</b> Chat ID: <code>{data.get('source_chat_id')}</code>, "
        f"Msg ID: <code>{data.get('source_message_id')}</code>\n\n"
        "Barcha ma'lumotlar to'g'rimi?"
    )

    await message.answer(card_text, parse_mode="HTML", reply_markup=get_confirm_add_movie_keyboard())


@router.callback_query(F.data == "confirm_save_movie")
async def handle_confirm_save_movie(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    """Kinoni ma'lumotlar bazasiga saqlash."""
    data = await state.get_data()
    if not data or "code" not in data or "title" not in data:
        await callback.answer("Xatolik: Ma'lumotlar topilmadi. Qaytadan urinib ko'ring.", show_alert=True)
        await state.clear()
        return

    # Takroriy kod tekshiruvi (race condition'dan himoya)
    if await db.code_exists(data["code"]):
        await callback.answer("Ushbu kod allaqachon mavjud!", show_alert=True)
        await state.clear()
        return

    try:
        movie_id = await db.add_movie(
            code=data["code"],
            title=data["title"],
            category=data["category"],
            source_chat_id=data["source_chat_id"],
            source_message_id=data["source_message_id"],
            year=data.get("year"),
            description=data.get("description"),
            poster_file_id=data.get("poster_file_id"),
            is_active=1,
        )
        await state.clear()
        poster_info = " (Muqovasi bilan)" if data.get("poster_file_id") else ""
        await callback.message.edit_text(
            f"✅ <b>Kino muvaffaqiyatli saqlandi!</b>{poster_info}\n\n"
            f"• Baza ID: <code>{movie_id}</code>\n"
            f"• Kod: <code>{data['code']}</code>\n"
            f"• Nomi: <b>{data['title']}</b>",
            parse_mode="HTML",
            reply_markup=get_admin_main_keyboard(),
        )
        await callback.answer("Kino saqlandi!")
    except Exception as e:
        logger.exception("Error saving movie: %s", e)
        await callback.answer("Bazaga saqlashda xatolik yuz berdi!", show_alert=True)


# --- STATISTIKA ---

@router.message(F.text == "📊 Statistika")
@router.callback_query(F.data == "admin_stats")
async def handle_admin_stats(event: Message | CallbackQuery, db: Database) -> None:
    """Bot statistikasini chiqarish."""
    stats = await db.get_stats()

    genres_lines = []
    for g, count in stats["genres_stat"].items():
        genres_lines.append(f"  • {g}: <b>{count}</b> ta")
    genres_text = "\n".join(genres_lines) if genres_lines else "  • Hozircha kinolar yo'q"

    text = (
        "📊 <b>MinoTV Bot Statistikasi:</b>\n\n"
        f"👥 <b>Foydalanuvchilar:</b> {stats['total_users']} nafar\n"
        f"🎬 <b>Jami kinolar:</b> {stats['total_movies']} ta\n"
        f"🟢 <b>Faol kinolar:</b> {stats['active_movies']} ta\n"
        f"🔴 <b>Nofaol kinolar:</b> {stats['total_movies'] - stats['active_movies']} ta\n\n"
        f"🎭 <b>Janrlar bo'yicha:</b>\n{genres_text}"
    )

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())
        await event.answer()
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=get_admin_main_keyboard())


# --- KINOLAR RO'YXATI VA BOSHQARISH ---

@router.message(F.text == "📚 Kinolar ro'yxati")
async def handle_admin_movies_list_msg(message: Message, db: Database) -> None:
    """Admin kinolar ro'yxatini chiqarish (1-sahifa)."""
    await show_admin_movies_page(message, db, page=1)


@router.callback_query(AdminMovieCallback.filter(F.action == "page"))
async def handle_admin_movies_list_page(
    callback: CallbackQuery,
    callback_data: AdminMovieCallback,
    db: Database,
) -> None:
    """Admin kinolar ro'yxatida sahifalash."""
    await show_admin_movies_page(callback, db, page=callback_data.page)
    await callback.answer()


async def show_admin_movies_page(event: Message | CallbackQuery, db: Database, page: int) -> None:
    """Kinolar ro'yxatini sahifalash logikasi."""
    page_size = 10
    total_count = await db.count_all_movies()
    total_pages = max(1, ceil(total_count / page_size))
    page = max(1, min(page, total_pages))

    if total_count == 0:
        msg = "📚 Hozircha bazada hech qanday kino mavjud emas."
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(msg, reply_markup=get_admin_main_keyboard())
        else:
            await event.answer(msg, reply_markup=get_admin_main_keyboard())
        return

    movies = await db.get_all_movies(page=page, page_size=page_size)
    text = (
        f"📚 <b>Barcha kinolar ro'yxati</b>\n"
        f"Jami: {total_count} ta (Sahifa: {page}/{total_pages})\n\n"
        "Batafsil ko'rish, tahrirlash yoki o'chirish uchun kinoni tanlang:"
    )

    keyboard = get_admin_movies_list_keyboard(movies, current_page=page, total_pages=total_pages)

    if isinstance(event, CallbackQuery):
        await event.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    else:
        await event.answer(text, parse_mode="HTML", reply_markup=keyboard)


# --- KINO TAFSILOTLARI ---

@router.callback_query(AdminMovieCallback.filter(F.action == "view"))
async def handle_view_movie_detail(
    callback: CallbackQuery,
    callback_data: AdminMovieCallback,
    db: Database,
) -> None:
    """Kino ma'lumotlarini to'liq ko'rsatish."""
    movie = await db.get_movie_by_id(callback_data.movie_id)
    if not movie:
        await callback.answer("Kino topilmadi!", show_alert=True)
        return

    status_str = "🟢 Faol (foydalanuvchilarga ko'rinadi)" if movie["is_active"] == 1 else "🔴 Nofaol (yashirilgan)"
    poster_status = "✅ Mavjud" if movie.get("poster_file_id") else "❌ Mavjud emas"

    text = (
        f"🎬 <b>Kino Tafsilotlari (ID: {movie['id']}):</b>\n\n"
        f"• <b>Nomi:</b> {movie['title']}\n"
        f"• <b>Kodi:</b> <code>{movie['code']}</code>\n"
        f"• <b>Janri:</b> {movie['category']}\n"
        f"• <b>Yili:</b> {movie['year'] or 'Mavjud emas'}\n"
        f"• <b>Muqova:</b> {poster_status}\n"
        f"• <b>Holati:</b> {status_str}\n"
        f"• <b>Tavsif:</b> {movie['description'] or 'Yo\'q'}\n"
        f"• <b>Manba kanal ID:</b> <code>{movie['source_chat_id']}</code>\n"
        f"• <b>Manba xabar ID:</b> <code>{movie['source_message_id']}</code>\n"
        f"• <b>Qo'shilgan vaqti:</b> {movie['created_at']}"
    )

    keyboard = get_admin_movie_detail_keyboard(
        movie_id=movie["id"],
        is_active=movie["is_active"],
        page=callback_data.page,
    )

    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


# --- KINO HOLATINI O'ZGARTIRISH (TOGGLE STATUS) ---

@router.callback_query(AdminMovieCallback.filter(F.action == "toggle"))
async def handle_toggle_status(
    callback: CallbackQuery,
    callback_data: AdminMovieCallback,
    db: Database,
) -> None:
    """Kinoni faol/nofaol qilish."""
    movie = await db.get_movie_by_id(callback_data.movie_id)
    if not movie:
        await callback.answer("Kino topilmadi!", show_alert=True)
        return

    new_status = 0 if movie["is_active"] == 1 else 1
    await db.update_movie(movie["id"], is_active=new_status)

    alert_msg = "Kino nofaol qilindi (yashirildi)" if new_status == 0 else "Kino faollashtirildi"
    await callback.answer(alert_msg)

    # Tafsilotlar ekranini yangilash
    await handle_view_movie_detail(callback, callback_data, db)


# --- KINO O'CHIRISH (DELETE) ---

@router.callback_query(AdminMovieCallback.filter(F.action == "del"))
async def handle_prompt_delete(
    callback: CallbackQuery,
    callback_data: AdminMovieCallback,
    db: Database,
) -> None:
    """Kino o'chirishni tasdiqlashni so'rash."""
    movie = await db.get_movie_by_id(callback_data.movie_id)
    if not movie:
        await callback.answer("Kino topilmadi!", show_alert=True)
        return

    text = (
        f"⚠️ <b>Haqiqatan ham ushbu kinoni o'chirmoqchimisiz?</b>\n\n"
        f"• <b>Nomi:</b> {movie['title']}\n"
        f"• <b>Kodi:</b> <code>{movie['code']}</code>\n\n"
        "Bu amalni ortga qaytarib bo'lmaydi!"
    )
    keyboard = get_delete_confirmation_keyboard(movie_id=movie["id"], page=callback_data.page)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AdminMovieCallback.filter(F.action == "confirm_del"))
async def handle_confirm_delete(
    callback: CallbackQuery,
    callback_data: AdminMovieCallback,
    db: Database,
) -> None:
    """Kinoni bazadan butunlay o'chirish."""
    movie_id = callback_data.movie_id
    success = await db.delete_movie(movie_id)

    if success:
        await callback.answer("✅ Kino muvaffaqiyatli o'chirildi!", show_alert=True)
    else:
        await callback.answer("Kino topilmadi yoki allaqachon o'chirilgan.", show_alert=True)

    await show_admin_movies_page(callback, db, page=callback_data.page)


# --- KINO TAHRIRLASH (EDIT) ---

@router.callback_query(AdminMovieCallback.filter(F.action == "edit"))
async def handle_prompt_edit_fields(
    callback: CallbackQuery,
    callback_data: AdminMovieCallback,
) -> None:
    """Tahrirlash uchun maydon tanlash menyusini ochish."""
    text = "✏️ <b>Qaysi ma'lumotni tahrirlamoqchisiz?</b>"
    keyboard = get_admin_edit_fields_keyboard(movie_id=callback_data.movie_id, page=callback_data.page)
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(AdminEditFieldCallback.filter())
async def handle_select_edit_field(
    callback: CallbackQuery,
    callback_data: AdminEditFieldCallback,
    state: FSMContext,
) -> None:
    """Tahrirlanadigan maydon tanlanganda."""
    field = callback_data.field
    movie_id = callback_data.movie_id

    await state.update_data(edit_movie_id=movie_id, edit_field=field)

    if field == "category":
        await callback.message.edit_text(
            "🎭 Yangi janrni tanlang:",
            reply_markup=get_admin_genre_selection_keyboard(prefix="adm_edit_cat"),
        )
        await callback.answer()
        return

    if field == "poster":
        await state.set_state(EditMovieState.waiting_for_value)
        prompt_text = (
            "🖼 <b>Kino muqovasini tahrirlash:</b>\n\n"
            "Yangi poster rasmini (foto) yuboring yoki mavjud muqovani butunlay olib tashlash uchun /remove yozing."
        )
        await callback.message.edit_text(prompt_text, parse_mode="HTML")
        await callback.answer()
        return

    field_labels = {
        "title": "yangi nomini",
        "code": "yangi unikal kodini (faqat raqamlar)",
        "year": "yangi yilini (4 xonali raqam yoki tozalash uchun /empty)",
        "description": "yangi tavsifini (yoki tozalash uchun /empty)",
    }

    await state.set_state(EditMovieState.waiting_for_value)
    prompt_text = f"📝 Iltimos, kino uchun {field_labels.get(field, 'yangi qiymat')}ni kiriting:"
    await callback.message.edit_text(prompt_text)
    await callback.answer()


@router.callback_query(F.data.startswith("adm_edit_cat:"))
async def handle_edit_category_save(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
) -> None:
    """Janrni tahrirlashni saqlash."""
    new_category = callback.data.split(":", 1)[1]
    data = await state.get_data()
    movie_id = data.get("edit_movie_id")

    if not movie_id:
        await callback.answer("Xatolik yuz berdi. Qaytadan urinib ko'ring.", show_alert=True)
        return

    await db.update_movie(movie_id, category=new_category)
    await state.clear()
    await callback.answer("Janr yangilandi!")

    # Yangilangan kino tafsilotini ko'rsatish
    await handle_view_movie_detail(
        callback,
        AdminMovieCallback(action="view", movie_id=movie_id, page=1),
        db,
    )


@router.message(EditMovieState.waiting_for_value)
async def handle_receive_edit_value(
    message: Message,
    state: FSMContext,
    db: Database,
) -> None:
    """Tahrirlangan qiymatni saqlash."""
    data = await state.get_data()
    movie_id = data.get("edit_movie_id")
    field = data.get("edit_field")
    raw_val = (message.text or "").strip()

    if not movie_id or not field:
        await message.answer("Sessiya eskirgan. /admin buyrug'ini yuboring.")
        await state.clear()
        return

    val = None
    if field == "poster":
        if message.photo:
            val = message.photo[-1].file_id
        elif raw_val.lower() == "/remove":
            val = None
        else:
            await message.answer(
                "❌ Iltimos, yangi poster rasmini (foto) yuboring yoki muqovani o'chirish uchun /remove deb yozing:"
            )
            return
    elif field == "code":
        if not raw_val.isdigit():
            await message.answer("❌ Kino kodi faqat raqamlardan iborat bo'lishi kerak! Qayta kiriting:")
            return
        # Boshqa kinoda bu kod bor-yo'qligini tekshirish
        existing = await db.get_movie_by_code(raw_val, active_only=False)
        if existing and existing["id"] != movie_id:
            await message.answer(f"❌ <b>{raw_val}</b> kodi boshqa kinoda band! Boshqa kod kiriting:", parse_mode="HTML")
            return
        val = raw_val
    elif field == "year":
        if raw_val.lower() == "/empty":
            val = None
        else:
            if not raw_val.isdigit() or len(raw_val) != 4:
                await message.answer("❌ 4 xonali to'g'ri yil kiriting yoki tozalash uchun /empty yozing:")
                return
            val = int(raw_val)
    elif field == "description":
        val = None if raw_val.lower() == "/empty" else raw_val
    elif field == "title":
        if not raw_val:
            await message.answer("Kino nomi bo'sh bo'lishi mumkin emas!")
            return
        val = raw_val

    # Bazada yangilash
    await db.update_movie(movie_id, **{field: val})
    await state.clear()

    await message.answer("✅ Ma'lumot muvaffaqiyatli yangilandi!")
    # Yangilangan kinoni chiqarish
    movie = await db.get_movie_by_id(movie_id)
    if movie:
        status_str = "🟢 Faol" if movie["is_active"] == 1 else "🔴 Nofaol"
        poster_status = "✅ Mavjud" if movie.get("poster_file_id") else "❌ Mavjud emas"
        text = (
            f"🎬 <b>Kino Yangilandi (ID: {movie['id']}):</b>\n\n"
            f"• <b>Nomi:</b> {movie['title']}\n"
            f"• <b>Kodi:</b> <code>{movie['code']}</code>\n"
            f"• <b>Janri:</b> {movie['category']}\n"
            f"• <b>Yili:</b> {movie['year'] or 'Mavjud emas'}\n"
            f"• <b>Muqova:</b> {poster_status}\n"
            f"• <b>Holati:</b> {status_str}\n"
            f"• <b>Tavsif:</b> {movie['description'] or 'Yo\'q'}\n"
        )
        keyboard = get_admin_movie_detail_keyboard(movie_id=movie["id"], is_active=movie["is_active"], page=1)
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)

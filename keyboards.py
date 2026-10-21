from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.filters.callback_data import CallbackData
from config import GENRES


# --- CALLBACK DATA DEFINITIONS ---

class CategoryNavCallback(CallbackData, prefix="cat"):
    genre_idx: int
    page: int


class MovieSelectCallback(CallbackData, prefix="mov"):
    movie_id: int


class SearchNavCallback(CallbackData, prefix="srch"):
    page: int


class AdminMovieCallback(CallbackData, prefix="amov"):
    action: str  # "view", "edit", "del", "toggle", "page", "confirm_del"
    movie_id: int = 0
    page: int = 1


class AdminEditFieldCallback(CallbackData, prefix="aedit"):
    field: str  # "title", "code", "cat", "year", "desc"
    movie_id: int


# --- FOYDALANUVCHI KEYBOARDLARI ---

def get_main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Asosiy foydalanuvchi reply menyusi."""
    keyboard = [
        [
            KeyboardButton(text="🔢 Kino kodini kiritish"),
            KeyboardButton(text="🎭 Janrlar"),
        ],
        [
            KeyboardButton(text="🔍 Kino qidirish"),
            KeyboardButton(text="ℹ️ Yordam"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_cancel_reply_keyboard() -> ReplyKeyboardMarkup:
    """Bekor qilish reply tugmasi."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def get_genres_keyboard() -> InlineKeyboardMarkup:
    """Janrlar inline menyusi."""
    buttons = []
    # Janrlarni 2 tadan qilib joylashtirish
    for i in range(0, len(GENRES), 2):
        row = [
            InlineKeyboardButton(
                text=f"🎬 {GENRES[i]}",
                callback_data=CategoryNavCallback(genre_idx=i, page=1).pack(),
            )
        ]
        if i + 1 < len(GENRES):
            row.append(
                InlineKeyboardButton(
                    text=f"🎬 {GENRES[i + 1]}",
                    callback_data=CategoryNavCallback(genre_idx=i + 1, page=1).pack(),
                )
            )
        buttons.append(row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_movies_pagination_keyboard(
    movies: list[dict],
    current_page: int,
    total_pages: int,
    genre_idx: int,
) -> InlineKeyboardMarkup:
    """Janr bo'yicha sahifalangan kinolar inline tugmalari."""
    buttons = []

    # Har bir kino uchun alohida tugma
    for movie in movies:
        title_text = f"▶️ {movie['title']}"
        if movie.get("year"):
            title_text += f" ({movie['year']})"
        buttons.append([
            InlineKeyboardButton(
                text=title_text,
                callback_data=MovieSelectCallback(movie_id=movie["id"]).pack(),
            )
        ])

    # Sahifalash tugmalari
    nav_row = []
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=CategoryNavCallback(genre_idx=genre_idx, page=current_page - 1).pack(),
            )
        )

    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {current_page}/{max(1, total_pages)}",
            callback_data="noop",
        )
    )

    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=CategoryNavCallback(genre_idx=genre_idx, page=current_page + 1).pack(),
            )
        )

    if nav_row:
        buttons.append(nav_row)

    # Ortga tugmasi
    buttons.append([
        InlineKeyboardButton(
            text="🔙 Janrlarga qaytish",
            callback_data="back_to_genres",
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_search_results_keyboard(
    movies: list[dict],
    current_page: int = 1,
    total_pages: int = 1,
) -> InlineKeyboardMarkup:
    """Qidiruv natijalari uchun inline tugmalar."""
    buttons = []
    for movie in movies:
        title_text = f"▶️ {movie['title']}"
        if movie.get("year"):
            title_text += f" ({movie['year']})"
        buttons.append([
            InlineKeyboardButton(
                text=title_text,
                callback_data=MovieSelectCallback(movie_id=movie["id"]).pack(),
            )
        ])

    nav_row = []
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=SearchNavCallback(page=current_page - 1).pack(),
            )
        )

    if total_pages > 1:
        nav_row.append(
            InlineKeyboardButton(
                text=f"📄 {current_page}/{total_pages}",
                callback_data="noop",
            )
        )

    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=SearchNavCallback(page=current_page + 1).pack(),
            )
        )

    if nav_row:
        buttons.append(nav_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


# --- ADMIN KEYBOARDLARI ---

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    """Admin asosiy menyusi (Inline)."""
    buttons = [
        [
            InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="admin_add_movie"),
            InlineKeyboardButton(text="📚 Kinolar ro'yxati", callback_data=AdminMovieCallback(action="page", page=1).pack()),
        ],
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="🔍 Qidirish", callback_data="admin_search_movie"),
        ],
        [
            InlineKeyboardButton(text="❌ Yopish", callback_data="admin_close"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_reply_keyboard() -> ReplyKeyboardMarkup:
    """Admin tezkor reply menyusi."""
    keyboard = [
        [
            KeyboardButton(text="➕ Kino qo'shish"),
            KeyboardButton(text="📚 Kinolar ro'yxati"),
        ],
        [
            KeyboardButton(text="📊 Statistika"),
            KeyboardButton(text="❌ Bekor qilish"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)


def get_admin_genre_selection_keyboard(prefix: str = "adm_cat") -> InlineKeyboardMarkup:
    """Kino qo'shish/tahrirlashda janr tanlash."""
    buttons = []
    for i in range(0, len(GENRES), 2):
        row = [
            InlineKeyboardButton(text=GENRES[i], callback_data=f"{prefix}:{GENRES[i]}")
        ]
        if i + 1 < len(GENRES):
            row.append(
                InlineKeyboardButton(text=GENRES[i + 1], callback_data=f"{prefix}:{GENRES[i + 1]}")
            )
        buttons.append(row)
    buttons.append([
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_confirm_add_movie_keyboard() -> InlineKeyboardMarkup:
    """Kino qo'shishni tasdiqlash tugmalari."""
    buttons = [
        [
            InlineKeyboardButton(text="✅ Saqlash", callback_data="confirm_save_movie"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_action"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_movies_list_keyboard(
    movies: list[dict],
    current_page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    """Admin uchun sahifalangan kinolar ro'yxati."""
    buttons = []
    for m in movies:
        status_icon = "🟢" if m.get("is_active", 1) == 1 else "🔴"
        title_text = f"{status_icon} [{m['code']}] {m['title']}"
        buttons.append([
            InlineKeyboardButton(
                text=title_text[:40],
                callback_data=AdminMovieCallback(action="view", movie_id=m["id"], page=current_page).pack(),
            )
        ])

    nav_row = []
    if current_page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅️ Oldingi",
                callback_data=AdminMovieCallback(action="page", page=current_page - 1).pack(),
            )
        )

    nav_row.append(
        InlineKeyboardButton(
            text=f"📄 {current_page}/{max(1, total_pages)}",
            callback_data="noop",
        )
    )

    if current_page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Keyingi ➡️",
                callback_data=AdminMovieCallback(action="page", page=current_page + 1).pack(),
            )
        )

    if nav_row:
        buttons.append(nav_row)

    buttons.append([
        InlineKeyboardButton(text="🔙 Admin bosh menyusi", callback_data="admin_menu")
    ])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_movie_detail_keyboard(movie_id: int, is_active: int, page: int) -> InlineKeyboardMarkup:
    """Admin tomonidan tanlangan kino tafsilotlari va harakatlar."""
    toggle_text = "🔴 Nofaol qilish" if is_active == 1 else "🟢 Faollashtirish"
    buttons = [
        [
            InlineKeyboardButton(
                text="✏️ Tahrirlash",
                callback_data=AdminMovieCallback(action="edit", movie_id=movie_id, page=page).pack(),
            ),
            InlineKeyboardButton(
                text=toggle_text,
                callback_data=AdminMovieCallback(action="toggle", movie_id=movie_id, page=page).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🗑 Kino o'chirish",
                callback_data=AdminMovieCallback(action="del", movie_id=movie_id, page=page).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Ro'yxatga qaytish",
                callback_data=AdminMovieCallback(action="page", page=page).pack(),
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_admin_edit_fields_keyboard(movie_id: int, page: int) -> InlineKeyboardMarkup:
    """Tahrirlanadigan maydonlarni tanlash."""
    buttons = [
        [
            InlineKeyboardButton(
                text="🏷 Nomi",
                callback_data=AdminEditFieldCallback(field="title", movie_id=movie_id).pack(),
            ),
            InlineKeyboardButton(
                text="🔢 Kodi",
                callback_data=AdminEditFieldCallback(field="code", movie_id=movie_id).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🎭 Janri",
                callback_data=AdminEditFieldCallback(field="category", movie_id=movie_id).pack(),
            ),
            InlineKeyboardButton(
                text="📅 Yili",
                callback_data=AdminEditFieldCallback(field="year", movie_id=movie_id).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="📝 Tavsif",
                callback_data=AdminEditFieldCallback(field="description", movie_id=movie_id).pack(),
            ),
            InlineKeyboardButton(
                text="🖼 Muqova",
                callback_data=AdminEditFieldCallback(field="poster", movie_id=movie_id).pack(),
            ),
        ],
        [
            InlineKeyboardButton(
                text="🔙 Ortga",
                callback_data=AdminMovieCallback(action="view", movie_id=movie_id, page=page).pack(),
            ),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_delete_confirmation_keyboard(movie_id: int, page: int) -> InlineKeyboardMarkup:
    """O'chirishni tasdiqlash."""
    buttons = [
        [
            InlineKeyboardButton(
                text="⚠️ Ha, o'chirilsin",
                callback_data=AdminMovieCallback(action="confirm_del", movie_id=movie_id, page=page).pack(),
            ),
            InlineKeyboardButton(
                text="❌ Bekor qilish",
                callback_data=AdminMovieCallback(action="view", movie_id=movie_id, page=page).pack(),
            ),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

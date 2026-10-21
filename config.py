import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env faylini yuklash
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def parse_admin_ids(raw_ids: str | None) -> list[int]:
    """Admin IDlarini xavfsiz parse qilish."""
    if not raw_ids:
        return []
    ids: list[int] = []
    for item in raw_ids.split(","):
        cleaned = item.strip()
        if not cleaned:
            continue
        try:
            ids.append(int(cleaned))
        except ValueError:
            print(f"[OGOHLANTIRISH] Yaroqsiz admin ID topildi: {cleaned}", file=sys.stderr)
    return ids


def parse_channel_id(raw_id: str | None) -> int | None:
    """Kanal ID sini xavfsiz parse qilish."""
    if not raw_id:
        return None
    try:
        return int(raw_id.strip())
    except ValueError:
        return None


# Konfiguratsiya sinfi
class Config:
    def __init__(self, validate_token: bool = True):
        self.bot_token: str = os.getenv("BOT_TOKEN", "").strip()
        if validate_token and not self.bot_token:
            raise ValueError(
                "BOT_TOKEN topilmadi yoki bo'sh!\n"
                "Iltimos, .env faylini yarating va BOT_TOKEN qiymatini kiriting.\n"
                "Namuna uchun .env.example fayliga qarang."
            )

        self.admin_ids: list[int] = parse_admin_ids(os.getenv("ADMIN_IDS"))
        self.source_channel_id: int | None = parse_channel_id(os.getenv("SOURCE_CHANNEL_ID"))
        self.db_path: str = os.getenv("DB_PATH", str(BASE_DIR / "minotv.db")).strip()

    def is_admin(self, user_id: int) -> bool:
        """Foydalanuvchi admin ekanligini tekshirish."""
        return user_id in self.admin_ids


# Mavjud kino janrlari ro'yxati
GENRES: list[str] = [
    "Fantastika",
    "Multfilm",
    "Jangari",
    "Komediya",
    "Drama",
    "Dahshat",
    "Sarguzasht",
    "Romantika",
    "Detektiv",
    "Anime",
    "Boshqa",
]

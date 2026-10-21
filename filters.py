from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message
from config import Config


class IsAdminFilter(BaseFilter):
    """Foydalanuvchi admin ekanligini tekshiruvchi filtr."""

    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return False
        return config.is_admin(user_id)

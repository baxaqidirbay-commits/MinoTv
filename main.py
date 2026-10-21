import asyncio
import logging
import os
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from config import Config
from database import Database
from handlers.admin import router as admin_router
from handlers.user import router as user_router

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("minotv")


async def start_health_server() -> web.AppRunner | None:
    """Render yoki boshqa hostinglar uchun fonda ishlaydigan health check web server."""
    port_str = os.getenv("PORT")
    if not port_str or not port_str.isdigit():
        return None

    port = int(port_str)
    app = web.Application()

    async def handle_ping(request: web.Request) -> web.Response:
        return web.Response(text="MinoTV Bot is running 24/7!", content_type="text/plain")

    app.router.add_get("/", handle_ping)
    app.router.add_get("/health", handle_ping)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info("Health-check web server %d-portda ishga tushdi (Render uchun).", port)
    return runner


async def setup_bot_commands(bot: Bot) -> None:
    """Telegram menyusidagi asosiy buyruqlar."""
    commands = [
        BotCommand(command="start", description="Botni ishga tushirish"),
        BotCommand(command="help", description="Yordam va qo'llanma"),
        BotCommand(command="admin", description="Admin paneli (faqat adminlar uchun)"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.warning("Bot buyruqlarini o'rnatishda xatolik: %s", e)


async def main() -> None:
    logger.info("MinoTV bot ishga tushirilmoqda...")

    # 1. Konfiguratsiyani yuklash
    try:
        config = Config(validate_token=True)
    except ValueError as e:
        logger.critical("\n[XATOLIK] %s\n", e)
        sys.exit(1)

    # 2. Ma'lumotlar bazasini initsializatsiya qilish
    db = Database(config.db_path)
    await db.init_db()
    logger.info("SQLite ma'lumotlar bazasi tayyor: %s", config.db_path)

    # 3. Bot va Dispatcher yaratish
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Dependency injection (db va config barcha handlerlar va filtrlarga uzatiladi)
    dp["db"] = db
    dp["config"] = config

    # 4. Routerlarni ulash (admin router birinchi bo'lib tekshiriladi)
    dp.include_router(admin_router)
    dp.include_router(user_router)

    # 5. Buyruqlarni sozlash
    await setup_bot_commands(bot)

    # 6. Pollingni boshlash
    logger.info("Adminlar soni: %d", len(config.admin_ids))
    logger.info("MinoTV Bot muvaffaqiyatli ishga tushdi va xabarlarni qabul qilmoqda (Polling)...")

    health_runner = await start_health_server()

    try:
        # Eski update'larni tozalash (drop pending updates)
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("Bot to'xtatildi.")
    except Exception as e:
        logger.exception("Kutilmagan xatolik: %s", e)
    finally:
        if health_runner:
            await health_runner.cleanup()
        await bot.session.close()
        logger.info("Bot sessiyasi yopildi.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Dastur to'xtatildi.")

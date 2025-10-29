import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from aiogram.client.default import DefaultBotProperties
from config import Config, load_config
from src.database.base import Base
# ensure_primary_admin funksiyasi sign_data.py dan import qilinishi shart!
from src.database.sign_data import User, ensure_primary_admin
from src.handlers import registration, test, admin
from aiogram.types import BotCommand
from src.handlers.registration import set_default_commands

logger = logging.getLogger(__name__)


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(filename)s:%(lineno)d #%(levelname)-8s "
               "[%(asctime)s] - %(name)s - %(message)s",
    )

    logger.info("Starting bot")
    config: Config = load_config()
    engine = create_async_engine(
        config.db.url,
        echo=False
    )

    # ------------------------------------------------------------
    # 1. ADMIN MA'LUMOTLARI QATTIQ BELGILANDI
    # ------------------------------------------------------------
    SUPER_ADMIN_ID = 6027539464
    ADMIN_FIRST_NAME = "Abror"
    ADMIN_LAST_NAME = "Bobonazarov"

    logger.info("Checking database tables...")
    async with engine.begin() as conn:
        # DB'dagi barcha jadvallarni yaratadi
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)
    logger.info("Database setup complete.")

    session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        engine, expire_on_commit=False
    )

    # ------------------------------------------------------------
    # 2. SUPER ADMINNI DBGA QO'SHISH/YANGILASH MANTIG'I
    # ------------------------------------------------------------
    logger.info(f"Super Admin {SUPER_ADMIN_ID}ni ta'minlash boshlandi...")
    async with session_factory() as session:
        # ensure_primary_admin funksiyasi orqali admin yaratiladi yoki huquqi tiklanadi
        await ensure_primary_admin(
            session,
            tg_id=SUPER_ADMIN_ID,
            first_name=ADMIN_FIRST_NAME,
            last_name=ADMIN_LAST_NAME
        )
    logger.info(f"Super Admin ({ADMIN_FIRST_NAME} {ADMIN_LAST_NAME}) ta'minlandi.")
    # ------------------------------------------------------------

    bot: Bot = Bot(token=config.tg_bot.token, default=DefaultBotProperties(parse_mode="HTML"))
    dp: Dispatcher = Dispatcher(storage=MemoryStorage())

    # Komandalarni o'rnatish
    await set_default_commands(bot)

    # Routerlarni ulash
    dp.include_router(registration.router)
    dp.include_router(test.router)
    dp.include_router(admin.router)

    # Botni ishga tushirish
    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(
        bot,
        session_factory=session_factory,
        config=config,
        timeout=60
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")
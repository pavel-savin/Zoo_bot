import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import config
from app import router


async def main():
    bot = Bot(token=config.TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

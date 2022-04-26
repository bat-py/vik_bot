import configparser
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext

import admin_panel
import sql_handler
import registration
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import checkup

config = configparser.ConfigParser()
config.read('config.ini')
API_TOKEN = config['main']['api_token']

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=API_TOKEN, parse_mode='html')
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)


@dp.message_handler(lambda message: message.text == 'testtt')
async def testtt(message: types.Message, state: FSMContext):
    a = await message.bot.send_message(
        message.chat.id,
        'helloooooo'
    )
    print(a.message_id)


if __name__ == '__main__':
    registration.register_handlers(dp)
    admin_panel.register_handlers(dp)
    checkup.register_handlers(dp)
    checkup.scheduler.start()

    executor.start_polling(dp, skip_updates=True, on_startup=checkup.schedule_jobs)

import configparser
import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
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


@dp.message_handler(content_types=['location'])
async def location(message: types.Message):
    #await message.bot.send_location(
    #    message.chat.id,
    #    message.location.latitude,
    #    message.location.longitude
    #)
    latitude = message.location.latitude
    longitude = message.location.longitude
    print(latitude)
    print(longitude)

    link = f"https://www.google.com/maps?q={latitude},{longitude}&ll={latitude},{longitude}&z=16"
    msg = f'Ответ: <a href="{link}">Your geolocation</a>'

    await message.answer(msg, disable_web_page_preview=True)


if __name__ == '__main__':
    registration.register_handlers(dp)
    admin_panel.register_handlers(dp)
    checkup.register_handlers(dp)
    checkup.scheduler.start()

    executor.start_polling(dp, skip_updates=True, on_startup=checkup.schedule_jobs)


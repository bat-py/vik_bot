import configparser
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
import button_creators
import sql_handler
from aiogram import types, Dispatcher

config = configparser.ConfigParser()
config.read('config.ini')


class MyStates(StatesGroup):
    waiting_for_password = State()


async def admin_command_handler(message: types.Message):
    """
    Обработывает команду /admin
    :param message:
    :return:
    """
    chat_id = message.chat.id
    # Если возвращает пользователь уже есть в списке тогда он возвращает chat_id этого админа
    check_admin_exist = sql_handler.check_admin_exist(chat_id)

    # Если он уже есть в таблице "admins" просто вернем главное меню
    if check_admin_exist:
        await main_menu(message)

    # Если этого пользователя нету в списке админов, тогда попросит ввести пароль
    else:
        # password = sql_handler.get_admin_menu_password()

        # Установим статус на waiting_for_password
        await MyStates.waiting_for_password.set()

        msg = config['msg']['enter_password']

        # Создаем кнопку Отменить
        cancel = config['msg']['cancel']
        button = button_creators.reply_keyboard_creator([[cancel]])

        await message.bot.send_message(
            chat_id,
            msg,
            reply_markup=button
        )


async def check_password(message: types.Message, state: FSMContext):
    """
    Проверяет введенный пароль
    :param message:
    :return:
    """

    # Если нажал на кнопку Отменить, тогда остановим state и отправим смс что успешно отменено
    if message.text == config['msg']['cancel']:
        await state.finish()

        msg = config['msg']['canceled']
        # Нужен чтобы скрыть reply markup кнопки
        hide_reply_markup = button_creators.hide_reply_buttons()
        await message.bot.send_message(
            message.chat.id,
            msg,
            reply_markup=hide_reply_markup
        )
    # Запуститься если пользователь ввел пароль
    else:
        password = sql_handler.get_admin_menu_password()

        # Если пароль правильный, добавим этого пользователя в таблицу админов и он начнет получать уведомления
        if message.text.strip() == password:
            chat_id = message.chat.id
            first_name = message.chat.first_name
            # Добавим пользователя в таблицу "admins"
            sql_handler.add_new_admin(chat_id, first_name)

            # Отправим сообщения что он зарегистрирован успешно ###########################
            msg = config['msg']['your_account_registered']
            await message.bot.send_message(
                message.chat.id,
                msg
            )

            # Остановим state "waiting_for_password"
            await state.finish()

            # Отправим главное меню
            await main_menu(message)

        # Если не правильный тогда попросит еще раз ввести
        else:
            msg = config['msg']['wrong_password']
            await message.bot.send_message(
                message.chat.id,
                msg
            )


async def main_menu(message: types.Message):
    # Создаем кнопки
    buttons_name = [[config['msg']['on_off']], [config['msg']['missing']], [config['msg']['report']]]

    buttons = button_creators.reply_keyboard_creator(buttons_name)

    # Составим сообщение
    msg1 = config['msg']['welcome_admin']
    msg2 = message.chat.first_name
    msg = f"{msg1} <b>{msg2}</b>"

    await message.bot.send_message(
        message.chat.id,
        msg,
        reply_markup=buttons
    )


async def on_off_menu_handler(message: types.Message):
    check_admin = sql_handler.check_admin_exist(message.chat.id)

    # Если он зарегистрирован и есть в базе
    if check_admin:
        status = sql_handler.get_admin_notification_status(message.chat.id)

        # Если статус был 0 поменяем на 1 или наоборот
        if status:
            sql_handler.update_admin_notification_status(message.chat.id, 0)
            msg = config['msg']['notification_off']
        else:
            sql_handler.update_admin_notification_status(message.chat.id, 1)
            msg = config['msg']['notification_on']

        await message.bot.send_message(
            message.chat.id,
            msg
        )


async def missing_list_handler(message: types.Message):
    """
    Запустить если пользователь нажал на "Список отсутствующих" и он вернет список тех кого сейчас нету
    :param message:
    :return:
    """
    # Получаем ID тех кто пришел
    ids_who_came = sql_handler.get_todays_logins()
    ids_who_came = [int(i[0]) for i in ids_who_came]
    # Список всех пользователей (только те где Who == 'Control')
    all_members_id = sql_handler.get_all_users_id(control=True)
    all_members_id = [i[0] for i in all_members_id]

    # Список опоздавших
    latecommers = []
    for i in all_members_id:
        if i not in ids_who_came:
            latecommers.append(i)

    # Получаем список опоздавших: [(ID, Name, chat_id), ...]
    latecommer_users = sql_handler.get_users_name_chat_id(latecommers)
    latecommer_users_names_list = list(map(lambda user: user[1], latecommer_users))

    msg1 = config['msg']['missing_full']
    msg2 = '\n'.join(latecommer_users_names_list)
    msg = msg1 + '\n' + msg2

    await message.bot.send_message(
        message.chat.id,
        msg
    )


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(
        admin_command_handler,
        commands=['admin']
    )

    dp.register_message_handler(
        check_password,
        content_types=['text'],
        state=MyStates.waiting_for_password
    )

    dp.register_message_handler(
        on_off_menu_handler,
        lambda message: message.text == config['msg']['on_off']
    )

    dp.register_message_handler(
        missing_list_handler,
        lambda message: message.text == config['msg']['missing']
    )
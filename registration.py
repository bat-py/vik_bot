import configparser

from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
import button_creators
import sql_handler
from aiogram import types, Dispatcher

config = configparser.ConfigParser()
config.read('config.ini')


class MyStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_user_id_confirmation = State()


async def start_command_handler(message: types.Message):
    msg1 = config['msg']['choose_your_name']

    # Creating list of members: id) firstname lastname
    users_list = sql_handler.get_all_users()
    id_name_list = list(map(lambda row: [row[0], row[1]], users_list))
    id_name_str = [f'{row[0]}) {row[1]}' for row in id_name_list]
    msg2 = '\n'.join(id_name_str)

    msg = msg1 + '\n' + msg2

    await MyStates.waiting_for_user_id.set()
    await message.bot.send_message(
        message.chat.id,
        msg
    )


async def user_id_confirmation(message: types.Message, state: FSMContext):
    """
    #Запуститься после того как пользователь выбрал свой ID, а функция попросит подтвердить(Да или НЕТ) выбор у пользователя
    :param message:
    :return:
    """
    choosen_id = message.text
    users_id = sql_handler.get_all_users_id()
    users_id_list = list(map(lambda user: int(user[0]), users_id))

    if choosen_id.isdigit():
        # Если пользователь выбрал существующий ID номер
        if int(choosen_id) in users_id_list:
            # Создаем сообщения о подтверждении и кнопки "Да" и "Нет"
            user_name = sql_handler.get_user_name(choosen_id)
            msg1 = config['msg']['confirmation']
            msg = f"<b>{user_name}</b> {msg1}"
            yes_and_no_buttons = button_creators.reply_keyboard_creator([['Да', 'Нет']], one_time=True)

            # Сохраняем выбранный номер
            await state.update_data(choosen_id=choosen_id)

            await MyStates.waiting_for_user_id_confirmation.set()
            await message.bot.send_message(
                message.chat.id,
                msg,
                reply_markup=yes_and_no_buttons
            )

        # Если выбрал число, но числа нет в списке
        else:
            msg = config['msg']['wrong_number']
            await message.bot.send_message(
                message.chat.id,
                msg
            )
    # Если отправил не целое число
    else:
        msg = config['msg']['not_integer']
        await message.bot.send_message(
            message.chat.id,
            msg
        )


#Запуститься после того как пользователь подтвердил свой выбор
async def user_id_confirmed(message: types.Message, state: FSMContext):
    if  message.text == 'Да':
        all_data = await state.get_data()
        user_id = all_data['choosen_id']

        # Сохранит chat_id пользователя в базу, а если уже есть то обновит
        sql_handler.update_chat_id(message.chat.id, user_id)

        # Аннулируем state
        await state.finish()

        msg = config['msg']['your_account_registered']
        await message.bot.send_message(
            message.chat.id,
            msg
        )

    elif message.text == 'Нет':
        await start_command_handler(message)
    else:
        pass


def register_handlers(dp: Dispatcher):
    dp.register_message_handler(
        start_command_handler,
        commands=['registration']
    )

    dp.register_message_handler(
        user_id_confirmation,
        state=MyStates.waiting_for_user_id
    )

    dp.register_message_handler(
        user_id_confirmed,
        state=MyStates.waiting_for_user_id_confirmation
    )
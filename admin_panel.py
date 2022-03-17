import configparser
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
import button_creators
import sql_handler
from aiogram import types, Dispatcher
import datetime

config = configparser.ConfigParser()
config.read('config.ini')


class MyStates(StatesGroup):
    waiting_for_password = State()
    waiting_for_worker_number = State()
    waiting_for_term = State()


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
        # Отправим сообщения "добро пожаловать админ first_name"
        msg1 = config['msg']['welcome_admin']
        msg2 = message.chat.first_name
        msg = f"{msg1} <b>{msg2}</b>"
        await message.answer(msg)

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

            # Отправим сообщения "добро пожаловать админ first_name"
            msg1 = config['msg']['welcome_admin']
            msg2 = message.chat.first_name
            msg = f"{msg1} <b>{msg2}</b>"
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
    msg = config['msg']['main_menu']

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


async def report_handler(message: types.Message, state: FSMContext):
    """
    Запуститься после того как админ нажал на кнопку "Отчет". Функция отправит список всех рабочих чтобы он выбрал
    и кнопку "главное меню"
    :param state:
    :param message:
    :return:
    """
    # Получаем список всех рабочих(who=control): [(ID, name, Who, chat_id), ...]
    users_list = sql_handler.get_all_workers()

    # Составим из users_list библиотеку {1: [ID, name, Who, chat_id], 2:...}
    users_dict = {}
    for i in range(len(users_list)):
        users_dict[str(i+1)] = users_list[i]
    # Сохраним users_dict в state, он потом нам понадобиться
    await state.update_data(users_dict=users_dict)

    msg1 = config['msg']['choose_worker']
    # Составим список всех рабочих чтобы отправить виде смс админу: ['1) Alisher Raximov', '', ...]
    nomer_name_list = [f'{nomer}) {data[1]}' for nomer, data in users_dict.items()]
    msg2 = '\n'.join(nomer_name_list)
    msg = msg1 + '\n' + msg2

    # Создадим кнопку "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['main_menu']]])

    # Устанавливаем статус
    await MyStates.waiting_for_worker_number.set()

    await message.answer(msg, reply_markup=button)


async def choosen_worker_handler(message: types.Message, state: FSMContext):
    """
    Запуститься после того как админ выбрал номер рабочего
    :param message:
    :param state:
    :return:
    """
    data = await state.get_data()
    # Получим "users_list" библиотеку {'1': [ID, name, Who, chat_id], 2:...}
    users_dict = data['users_dict']
    workers_numbers_list = users_dict.keys()

    if message.text == config['msg']['main_menu']:
        await state.finish()
        await main_menu(message)
    # Если админ выбрал существующий номер, спросим сколько дней отчета надо показать
    elif message.text in workers_numbers_list:
        chosen_worker_info = users_dict[message.text]
        # Сохраним выбранного работника в память (ID, name, Who, chat_id)
        await state.update_data(chosen_worker=chosen_worker_info)

        # Меняем статус на waiting_for_term
        await MyStates.waiting_for_term.set()

        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['main_menu']]])

        # Составим сообщения: "Вы выбрали: Name"
        msg1 = config['msg']['you_chose'] + chosen_worker_info[1]
        msg2 = config['msg']['term']
        msg = msg1 + '\n\n' + msg2

        await message.answer(
            msg,
            reply_markup=button
        )

    # Если админ выбрал несуществующий номер
    else:
        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['main_menu']]])

        msg = config['msg']['wrong_number']
        await message.answer(msg, reply_markup=button)


async def chosen_term_handler(message: types.Message, state: FSMContext):
    """
    Запуститься после того как пользователь выбрал сколько дней отчета надо показать(1-31)
    :param state:
    :param message:
    :return:
    """
    str_numbers = [str(i) for i in range(1,31)]

    # Если нажал на кнопку назад
    if message.text == config['msg']['main_menu']:
        await state.finish()
        await main_menu(message)
    # Если отправил число от 1 до 30
    elif message.text.strip() in str_numbers:
        all_data = await state.get_data()
        # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
        chosen_worker = all_data['chosen_worker']
        chosen_term = message.text.strip()

        # Отключаем статус waiting_for_term
        await state.finish()

        # Получаем из таблицы "report" все информации об опоздании по id этого человека за выбранный срок:  [(id, user_id, date, comment, time), ...], где каждый элемент это отдельный день
        worker_report_list = sql_handler.get_data_by_term(chosen_worker[0], chosen_term)

        # Этот лист хранит блоки сообщения каждого опоздавшего дня (дата, опоздал на, причина)
        msg_late_days_list = []

        # В day хранится: (id, user_id, date, comment, time). Цикл заполняет лист msg_late_days_list
        for day in worker_report_list:
            # Определяем оставил ли он комментарию
            if day[3]:
                comment = day[3]
            else:
                comment = config['msg']['no_comment']

            # Если есть время значит он пришел с опозданием
            if day[4]:
                # Определим на сколько часов и минут он опоздал
                start_hour = int(config['time']['start_hour'])
                start_minute = int(config['time']['start_minute'])
                beginning_delta = datetime.timedelta(hours=start_hour, minutes=start_minute)
                came_time = day[4]

                came_time_delta = datetime.timedelta(hours=came_time.hour,minutes=came_time.minute,seconds=came_time.second)
                late_time_in_seconds = came_time_delta - beginning_delta
                late_time = (datetime.datetime.min + late_time_in_seconds).time()

                # Время прихода с опозданием
                came_time_str = came_time.strftime('%H:%M:%S')
                # На сколько времени он опоздал
                late_time_str = late_time.strftime('%H:%M:%S')

                # Составим сообщения об опоздании
                msg1 = f"{day[2]} {came_time_str}\n{config['msg']['late_by']} {late_time_str}\n"
            # Если нету время прихода, значит он вообще не пришел
            else:
                msg1 = f"{day[2]}\n{config['msg']['did_not_come']}\n"

            # Составим окончательный блок одного дня опоздания для сообщения
            msg2 = config['msg']['reason'] + comment
            msg_block = msg1 + msg2

            msg_late_days_list.append(msg_block)

        # Составим сообщение
        msg1 = config['msg']['you_chose'] + chosen_worker[1]

        # Если у выбранного пользователя нашлись опоздания
        if msg_late_days_list:
            msg2 = '\n\n'.join(msg_late_days_list)
        # Если ни разу не опоздал
        else:
            msg2 = config['msg']['no_latecomes']

        msg = msg1 + '\n\n' + msg2

        # Кнопка "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['main_menu']]])

        await message.answer(
            msg,
            reply_markup=button
        )

    # Если отправил неправильное число или текст
    else:
        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['main_menu']]])

        msg = config['msg']['wrong_term']
        await message.answer(msg, reply_markup=button)


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

    dp.register_message_handler(
        report_handler,
        lambda message: message.text == config['msg']['report']
    )

    dp.register_message_handler(
        choosen_worker_handler,
        state=MyStates.waiting_for_worker_number
    )

    dp.register_message_handler(
        chosen_term_handler,
        state=MyStates.waiting_for_term
    )

    dp.register_message_handler(
        main_menu,
        lambda message: message.text == config['msg']['main_menu']
    )

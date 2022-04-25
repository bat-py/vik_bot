import asyncio
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
    waiting_for_report_type = State()
    waiting_report_page_buttons = State()


async def admin_command_handler(message: types.Message, state: FSMContext):
    """
    Обработывает команду /admin
    :param state:
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

        await main_menu(message, state)

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

            # Отправим главное меню
            await main_menu(message, state)

        # Если не правильный тогда попросит еще раз ввести
        else:
            msg = config['msg']['wrong_password']
            await message.bot.send_message(
                message.chat.id,
                msg
            )


async def main_menu(message_or_callback_query, state: FSMContext):
    await state.finish()

    # Создаем кнопки
    buttons_name = [[config['msg']['report']], [config['msg']['missing']], [config['msg']['on_off']]]

    buttons = button_creators.reply_keyboard_creator(buttons_name)

    # Составим сообщение
    msg = config['msg']['main_menu']

    await message_or_callback_query.bot.send_message(
        message_or_callback_query.from_user.id,
        msg,
        reply_markup=buttons
    )


def on_off_menu_handler_buttons_creator(admin_status):
    """
    Функцию передаем лист: [0, 1, 1, 0]. Исходя из этого он создает нам кнопки
    :param admin_status:
    :return: Вернет созданные кнопки меню "Вкл/Выкл уведомление"
    """
    on = config['msg']['on']
    off = config['msg']['off']

    statues = []
    for i in admin_status:
        # Если "Уведомление об опоздавших" включен
        if i:
            statues.append(on)
        else:
            statues.append(off)

    but1_msg = f"{config['msg']['late_come_notification']} (Статус: {statues[0]})"
    but2_msg = f"{config['msg']['latecomer_came_notification']} (Статус: {statues[1]})"
    but3_msg = f"{config['msg']['comment_notification']} (Статус: {statues[2]})"
    but4_msg = f"{config['msg']['early_leave_notification']} (Статус: {statues[3]})"
    but5_msg = config['msg']['main_menu']

    # Создаем inline кнопки
    buttons = button_creators.inline_keyboard_creator([
        [[but1_msg, 'notification_button1']],
        [[but2_msg, 'notification_button2']],
        [[but3_msg, 'notification_button3']],
        [[but4_msg, 'notification_button4']],
        [[but5_msg, 'main_menu']]
    ]
    )

    return buttons


async def on_off_menu_handler(message: types.Message):
    check_admin = sql_handler.check_admin_exist(message.chat.id)

    # Если он зарегистрирован и есть в базе
    if check_admin:
        # Удаляем 2 последные сообщения
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        # В меню "Вкл/Выкл уведомление" будет 3 inline кнопки
        msg = config['msg']['on_off_menu']

        # Берем 4 статуса из таблицы admin и выходя из него создадим inline кнопки. Получит лист типа: (1, 0, 1, 0)
        admin_status = sql_handler.get_admin_notification_status(message.chat.id)

        # Функция on_off_menu_handler_buttons_creator создает нам кнопки
        buttons = on_off_menu_handler_buttons_creator(admin_status)

        await message.bot.send_message(
            message.chat.id,
            msg,
            reply_markup=buttons
        )


async def on_off_buttons_handler(callback_query: types.CallbackQuery):
    """
    Отвечает за кнопки(Уведом. об опоздавших, Уведом. о приходе опоздавших, Уведом. о рано ушедших) меню
    "Вкл/Выкл уведомление"
    :param callback_query:
    :return:
    """
    chosen_button = callback_query.data.replace('notification_button', '')

    # Получаем все 3 статуса: [0, 1, 1, 0]
    all_notification_status = list(sql_handler.get_admin_notification_status(callback_query.from_user.id))

    # Если нажал на 1-кнопку: Уведом. об опоздавших
    if chosen_button == '1':
        # Если статус включен тогда его выключим
        if all_notification_status[0] == 1:
            all_notification_status[0] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[0] = 1

    # Если нажал на 2-кнопку: Уведом. о приходе опоздавших
    elif chosen_button == '2':
        # Если статус включен тогда его выключим
        if all_notification_status[1] == 1:
            all_notification_status[1] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[1] = 1

    # Если нажал на 3-кнопку: Уведом. об оставленном комментарии(геолокация)
    elif chosen_button == '3':
        # Если статус включен тогда его выключим
        if all_notification_status[2] == 1:
            all_notification_status[2] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[2] = 1

    # Если нажал на 4-кнопку: Уведом. о рано ушедших
    elif chosen_button == '4':
        # Если статус включен тогда его выключим
        if all_notification_status[3] == 1:
            all_notification_status[3] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[3] = 1

    # Сохраним изменения в базе
    sql_handler.update_admin_notification_status(callback_query.from_user.id, all_notification_status)

    # Создаем новые inline кнопки
    new_inline_buttons = on_off_menu_handler_buttons_creator(all_notification_status)

    # Изменим inline кнопки, чтобы админ видел что
    await callback_query.message.edit_reply_markup(new_inline_buttons)


async def missing_list_handler(message: types.Message):
    """
    Запустится если пользователь нажал на "Список отсутствующих" и он вернет список тех кого сейчас нету
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

    latecommer_users_names_list = []
    for n, user in enumerate(latecommer_users):
        msg = f"{n + 1}. {user[1]}"
        latecommer_users_names_list.append(msg)

    lines = config['msg']['three_lines']
    msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
    # Если есть отсутствующие
    if latecommer_users_names_list:
        msg2 = config['msg']['missing_full']
        msg3 = '\n'.join(latecommer_users_names_list)
        msg = msg1 + '\n' + msg2 + '\n' + msg3
    # Если все на работе и отсутствующих нет
    else:
        msg = msg1 + '\n' + config['msg']['missing_full'] + '\n' + config['msg']['no_missing']

    # Удаляем сообщение "missing"
    try:
        await message.bot.delete_message(message.chat.id, message.message_id)
    except:
        pass

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
        users_dict[str(i + 1)] = users_list[i]
    # Сохраним users_dict в state, он потом нам понадобиться
    await state.update_data(users_dict=users_dict)

    msg1 = config['msg']['choose_worker']
    # Составим список всех рабочих чтобы отправить виде смс админу: ['1) Alisher Raximov', '', ...]
    nomer_name_list = [f'{nomer}. {data[1]}' for nomer, data in users_dict.items()]
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
        try:
            for i in range(3):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        await main_menu(message, state)

    # Если эта информация уже есть, значит админ вернулся назад со следующего меню
    elif data.get('chosen_worker') and message.text == config['msg']['back']:
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        chosen_worker = data['chosen_worker']
        # Меняем статус на waiting_for_term
        await MyStates.waiting_for_term.set()

        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])

        # Составим сообщения: "Вы выбрали: Name"
        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = config['msg']['term']
        msg = msg1 + '\n\n' + msg2

        await message.answer(
            msg,
            reply_markup=button
        )

    # Если админ первый раз в этом меню и  выбрал существующий номер, спросим сколько дней отчета надо показать
    elif message.text in workers_numbers_list:
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        chosen_worker_info = users_dict[message.text]
        # Сохраним выбранного работника в память (ID, name, Who, chat_id)
        await state.update_data(chosen_worker=chosen_worker_info)

        # Меняем статус на waiting_for_term
        await MyStates.waiting_for_term.set()

        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])

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
        # button = button_creators.reply_keyboard_creator([[[config['msg']['back'], config['msg']['main_menu']]])
        try:
            await message.bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        msg = config['msg']['wrong_number']
        await message.answer(msg)  # , reply_markup=button)


### Отправит 6 пунктов
async def chosen_term_handler(message_or_callback_query, state: FSMContext):
    """
    Запуститься после того как пользователь выбрал сколько дней отчета надо показать(1-31). Потом вернет 6 пунктов
    Или после того как пользователь вернулся из следующего меню (из какого-то выбранного пункта отчета)
    :param message_or_callback_query:
    :param state:
    :return:
    """
    all_data = await state.get_data()

    str_numbers = [str(i) for i in range(1, 31)]

    # Если пользователь попал сюда после выбора периода(ответил на: "Сколько дней хотите посмотреть (1-30 дней):")
    try:
        text = message_or_callback_query.text
    # Если вместо текста получил callback_data значит он вернулся из следуюшего меню(6 пунктов)
    except:
        text = None

    if text:
        # Если нажал на кнопку Главное меню
        if message_or_callback_query.text == config['msg']['main_menu']:
            # Удаляем 2 последние сообщения
            try:
                for i in range(3):
                    await message_or_callback_query.bot.delete_message(message_or_callback_query.chat.id,
                                                                       message_or_callback_query.message_id - i)
            except:
                pass

            await main_menu(message_or_callback_query, state)

        # Если отправил число от 1 до 30 или если вернулся назад из следующего меню (из какого-то пункта отчета)
        elif message_or_callback_query.text.strip() in str_numbers or \
                (message_or_callback_query.text == config['msg']['back'] and all_data.get('term')):
            # Если не найдено переменный term значит он вернулся из следующего меню.
            if not all_data.get('term'):
                # Так как term не найдено значит он тут первый раз, поэтому сохраним выбранный диапазон
                await state.update_data(term=message_or_callback_query.text.strip())

            # Меняем статус на waiting_for_report_type
            await MyStates.waiting_for_report_type.set()

            # Создаем 6 inline кнопок для выбора типа отчета и кнопки назад и главное меню
            buttons_list = [
                [[config['msg']['come_leave_report_type'], 'come_leave_report_type']],
                [[config['msg']['late_report_type'], 'late_report_type']],
                [[config['msg']['early_leaved_report_type'], 'early_leaved_report_type']],
                [[config['msg']['missed_days_report_type'], 'missed_days_report_type']],
                [[config['msg']['presence_time_report_type'], 'presence_time_report_type']],
                [[config['msg']['all_data_report_type'], 'all_data_report_type']],
                [[config['msg']['back'], 'back'], [config['msg']['main_menu'], 'main_menu']]
            ]
            inline_button = button_creators.inline_keyboard_creator(buttons_list, row_width=2)

            msg = config['msg']['choose_report_type']

            # Удаляем 2 последние сообщения
            try:
                for i in range(2):
                    await message_or_callback_query.bot.delete_message(
                        message_or_callback_query.chat.id,
                        message_or_callback_query.message_id - i
                    )
            except:
                pass

            # Отправим сообщение с 6 inline кнопками
            await message_or_callback_query.answer(msg, reply_markup=inline_button)

        # Если нажал на кнопку Назад вместо количество дней
        elif message_or_callback_query.text == config['msg']['back']:
            # На всякие случаи аннулируем значение term
            await state.update_data(term=None)

            # Удаляем 2 последние сообщения
            try:
                for i in range(2):
                    await message_or_callback_query.bot.delete_message(
                        message_or_callback_query.chat.id,
                        message_or_callback_query.message_id - i
                    )
            except:
                pass

            await MyStates.waiting_for_worker_number.set()
            await report_handler(message_or_callback_query, state=state)

        # Если отправил неправильное число или текст
        else:
            # Создадим кнопку "Главное меню"
            button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
            # Удаляем 2 последние сообщения
            try:
                for i in range(2):
                    await message_or_callback_query.bot.delete_message(message_or_callback_query.chat.id,
                                                                       message_or_callback_query.message_id - i)
            except:
                pass

            msg = config['msg']['wrong_term']
            await message_or_callback_query.answer(msg, reply_markup=button)
    # Если он вернулся со следующего меню(6 пунктов) используя inline кнопку назад
    else:
        # Удаляем 2 последние сообщения
        try:
            for i in range(2):
                await message_or_callback_query.bot.delete_message(
                    message_or_callback_query.message.chat.id,
                    message_or_callback_query.message.message_id - i
                )
        except:
            pass

        # Аннулируем значение term
        await state.update_data(term=None)

        data = await state.get_data()
        chosen_worker = data['chosen_worker']
        # Меняем статус на waiting_for_term
        await MyStates.waiting_for_term.set()

        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])

        # Составим сообщения: "Вы выбрали: Name"
        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = config['msg']['term']
        msg = msg1 + '\n\n' + msg2

        await message_or_callback_query.bot.send_message(
            message_or_callback_query.from_user.id,
            msg,
            reply_markup=button
        )


async def come_leave_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 1 пункт: Приход / Уход
    :param state:
    :param callback_query:
    :return:
    """

    # Удаляем 2 последние сообщения
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
    chosen_worker = all_data['chosen_worker']
    chosen_term = all_data['term']

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    for day in chosen_days:
        # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
        in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

        mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                config['msg']['three_lines'] + '</b>\n'

        # Если данное число(date) выходной, тогда напишем: "🗓 Выходные\n Время прихода | Время ухода или просто "🗓 Выходные\n Не пришел"
        if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
            mesg2 = config['msg']['weekend'] + '\n'
        else:
            mesg2 = ''

        # Если в in_out_time: False
        if not in_out_time:
            mesg3 = config['msg']['dont_came']
        # Если в in_out_time: (in_time, out_time)
        elif in_out_time[0] and in_out_time[1]:
            mesg3_1 = config['msg']['came'] + ' ' + in_out_time[0].strftime('%H:%M')
            mesg3_2 = config['msg']['leaved'] + ' ' + in_out_time[1].strftime('%H:%M')
            mesg3 = mesg3_1 + '  <b>|</b>  ' + mesg3_2
        # Если в in_out_time: (in_time, False)
        else:
            mesg3_1 = config['msg']['came'] + ' ' + in_out_time[0].strftime('%H:%M')
            mesg3_2 = config['msg']['leaved']
            mesg3 = mesg3_1 + '  <b>|</b>  ' + mesg3_2

        # Составим сообщение
        msg2 = mesg1 + mesg2 + mesg3

        # Добавим созданную часть сообщения в msg2_block_list
        msg2_block_list.append(msg2)

    msg1 = config['msg']['you_chose'] + chosen_worker[1]
    msg2 = '\n\n'.join(msg2_block_list)
    msg = msg1 + '\n\n' + msg2

    # Кнопка "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def late_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 2 пункт: Опоздание
    :param callback_query:
    :return:
    """
    # Удаляем 2 последние сообщения
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
    chosen_worker = all_data['chosen_worker']
    chosen_term = all_data['term']

    # Суммарное время опозданий
    total_late_hours = datetime.timedelta()

    # Получаем из таблицы "report" все информации об опоздании по id этого человека за выбранный срок:  [(id, user_id, date, comment, time), ...], где каждый элемент это отдельный день
    worker_report_list = sql_handler.get_data_by_term(chosen_worker[0], chosen_term)
    # Из worker_report_list создадим библиотеку: {date: (id, user_id, date, comment, time), ...}
    worker_report_dict = {}
    for day in worker_report_list:
        worker_report_dict[day[2]] = day

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    for day in chosen_days:
        if day in worker_report_dict:
            # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
            in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

            # Если он пришел с опозданием, составим об этом сообщение. worker_report_dict[day] хранит (id, user_id, date, comment, time)
            if worker_report_dict[day][4]:
                mesg1 = config['msg']['came'] + ' ' + str(worker_report_dict[day][4].strftime("%H:%M"))

                # Определим на сколько часов и минут он опоздал
                beginning_delta = datetime.timedelta(hours=int(config['time']['start_hour']),
                                                     minutes=int(config['time']['start_minute']))
                came_time = worker_report_dict[day][4]
                came_time_delta = datetime.timedelta(hours=came_time.hour, minutes=came_time.minute,
                                                     seconds=came_time.second)
                late_time_in_seconds = came_time_delta - beginning_delta
                late_time = (datetime.datetime.min + late_time_in_seconds).time()

                # Вместо "Опоздал на: 07:52" создаем "Опоздал на: 7 часов 52 минуты"
                hour = str(late_time.hour)
                minute = str(late_time.minute)
                if hour == '0':
                    time = f"{minute} мин."
                else:
                    time = f"{hour.lstrip('0')} час. {minute} мин."
                mesg3 = config['msg']['late_by'] + ' ' + time

                # Прибавим время опоздания в суммарную delta
                total_late_hours += late_time_in_seconds

                # Если пользователь оставил комментарии о своем опоздании
                if worker_report_dict[day][3]:
                    mesg4 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                else:
                    mesg4 = config['msg']['reason']

                # Если в in_out_time хранится: False
                if not in_out_time:
                    mesg2 = config['msg']['leaved']
                # Если в in_out_time хранится: (in_time, out_time)
                elif in_out_time[1]:
                    # Получит (msg, timedelta): "Ушел в: 19:20" или "Ушел в: 15:20\n Ушел раньше чем: 3:40" или "Ушел в: Нету данных"
                    # timedelta: чтобы определить суммарное время
                    out_check = early_leave_check(in_out_time[1])
                    # Если есть время ухода и раннего ухода
                    mesg2_5 = out_check[0]
                    if '#' in mesg2_5:
                        ms = mesg2_5.split('#')
                        mesg2 = ms[0]
                    else:
                        mesg2 = mesg2_5
                # Если в in_out_time хранится: (in_time, False)
                else:
                    mesg2 = config['msg']['leaved']

                msg2_1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                         config['msg']['three_lines'] + '</b>'
                # Хранит в себе "Приход: | Уход:\n Опоздал на:\n Причина:"
                msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + '\n' + mesg3 + '\n' + mesg4
                msg2 = msg2_1 + '\n' + msg2_2

                msg2_block_list.append(msg2)

    # Если хоть раз опоздал
    if msg2_block_list:
        # Из дельта переводим на обычный время опозданий
        total_late_time = datetime.datetime.min + total_late_hours
        if total_late_time.day == 1:
            hour = str(total_late_time.hour)
            minute = str(total_late_time.minute)
            if hour == '0':
                total_late = f"{minute} мин."
            else:
                total_late = f"{hour.lstrip('0')} час. {minute} мин."
        else:
            hours = str((total_late_time - 1)*24 + total_late_time.hour)
            minute = str(total_late_time.minute)
            total_late = f"{hours} час. {minute} мин."

        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg3 = config['msg']['total_late'] + ' ' + total_late
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3
    else:
        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = config['msg']['no_latecomes']
        msg = msg1 + '\n\n' + msg2

    # Кнопки "Назад" и "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def early_leaved_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 3 пункт: Ранний уход
    :param callback_query:
    :return:
    """
    # Удаляем 2 последние сообщения
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
    chosen_worker = all_data['chosen_worker']
    chosen_term = all_data['term']

    # Хранит суммарное время(раньше времени)
    total_early_lived_time = datetime.timedelta()

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    for day in chosen_days:
        # Если данное число(date) не выходной
        if str(datetime.date.isoweekday(day)) not in config['time']['day_off']:
            # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
            in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

            # Если в in_out_time хранится: (in_time, out_time)
            if in_out_time and in_out_time[1]:
                # Получит (msg, timedelta): "Ушел в: 19:20" или "Ушел в: 15:20" или "Уход: 17:00:00 # Ушел раньше времени: 0:15" или "Ушел в: Нету данных"
                # timedelta: чтобы определить суммарное время
                out_check = early_leave_check(in_out_time[1])

                # Если в out_check[0] есть # значит он ушел раньше времени
                mesg2_1 = out_check[0]
                if '#' in mesg2_1:
                    ms = mesg2_1.split('#')
                    mesg3 = ms[0]
                    mesg4 = ms[1]

                    # Получить: comment и geolocation: (comment, geolocatoin) или (comment, False) или False
                    report = sql_handler.get_user_early_leaved_report_by_user_id_and_date(chosen_worker[0], day)
                    # Если report не равно False и если он оставил хотябы комментарий:
                    if report and report[0]:
                        # Создаем строку "Причина:"
                        mesg5 = f"\n{config['msg']['reason']} {report[0]}"

                        # Если оставил геолокацию
                        if report[1]:
                            geolocation = report[1].split(',')
                            url = f"https://www.google.com/maps?q={geolocation(0)},{geolocation(1)}&ll={geolocation(0)},{geolocation(1)}&z=16"
                            mesg6 = f"\n{config['msg']['geolocation']} {url}"
                        else:
                            mesg6 = f"\n{config['msg']['didnt_send_geolocation']}"
                    # Если вообще не ответил
                    else:
                        mesg5 = f"\n{config['msg']['reason']} {config['msg']['didnt_send_comment']}"
                        mesg6 = ''

                    # Прибовляем время в суммарное время раннего ухода(если он ушел раньше. А если нет то timedelta = 0)
                    total_early_lived_time += out_check[1]

                    # Хранит: "--- 29.03.2022 ---"
                    mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                            config['msg']['three_lines'] + '</b>'
                    # Хранит "Приход: 15:12"
                    mesg2 = config['msg']['came'] + ' ' + str(in_out_time[0].strftime("%H:%M"))
                    msg2_2 = mesg1 + '\n' + mesg2 + '  <b>|</b>  ' + mesg3 + '\n' + mesg4 + mesg5 + mesg6

                    msg2_block_list.append(msg2_2)

    # Если хоть раз ушел раньше времени
    if msg2_block_list:
        # Из дельта переводим на обычный время раннего ухода
        total_early_time = datetime.datetime.min + total_early_lived_time
        if total_early_time.day == 1:
            hour = str(total_early_time.hour)
            minute = str(total_early_time.minute)
            if hour == '0':
                total_early = f"{minute} мин."
            else:
                total_early = f"{hour.lstrip('0')} час. {minute} мин."
        else:
            hours = str((total_early_time.day - 1)*24 + total_early_time.hour)
            minute = str(total_early_time.minute)
            total_early = f"{hours} час. {minute} мин."

        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg3 = config['msg']['total_early'] + ' ' + total_early
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3
    else:
        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = config['msg']['no_early_leaves']
        msg = msg1 + '\n\n' + msg2

    # Кнопки "Назад" и "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def missed_days_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 4 пункт: Пропущенные дни
    :param callback_query:
    :return:
    """
    # Удаляем 2 последние сообщения
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
    chosen_worker = all_data['chosen_worker']
    chosen_term = all_data['term']

    # Суммарное количества дней который не пришел
    missed_days = 0

    # Получаем из таблицы "report" все информации об опоздании по id этого человека за выбранный срок:  [(id, user_id, date, comment, time), ...], где каждый элемент это отдельный день
    worker_report_list = sql_handler.get_data_by_term(chosen_worker[0], chosen_term)
    # Из worker_report_list создадим библиотеку: {date: (id, user_id, date, comment, time), ...}
    worker_report_dict = {}
    for day in worker_report_list:
        worker_report_dict[day[2]] = day

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    for day in chosen_days:
        # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
        in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

        # Если в in_out_time хранится False значит в этот день он не пришел. Если день был выходным тогда день пропустим
        if not in_out_time and str(datetime.date.isoweekday(day)) not in config['time']['day_off']:
            missed_days += 1

            # Хранит: (id, user_id, date, comment, time)
            report = worker_report_dict.get(day)

            # Если report данного дня найден и пользователь оставил комментарию
            if report and report[3]:
                mesg3 = config['msg']['reason'] + report[3]
            # Если были проблемы с базой и report выбранного дня не найден или пользователь не оставил комментарию
            else:
                mesg3 = config['msg']['reason']

            # Хранит: "--- 29.03.2022 ---"
            mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                    config['msg']['three_lines'] + '</b>'
            mesg2 = config['msg']['did_not_come']

            # msg2 = mesg1 + '\n' + mesg2 + '\n' + mesg3
            msg2 = mesg1 + '\n' + mesg3
            msg2_block_list.append(msg2)

    # Если хоть раз не пришел
    if msg2_block_list:
        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg3 = config['msg']['total_missed'] + ' ' + str(missed_days)
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3
    else:
        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = config['msg']['no_missed_days']
        msg = msg1 + '\n\n' + msg2

    # Кнопки "Назад" и "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def presence_time_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 5 пункт: Время присутствия
    :param state:
    :param callback_query:
    :return:
    """
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
    chosen_worker = all_data['chosen_worker']
    chosen_term = all_data['term']

    # Хранит суммарное время присутствии
    total_presence_time = datetime.timedelta()

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    for day in chosen_days:
        # Получим все in/out указанного дня: [(datetime.time(9, 6, 47), 'DeviceNo'), ...] или если ничего не найдено: []
        all_in_outs_one_day = sql_handler.get_all_in_outs_one_day(chosen_worker[0], day)

        mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                config['msg']['three_lines'] + '</b>'

        # Если нет записей, значит он вообще не пришел
        if not all_in_outs_one_day:
            # Если это выходной день тогда напишем: "Выходные\n Не пришел"
            if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
                mesg2 = config['msg']['weekend'] + '\n' + config['msg']['dont_came']
            # Если не пришел в рабочий день
            else:
                mesg2 = config['msg']['did_not_come']

            # Добавим составленную часть сообщения в msg2_block_list
            msg2 = mesg1 + '\n' + mesg2
            msg2_block_list.append(msg2)
        else:
            in_device = config['device']['in_device']
            out_device = config['device']['out_device']

            in_time = 0
            # Тут храним время присутствия одного дня
            day_presence_time_delta = datetime.timedelta()
            mesg2 = str()
            # Если в all_in_outs_one_day есть 2 in и 2 out, значит составим 2 строки: "in | out\n in | out"
            for i in all_in_outs_one_day:
                # Если in_time пуст, значит мы ожидаем in_time.
                # !!! Но иногда после in может быть опять in если сотрудник при выходе не использовал faceid
                if not in_time:
                    # Если получили in_device когда in_time пуст, значит всё в порядке
                    if i[1] == in_device:
                        in_time = i[0]
                        # mesg2 += config['msg']['came'] + ' ' + i[0].strftime('%H:%M')
                    # Если in_time пуст но получили out_device, значит после уход опять получили уход. Приход между ними
                    # не было из-за того что рабочей не использовал faceid. В таком случае бот не будет рассчитывать это
                    # время и сотрудник потеряет время присутствии
                    else:
                        mesg2 += f"{config['msg']['came']}              |  {config['msg']['leaved']} {i[0].strftime('%H:%M')}\n"
                # Если in_time не пуст значит мы ожидаем out_time
                # !!! Но иногда после out может быть опять out если сотрудник при входе не использовал faceid
                else:
                    # Если получили out_device когда in_time не пуст, значит всё в порядке
                    if i[1] == out_device:
                        # Рассчитываем сколько часов был внутри и добавляем в суммарное время присутствии
                        in_time_delta = datetime.timedelta(hours=in_time.hour, minutes=in_time.minute,
                                                           seconds=in_time.second)
                        out_time_delta = datetime.timedelta(hours=i[0].hour, minutes=i[0].minute, seconds=i[0].second)
                        presence_time_delta = out_time_delta - in_time_delta
                        day_presence_time_delta += presence_time_delta

                        # Добавим строку "Приход: ... | Уход: ..."
                        mesg2 += f"{config['msg']['came']}  {in_time.strftime('%H:%M')}  |  {config['msg']['leaved']} {i[0].strftime('%H:%M')}\n"

                        # Онулируем in_time
                        in_time = 0
                    # Если получили in_device когда in_time не пуст, значит после прихода опять идет приход и уход между
                    # ними утерен из-за того что сотрудник не использовал faceid. В таком случаи мы не добавляем время в day_presence_time
                    else:
                        # Добавим строку: Приход: ... | Уход: "тут будет пусто"
                        mesg2 += f"{config['msg']['came']}  {in_time.strftime('%H:%M')}  |  {config['msg']['leaved']}\n"

                        # Запишем время в in_time чтобы в следующем цыкле не запустился "if not in_time"
                        in_time = i[0]

            # Из дельта переводим на обычный время опозданий
            day_presence_time = datetime.datetime.min + day_presence_time_delta

            # Вместо "Время присутствия: 07:52" создаем "Время присутствия: 7 часов 52 минуты"
            hour = str(day_presence_time.hour)
            minute = str(day_presence_time.minute)
            if hour == '0':
                time = f"{minute} мин."
            else:
                time = f"{hour.lstrip('0')} час. {minute} мин."
            mesg3 = config['msg']['presence_time'] + ' ' + time

            # Если это выходной день тогда напишем: "---date---\n Выходные\n Приход: | Уход: ..."
            if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
                # Соберем все части сообщения(Со строкой "🗓 Выходные") и добавим в msg2_block_list
                msg2 = mesg1 + '\n' + config['msg']['weekend'] + '\n' + mesg2 + mesg3
            else:
                # Время присутствия одного дня в общую время присутствия
                total_presence_time += day_presence_time_delta

                # Соберем все части сообщения и добавим в msg2_block_list
                msg2 = mesg1 + '\n' + mesg2 + mesg3

            msg2_block_list.append(msg2)

    # Из дельта переводим на обычный время присутствия
    presence_time = datetime.datetime.min + total_presence_time
    if presence_time.day == 1:
        hour = str(presence_time.hour)
        minute = str(presence_time.minute)
        if hour == '0':
            total_presence = f"{minute} мин."
        else:
            total_presence = f"{hour.lstrip('0')} час. {minute} мин."
    else:
        hours = str((presence_time.day - 1)*24 + presence_time.hour)
        minute = str(presence_time.minute)
        total_presence = f"{hours} час. {minute} мин."

    msg1 = config['msg']['you_chose'] + chosen_worker[1]
    msg2 = '\n\n'.join(msg2_block_list)
    # Создаем часть сообщения: "Итого время присутствия: 31:24"
    msg3 = config['msg']['total_presence_time'] + ' ' + total_presence

    msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3

    # Кнопки "Назад" и "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


def calc_presence_time(user_id, day):
    """
    Возвращает сколько часов(timedelta) рабочий был на работе в указанном дне в виде сообщения и timedelta чтобы
    :param user_id:
    :param day:
    :return: ("Время присутствия: 2 часа 23мин", datetime.timedelta(xxx))
    """
    # Получим все in/out указанного дня: [(datetime.time(9, 6, 47), 'DeviceNo'), ...] или если ничего не найдено: []
    all_in_outs_one_day = sql_handler.get_all_in_outs_one_day(user_id, day)

    # Хотя в all_in_outs_one_day всегда должен быть информация, но на всякие случаи страхуемся
    if all_in_outs_one_day:

        in_device = config['device']['in_device']
        out_device = config['device']['out_device']

        in_time = 0
        # Тут храним время присутствия одного дня
        day_presence_time_delta = datetime.timedelta()

        # Если в all_in_outs_one_day есть 2 in и 2 out, значит составим 2 строки: "in | out\n in | out"
        for i in all_in_outs_one_day:
            # Если in_time пуст, значит мы ожидаем in_time.
            # !!! Но иногда после in может быть опять in если сотрудник при выходе не использовал faceid
            if not in_time:
                # Если получили in_device когда in_time пуст, значит всё в порядке
                if i[1] == in_device:
                    in_time = i[0]
            # Если in_time не пуст значит мы ожидаем out_time
            # !!! Но иногда после out может быть опять out если сотрудник при входе не использовал faceid
            else:
                # Если получили out_device когда in_time не пуст, значит всё в порядке
                if i[1] == out_device:
                    # Рассчитываем сколько часов был внутри и добавляем в суммарное время присутствии
                    in_time_delta = datetime.timedelta(hours=in_time.hour, minutes=in_time.minute,
                                                       seconds=in_time.second)
                    out_time_delta = datetime.timedelta(hours=i[0].hour, minutes=i[0].minute, seconds=i[0].second)
                    presence_time_delta = out_time_delta - in_time_delta
                    day_presence_time_delta += presence_time_delta

                    # Онулируем in_time
                    in_time = 0
                # Если получили in_device когда in_time не пуст, значит после прихода опять идет приход и уход между
                # ними утерен из-за того что сотрудник не использовал faceid. В таком случаи мы не добавляем время в day_presence_time
                else:
                    # Запишем время в in_time чтобы в следующем цыкле не запустился "if not in_time"
                    in_time = i[0]

        # Из дельта переводим на обычный время опозданий
        day_presence_time = datetime.datetime.min + day_presence_time_delta

        # Вместо "Время присутствия: 07:52" создаем "Время присутствия: 7 часов 52 минуты"
        hour = str(day_presence_time.hour)
        minute = str(day_presence_time.minute)

        if day_presence_time.day == 1:
            if hour == '0':
                time = f"{minute} мин."
            else:
                time = f"{hour.lstrip('0')} час. {minute} мин."
        # Если время присутствия больше одного дня тогда будет: 52часа 5мин
        else:
            hours = str((day_presence_time.day - 1) * 24 + day_presence_time.hour)
            time = f"{hours} час. {minute} мин."

        # Составим сообщение: "Время присутствия: 2 час. 51 мин."
        mesg = config['msg']['presence_time'] + ' ' + time

        return mesg, day_presence_time_delta
    # Если вдруг что-то пошел ни так, тогда просто вернем пустую строку. Хотя так быть не должно
    else:
        return config['msg']['presence_time'], datetime.timedelta()


async def all_data_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запуститься если выбрал 6-пункт: Записи всех событий
    :param callback_query:
    :param state:
    :return:
    """
    if True:
        # Удаляем 2 последние сообщения
        try:
            for i in range(2):
                await callback_query.bot.delete_message(
                    callback_query.message.chat.id,
                    callback_query.message.message_id - i
                )
        except:
            pass

        # Установим новое состояние чтобы кнопка Назад после показа отчета работал
        await MyStates.waiting_report_page_buttons.set()

        all_data = await state.get_data()
        # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
        chosen_worker = all_data['chosen_worker']
        chosen_term = all_data['term']

        # Суммарное время опозданий
        total_late_hours = datetime.timedelta()
        # Хранит суммарное время(раньше времени)
        total_early_lived_time = datetime.timedelta()
        # Хранит суммарное время присутствии
        total_presence_time = datetime.timedelta()
        # Количество дней который не пришел
        missed_days = 0

        # Получаем из таблицы "report" все информации об опоздании по id этого человека за выбранный срок:  [(id, user_id, date, comment, time), ...], где каждый элемент это отдельный день
        worker_report_list = sql_handler.get_data_by_term(chosen_worker[0], chosen_term)
        # Из worker_report_list создадим библиотеку: {date: (id, user_id, date, comment, time), ...}
        worker_report_dict = {}
        for day in worker_report_list:
            worker_report_dict[day[2]] = day

        # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
        chosen_days = []
        for i in range(int(chosen_term)):
            day = datetime.datetime.now().date() - datetime.timedelta(days=i)
            chosen_days.append(day)
        chosen_days.reverse()

        msg2_block_list = []
        for day in chosen_days:
            # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
            in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

            # Получим ("Время присутствия: 2 часов 42 минуты", timedelta)
            presence_text_timedelta = calc_presence_time(chosen_worker[0], day)

            # Если данное число(date) выходной, тогда напишем: "🗓 Выходные\n Время прихода | Время ухода или просто "🗓 Выходные\n Не пришел"
            if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
                mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                        config['msg']['three_lines'] + '</b>'
                mesg2 = config['msg']['weekend']

                # Если в in_out_time: False
                if not in_out_time:
                    mesg3 = config['msg']['dont_came']
                    mesg4 = ''
                # Если в in_out_time: (in_time, out_time)
                elif in_out_time[0] and in_out_time[1]:
                    mesg3_1 = config['msg']['came'] + ' ' + in_out_time[0].strftime('%H:%M')
                    mesg3_2 = config['msg']['leaved'] + ' ' + in_out_time[1].strftime('%H:%M')
                    mesg3 = mesg3_1 + '  <b>|</b>  ' + mesg3_2

                    # Получим "Время присутствия: 2 часов 42 минуты". Но timedelta не добавим в total_presence_time так как сегодня выходной
                    mesg4 = '\n' + presence_text_timedelta[0]
                # Если в in_out_time: (in_time, False)
                else:
                    mesg3_1 = config['msg']['came'] + ' ' + in_out_time[0].strftime('%H:%M')
                    mesg3_2 = config['msg']['leaved']
                    mesg3 = mesg3_1 + '  <b>|</b>  ' + mesg3_2

                    # Получим "Время присутствия: 2 часов 42 минуты". Но timedelta не добавим в total_presence_time так как сегодня выходной
                    mesg4 = '\n' + presence_text_timedelta[0]

                # Составим сообщение
                msg2 = mesg1 + '\n' + mesg2 + '\n' + mesg3 + mesg4

                # Добавим созданную часть сообщения в msg2_block_list
                msg2_block_list.append(msg2)

                # Все что внизу пропустим
                continue

            # if day in worker_report_dict:
            # Так как in_out_time == False, значит он не пришел
            if not in_out_time:
                mesg1 = config['msg']['did_not_come']

                if worker_report_dict.get(day) and worker_report_dict[day][3]:
                    mesg2 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                else:
                    mesg2 = config['msg']['reason']

                msg2_2 = mesg1 + '\n' + mesg2
                missed_days += 1
            # Если он пришел с опозданием, составим об этом сообщение. worker_report_dict[day] хранит (id, user_id, date, comment, time)
            # Если в данный день существует в worker_report_dict и столбец time имеет какое-то значение значит он пришел с опозданием
            elif worker_report_dict.get(day) and worker_report_dict[day][4]:
                mesg1 = config['msg']['came'] + ' ' + str(worker_report_dict[day][4].strftime("%H:%M"))

                # Определим на сколько часов и минут он опоздал
                beginning_delta = datetime.timedelta(hours=int(config['time']['start_hour']),
                                                     minutes=int(config['time']['start_minute']))
                came_time = worker_report_dict[day][4]
                came_time_delta = datetime.timedelta(hours=came_time.hour, minutes=came_time.minute,
                                                     seconds=came_time.second)
                late_time_in_seconds = came_time_delta - beginning_delta
                late_time = (datetime.datetime.min + late_time_in_seconds).time()

                # Вместо "Опоздал на: 07:52" создаем "Опоздал на: 7 часов 52 минуты"
                hour = str(late_time.hour)
                minute = str(late_time.minute)
                if hour == '0':
                    time = f"{minute} мин."
                else:
                    time = f"{hour.lstrip('0')} час. {minute} мин."
                # Составим сообщение: "Опоздал на: 7 часов 52 минуты"
                mesg3 = config['msg']['late_by'] + ' ' + time

                # Прибавим время опоздания в суммарную delta
                total_late_hours += late_time_in_seconds

                #if worker_report_dict[day][3]:
                #    mesg4 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                #else:
                #    mesg4 = config['msg']['reason']
                mesg4 = ''

                # Получит (msg, timedelta): "Ушел в: 19:20" или "Ушел в: 15:20\n Ушел ра:ньше чем 3:40" или "Ушел в: Нету данных"
                # timedelta: чтобы определить суммарное время
                out_check = early_leave_check(in_out_time[1])
                # Если есть время ухода и раннего ухода
                mesg2_5 = out_check[0]
                if '#' in mesg2_5:
                    ms = mesg2_5.split('#')
                    mesg2 = ms[0]
                    mesg5 = f"\n{ms[1]}"
                else:
                    mesg2 = mesg2_5
                    mesg5 = ''
                # Прибовляем время в суммарное время раннего ухода(если он ушел раньше. А если нет то timedelta = 0)
                total_early_lived_time += out_check[1]

                # Прибавим время присутствия в общую дельту
                total_presence_time += presence_text_timedelta[1]
                # Получим "Время присутствия: 2 часов 42 минуты". Но timedelta не добавим в total_presence_time так как сегодня выходной
                mesg6 = presence_text_timedelta[0]

                # Хранит в себе "Приход: | Уход:\n Опоздал на:\n Причина:\n Время присутствия:"
                msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + '\n' + mesg3 + '\n' + mesg4 + mesg5 + '\n' + mesg6
            # Если in_out_time не False и в таблице report не найден данный день, значит он пришел во время
            else:
                mesg1 = config['msg']['came'] + ' ' + in_out_time[0].strftime("%H:%M")

                # Получит (msg, timedelta): "Ушел в: 19:20" или "Ушел в: 15:20\n Ушел раньше чем: 3:40" или "Ушел в: Нету данных"
                # timedelta: чтобы определить суммарное время
                out_check = early_leave_check(in_out_time[1])
                # Если есть время ухода и раннего ухода
                mesg2_5 = out_check[0]
                if '#' in mesg2_5:
                    ms = mesg2_5.split('#')
                    mesg2 = ms[0]
                    mesg3 = f"\n{ms[1]}"
                else:
                    mesg2 = mesg2_5
                    mesg3 = ''

                # Прибовляем время в суммарное время раннего ухода(если он ушел раньше. А если нет то timedelta = 0)
                total_early_lived_time += out_check[1]

                # Прибавим время присутствия в общую дельту
                total_presence_time += presence_text_timedelta[1]
                # Получим "Время присутствия: 2 часов 42 минуты". Но timedelta не добавим в total_presence_time так как сегодня выходной
                mesg4 = presence_text_timedelta[0]

                # Хранит в себе "Приход:\n Ушел в: "
                msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + mesg3 + '\n' + mesg4

            msg2_1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                     config['msg']['three_lines'] + '</b>'
            msg2 = msg2_1 + '\n' + msg2_2

            # Добавим созданную часть сообщения в msg2_block_list
            msg2_block_list.append(msg2)

        # Из дельта переводим на обычный время опозданий
        total_late_time = datetime.datetime.min + total_late_hours
        if total_late_time.day == 1:
            hour = str(total_late_time.hour)
            minute = str(total_late_time.minute)
            if hour == '0':
                total_late = f"{minute} мин."
            else:
                total_late = f"{hour.lstrip('0')} час. {minute} мин."
        else:
            day = int(total_late_time.strftime('%d')) - 1
            hour = str(total_late_time.hour)
            minute = str(total_late_time.minute)
            if hour == '0':
                total_late = f"{str(day)} дней {minute} мин."
            else:
                total_late = f"{str(day)} дней {hour.lstrip('0')} час. {minute} мин."

            total_late = total_late.lstrip('0')

        # Из дельта переводим на обычный время раннего ухода
        total_early_time = datetime.datetime.min + total_early_lived_time
        if total_early_time.day == 1:
            hour = str(total_early_time.hour)
            minute = str(total_early_time.minute)
            if hour == '0':
                total_early = f"{minute} мин."
            else:
                total_early = f"{hour.lstrip('0')} час. {minute} мин."
        else:
            day = int(total_early_time.strftime('%d')) - 1
            hour = str(total_early_time.hour)
            minute = str(total_early_time.minute)
            if hour == '0':
                total_early = f"{str(day)} дней {minute} мин."
            else:
                total_early = f"{str(day)} дней {hour.lstrip('0')} час. {minute} мин."

            total_early = total_early.lstrip('0')

        # Из дельта переводим на обычный время присутствия
        presence_time = datetime.datetime.min + total_presence_time
        if presence_time.day == 1:
            hour = str(presence_time.hour)
            minute = str(presence_time.minute)
            if hour == '0':
                total_presence = f"{minute} мин."
            else:
                total_presence = f"{hour.lstrip('0')} час. {minute} мин."
        else:
            day = int(presence_time.strftime('%d')) - 1
            hour = str(presence_time.hour)
            minute = str(presence_time.minute)
            if hour == '0':
                total_presence = f"{str(day)} дней {minute} мин."
            else:
                total_presence = f"{str(day)} дней {hour.lstrip('0')} час. {minute} мин."

            total_presence = total_presence.lstrip('0')

        msg3_1 = config['msg']['total_late'] + ' ' + total_late
        msg3_2 = config['msg']['total_early'] + ' ' + total_early
        msg3_3 = config['msg']['total_missed'] + ' ' + str(missed_days)
        msg3_4 = config['msg']['total_presence_time'] + ' ' + total_presence

        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg3 = msg3_1 + '\n' + msg3_2 + '\n' + msg3_3
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3 + '\n' + msg3_4

        # Кнопка "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
        await callback_query.bot.send_message(
            callback_query.from_user.id,
            msg,
            reply_markup=button
        )


async def main_menu_inline_button_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если нажал на inline кнопку Главное меню
    :param state:
    :param callback_query:
    :return:
    """
    # Удаляем 2 последние сообщения
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Вернем главное меню
    await main_menu(callback_query, state)


async def report_page_buttons(message: types.Message, state: FSMContext):
    """
    Эта функция нужна чтобы того как показал отчет за выбранный период мог работать кнопка Назад
    :param message:
    :param state:
    :return:
    """
    # Если нажал на кнопку Назад то вернем меню выбора типа отчета(6 пунктов из inline кнопок)
    if message.text == config['msg']['back']:
        await chosen_term_handler(message, state)
    # Если нажал на главное меню, то удалим последные 2 сообщения и вернем главное меню
    elif message.text == config['msg']['main_menu']:
        # Удаляем 2 последние сообщения
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        await main_menu(message, state)


def early_leave_check(time):
    """
    :param time:
    :return: Просто передаем ему время, а он исходя из end_hour и end_minute определит не ушел ли он раньше времени
    Если ушел после окончания дня тогда вернет "Уход: 19:01", а если ушел раньше тогда: "Уход: 17:00:00 # Ушел раньше времени: 0:15"
    Еще вернет early_seconds (в виде timedelta) чтобы находить суммарное время
    Второй элемент(early_time_delta) который он вернет это timedelta, чтобы находить суммарное время раннего ухода
    """
    early_time_delta = datetime.timedelta(0)

    # Иногда бывает что IN есть а OUT не было. В такое время он вернет "Нету данных"
    if not time:
        return config['msg']['leaved'], early_time_delta

    # Определим на сколько часов и минут он ушел раньше
    end_time_delta = datetime.timedelta(
        hours=int(config['time']['end_hour']),
        minutes=int(config['time']['end_minute'])
    )
    leaved_time_delta = datetime.timedelta(
        hours=time.hour,
        minutes=time.minute,
        seconds=time.second
    )

    # Если ушел раньше:
    if end_time_delta > leaved_time_delta:
        early_seconds = end_time_delta - leaved_time_delta
        early_time_hour = (datetime.datetime.min + early_seconds).time()

        # Вместо "Ранний уход: 07:52" создаем "Ранний уход: 7 часов 52 минуты"
        hour = str(early_time_hour.hour)
        minute = str(early_time_hour.minute)
        if hour == '0':
            early_leave_time = f"{minute} мин."
        else:
            early_leave_time = f"{hour.lstrip('0')} час. {minute} мин."

        msg1 = config['msg']['leaved'] + ' ' + time.strftime("%H:%M")
        msg2 = config['msg']['early_leaved'] + ' ' + early_leave_time
        msg = msg1 + '#' + msg2

        early_time_delta = early_seconds

    else:
        msg = config['msg']['leaved'] + ' ' + time.strftime("%H:%M")

    return msg, early_time_delta


def register_handlers(dp: Dispatcher):
    # Нужен только для того чтобы работал кнопка "Назад" после того как показал отчет за выбранный период
    dp.register_message_handler(
        report_page_buttons,
        content_types=['text'],
        state=MyStates.waiting_report_page_buttons
    )

    dp.register_message_handler(
        admin_command_handler,
        commands=['admin'],
        state='*'
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

    dp.register_callback_query_handler(
        on_off_buttons_handler,
        lambda c: c.data.startswith('notification_button')
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

    # Если выбрал 1 пункт
    dp.register_callback_query_handler(
        come_leave_report_type_handler,
        lambda c: c.data == 'come_leave_report_type',
        state=MyStates.waiting_for_report_type
    )

    # Если выбрал 2 пункт
    dp.register_callback_query_handler(
        late_report_type_handler,
        lambda c: c.data == 'late_report_type',
        state=MyStates.waiting_for_report_type
    )

    # Если выбрал 3 пункт
    dp.register_callback_query_handler(
        early_leaved_report_type_handler,
        lambda c: c.data == 'early_leaved_report_type',
        state=MyStates.waiting_for_report_type
    )

    # Если выбрал 4 пункт
    dp.register_callback_query_handler(
        missed_days_report_type_handler,
        lambda c: c.data == 'missed_days_report_type',
        state=MyStates.waiting_for_report_type
    )

    # Если выбрал 5 пункт
    dp.register_callback_query_handler(
        presence_time_report_type_handler,
        lambda c: c.data == 'presence_time_report_type',
        state=MyStates.waiting_for_report_type
    )

    # Если выбрал 6 пункт
    dp.register_callback_query_handler(
        all_data_report_type_handler,
        lambda c: c.data == 'all_data_report_type',
        state=MyStates.waiting_for_report_type
    )

    dp.register_callback_query_handler(
        chosen_term_handler,
        lambda c: c.data == 'back',
        state=MyStates.waiting_for_report_type
    )

    dp.register_message_handler(
        main_menu,
        lambda message: message.text == config['msg']['main_menu'],
        state='*'
    )

    dp.register_callback_query_handler(
        main_menu_inline_button_handler,
        lambda c: c.data == 'main_menu',
        state='*'
    )

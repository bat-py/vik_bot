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

        # Удаляем "Вкл/Выкл уведомление"(on_off
        try:
            await message.bot.delete_message(message.chat.id, message.message_id)
        except:
            pass

        await message.bot.send_message(
            message.chat.id,
            msg
        )


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

    # Если есть отсутствующие
    if latecommer_users_names_list:
        msg1 = config['msg']['missing_full']
        msg2 = '\n'.join(latecommer_users_names_list)
        msg = msg1 + '\n' + msg2
    # Если все на работе и отсутствующих нет
    else:
        msg = config['msg']['missing_full'] + '\n' + config['msg']['no_missing']

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
                late_time_str = late_time.strftime("%H:%M")
                mesg3 = config['msg']['late_by'] + ' ' + late_time_str

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
                msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + '\n' + mesg3 + mesg4
                msg2 = msg2_1 + '\n' + msg2_2

                msg2_block_list.append(msg2)

    # Если хоть раз опоздал
    if msg2_block_list:
        # Из дельта переводим на обычный время опозданий
        total_late_time = datetime.datetime.min + total_late_hours
        if total_late_time.day == 1:
            total_late = total_late_time.strftime('%H:%M')
        else:
            total_late = total_late_time.strftime('%d дней %H:%M')

        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + total_late
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

                    # Прибовляем время в суммарное время раннего ухода(если он ушел раньше. А если нет то timedelta = 0)
                    total_early_lived_time += out_check[1]

                    # Хранит: "--- 29.03.2022 ---"
                    mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                            config['msg']['three_lines'] + '</b>'
                    # Хранит "Приход: 15:12"
                    mesg2 = config['msg']['came'] + ' ' + str(in_out_time[0].strftime("%H:%M"))
                    msg2_2 = mesg1 + '\n' + mesg2 + '  <b>|</b>  ' + mesg3 + '\n' + mesg4

                    msg2_block_list.append(msg2_2)

    # Если хоть раз ушел раньше времени
    if msg2_block_list:
        # Из дельта переводим на обычный время раннего ухода
        total_early_time = datetime.datetime.min + total_early_lived_time
        if total_early_time.day == 1:
            total_early = total_early_time.strftime('%H:%M')
        else:
            total_early = total_early_time.strftime('%d дней %H:%M')

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
    print('4')




async def presence_time_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 5 пункт: Время присутствия
    :param state:
    :param callback_query:
    :return:
    """


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
            # Если при процессе сбора данных одного дня выйдет ошибка, тогда в это число напишем что пустые строки: "Приход: | Уход: "
            if True:
                # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
                in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

                # Если данное число(date) выходной, тогда напишем: "🗓 Выходные\n Время прихода | Время ухода или просто "🗓 Выходные\n Не пришел"
                if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
                    mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                            config['msg']['three_lines'] + '</b>'
                    mesg2 = config['msg']['weekend']

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
                    msg2 = mesg1 + '\n' + mesg2 + '\n' + mesg3

                    # Добавим созданную часть сообщения в msg2_block_list
                    msg2_block_list.append(msg2)

                    # Все что внизу пропустим
                    continue

                if day in worker_report_dict:
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
                        late_time_str = late_time.strftime("%H:%M")
                        mesg3 = config['msg']['late_by'] + ' ' + late_time_str

                        # Прибавим время опоздания в суммарную delta
                        total_late_hours += late_time_in_seconds

                        if worker_report_dict[day][3]:
                            mesg4 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                        else:
                            mesg4 = config['msg']['reason']

                        if in_out_time:
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
                        else:
                            mesg2 = config['msg']['leaved']
                            mesg5 = ''
                            total_early_lived_time += datetime.timedelta(0)

                        # Хранит в себе "Приход:\n Опоздал на:\n Причина:\n Ушел в:"
                        msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + '\n' + mesg3 + '\n' + mesg4 + mesg5
                    # Так как столбец time пуст, значит он не пришел
                    else:
                        mesg1 = config['msg']['did_not_come']

                        if worker_report_dict[day][3]:
                            mesg2 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                        else:
                            mesg2 = config['msg']['reason']

                        msg2_2 = mesg1 + '\n' + mesg2
                        missed_days += 1
                # Если в таблице report не найден данный день, значит он пришел во время
                else:
                    if in_out_time:
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
                    else:
                        mesg1 = config['msg']['came']

                        mesg2 = config['msg']['leaved']
                        mesg3 = ''
                        total_early_lived_time += datetime.timedelta(0)

                    # Хранит в себе "Приход:\n Ушел в: "
                    msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + mesg3

                msg2_1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                         config['msg']['three_lines'] + '</b>'
                msg2 = msg2_1 + '\n' + msg2_2

                # Добавим созданную часть сообщения в msg2_block_list
                msg2_block_list.append(msg2)

        # Из дельта переводим на обычный время опозданий
        total_late_time = datetime.datetime.min + total_late_hours

        if total_late_time.day == 1:
            total_late = total_late_time.strftime('%H:%M')
        else:
            total_late = total_late_time.strftime('%d дней %H:%M')
        # Из дельта переводим на обычный время раннего ухода
        total_early_time = datetime.datetime.min + total_early_lived_time
        if total_early_time.day == 1:
            total_early = total_early_time.strftime('%H:%M')
        else:
            total_early = total_early_time.strftime('%d дней %H:%M')

        msg3_1 = config['msg']['total_late'] + ' ' + total_late
        msg3_2 = config['msg']['total_early'] + ' ' + total_early
        msg3_3 = config['msg']['total_missed'] + ' ' + str(missed_days)

        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg3 = msg3_1 + '\n' + msg3_2 + '\n' + msg3_3
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3

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
        early_time = early_time_hour.strftime("%H:%M")

        msg1 = config['msg']['leaved'] + ' ' + time.strftime("%H:%M")
        msg2 = config['msg']['early_leaved'] + ' ' + early_time
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
        main_menu,
        lambda message: message.text == config['msg']['main_menu'],
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

    dp.register_callback_query_handler(
        main_menu_inline_button_handler,
        lambda c: c.data == 'main_menu',
        state='*'
    )

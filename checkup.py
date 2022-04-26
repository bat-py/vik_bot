from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import button_creators
import sql_handler
import configparser
import datetime

from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="vik_bot")

scheduler = AsyncIOScheduler()

config = configparser.ConfigParser()
config.read('config.ini')


class MyStates(StatesGroup):
    waiting_for_late_comment = State()
    #waiting_for_late_location = State()
    waiting_for_early_leave_comment = State()
    #waiting_for_early_leave_location = State()


async def check_users_in_logs(dp: Dispatcher):
    # today = datetime.datetime.today()
    # Получит число от 1-7. Если 1 значит сегодня понидельник, а если 7 значит воскресенье
    # day_of_week = datetime.datetime.isoweekday(today)
    # Если сегодня выходной то скрипт остановиться
    # if str(day_of_week) in config['time']['day_off']:
    #    return

    # Получаем ID тех кто пришел в 9:05 каждый день
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
    latecommer_users_names = list(map(lambda user: user[1], latecommer_users))

    today = datetime.datetime.today()
    # Получит число от 1-7. Если 1 значит сегодня понидельник, а если 7 значит воскресенье
    day_of_week = datetime.datetime.isoweekday(today)

    # Если сегодня не выходной. Админам отправит сообщение "Список опоздавших" а рабочим "Вы опоздали" с inline кнопкой
    if str(day_of_week) not in config['time']['day_off']:
        # Составляет сообщение чтобы отправить админам
        lines = config['msg']['three_lines']
        msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
        msg2 = config['msg']['list_of_latecomers']
        # Если есть опоздавшие
        if latecommer_users_names:
            latecommer_users_names_with_numbers = []
            for i in range(len(latecommer_users_names)):
                user = f"{str(i + 1)}. {latecommer_users_names[i]}"
                latecommer_users_names_with_numbers.append(user)
            msg3 = '\n'.join(latecommer_users_names_with_numbers)
        else:
            msg3 = config['msg']['no_latecomers']
        msg = msg1 + '\n' + msg2 + '\n' + msg3

        # Получаем список [(chat_id, first_name), ...] админов где столбец late_come_notification = 1 чтобы отправить список опоздавших
        admins_list = sql_handler.get_admins_where_notification_on('late_come_notification')

        # Отправляет сообщения всем админам
        for i in admins_list:
            try:
                await dp.bot.send_message(
                    i[0],
                    msg
                )
            except Exception as e:
                with open('journal.txt', 'a') as w:
                    w.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M  ') + \
                            'checkup.check_users_in_logs_1-try(admins_list):\n' + str(e) + '\n\n')

        # Каждому опоздавщему отправим сообщение чтобы он ответил почему опаздывает
        for user in latecommer_users:
            # Так как он будет отправлять каждому опоздавшему сообщения, но если кто-то заблокировал бот, он его пропустит
            try:
                await send_notification_to_latecomer(dp, user)
            except Exception as e:
                with open('journal.txt', 'a') as w:
                    w.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M  ') + \
                            'checkup.check_users_in_logs_2-try(latecommer_users):\n' + str(e) + '\n\n')

    # Если сегодня выходной то рабочим не отправит сообщение что они опоздали
    else:
        # Составляет сообщение чтобы отправить админам
        lines = config['msg']['three_lines']
        msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
        msg2 = config['msg']['list_those_who_came']

        # Получаем ID тех кто пришел в 9:05 каждый день
        ids_who_came = sql_handler.get_todays_logins()
        ids_who_came = [int(i[0]) for i in ids_who_came]

        # Если хоть кто-то пришел
        if ids_who_came:
            # Получаем информацию о тех кто пришел: [(ID, Name, chat_id), ...]
            users = sql_handler.get_users_name_chat_id(ids_who_came)
            users_names = list(map(lambda user: user[1], users))

            users_names_with_numbers = []
            for i in range(len(users_names)):
                user = f"{str(i + 1)}. {users_names[i]}"
                users_names_with_numbers.append(user)
            msg3 = '\n'.join(users_names_with_numbers)
        else:
            msg3 = config['msg']['nobody_came']
        msg = msg1 + '\n' + msg2 + '\n' + msg3

        # Получаем список [(chat_id, first_name), ...] админов где столбец late_come_notification = 1
        admins_list = sql_handler.get_admins_where_notification_on('late_come_notification')
        # Отправляет сообщения всем админам
        for i in admins_list:
            try:
                await dp.bot.send_message(
                    i[0],
                    msg
                )
            except Exception as e:
                with open('journal.txt', 'a') as w:
                    w.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M  ') + \
                            'checkup.check_users_in_logs_3-try(admins_list):\n' + str(e) + '\n\n')


async def send_notification_to_latecomer(dp: Dispatcher, latecomer_info):
    """
    Сперва создает строку в таблице "report": ID(8 значное код), user_id(ID того кто опоздал), date(сегодняшнее число),
    а столбец comment останется пустым.
    Отправит сообщения всем опоздавшим сообщения что они опоздали с inline кнопкой "Оставить комментарии",
    callback_data кнопки будет хранить "report.ID"
    latecomer_info хранит в себе (ID, Name, chat_id)  # ID это latecomer_id
    :param latecomer_info:
    :param dp:
    :return:
    """
    # report_creator создает запись в таблице report(id, user_id, date) и возвращает генерированный код(id)
    report_id = sql_handler.report_creator(latecomer_info[0])

    # Создадим inline кнопку "Оставить комментарии"
    leave_comment_button = button_creators.inline_keyboard_creator(
        [[[config['msg']['leave_comment'], f'late_missing_comment{report_id}']]])

    # Составим сообщение
    msg1 = f"{config['msg']['date']} {datetime.date.today().strftime('%d.%m.%Y')}"
    msg2 = f"<b>{latecomer_info[1]}</b> {config['msg']['you_late']}"
    msg = msg1 + '\n' + msg2

    # Отправим сообщения с inline кнопкой "Оставить комментарии" опоздавшему
    await dp.bot.send_message(
        latecomer_info[2],
        msg,
        reply_markup=leave_comment_button
    )


async def check_last_2min_logs(dp: Dispatcher):
    start_hour = int(config['time']['start_hour'])
    start_minute = int(config['time']['start_minute'])
    end_hour = int(config['time']['end_hour'])
    end_minute = int(config['time']['end_minute'])

    activate_time = datetime.time(start_hour, start_minute + 1, 0)
    end_time = datetime.time(end_hour, end_minute, 0)

    # Если время в промежутке 9:05 - 19:00
    now = datetime.datetime.now().time()
    today = datetime.datetime.today()
    # Получит число от 1-7. Если 1 значит сегодня понидельник, а если 7 значит воскресенье
    day_of_week = datetime.datetime.isoweekday(today)

    # if activate_time <= now < end_time and str(day_of_week) not in config['time']['day_off']:
    if activate_time <= now < end_time:
        # Получим список ID в виде МНОЖЕСТВО: "{'00000011', '00000026', ...}" тех кто зашел или ушел за последние 2мин
        last_1min_logs = sql_handler.get_last_1min_logins()

        # Если за последние 2 минуты кто-то пришел или ушел
        if last_1min_logs:
            for user in last_1min_logs:
                # Проверим опоздавшего на control/uncontrol
                control = sql_handler.check_control(int(user[0]))
                # Если опоздавший имеет статус Control, тогда админам отправим что он пришел только что пришел
                if control:
                    # Чтобы узнать первый раз ли он зашел получим количество логов рабочего за сегодня
                    all_logs_count = sql_handler.get_user_today_logs_count(user[0])

                    # Если это его первый раз за сегодня значит он только что пришел. Отправим админам что он пришел
                    if all_logs_count == 1:
                        admins = sql_handler.get_admins_where_notification_on('latecomer_came_notification')
                        admins_chat_id_list = list(map(lambda i: i[0], admins))

                        # Получаем информацию об опоздавшем (ID, name, Who, chat_id)
                        user_info = sql_handler.get_user_info_by_id(int(user[0]))

                        # Определим на сколько часов и минут он опоздал
                        start_hour = int(config['time']['start_hour'])
                        start_minute = int(config['time']['start_minute'])
                        beginning_delta = datetime.timedelta(hours=start_hour, minutes=start_minute)

                        now_time = datetime.time(user[1].hour, user[1].minute, user[1].second)
                        now_delta = datetime.timedelta(hours=user[1].hour, minutes=user[1].minute,
                                                       seconds=user[1].second)
                        late_second = now_delta - beginning_delta
                        late_time_hour = (datetime.datetime.min + late_second).time()

                        hour = str(late_time_hour.hour)
                        minute = str(late_time_hour.minute)
                        if hour == '0':
                            late_time = f"{minute} мин."
                        else:
                            late_time = f"{hour.lstrip('0')} час. {minute} мин."

                        # Запишем в таблицу "report" время прихода опоздавшего если сегодня не выходной
                        if str(day_of_week) not in config['time']['day_off']:
                            sql_handler.late_time_writer(user_info[0], now_time)

                        # Составим сообщения чтобы отправить админам
                        msg1 = f'<b>{user_info[1]}</b> '
                        msg2 = config['msg']['latecomer_came']
                        msg3 = f"{config['msg']['arrival_time']} {now_time.strftime('%H:%M')}"
                        msg4 = f"<b>{config['msg']['late_by']}</b> {late_time}"
                        msg = msg1 + msg2 + '\n\n' + msg3 + '\n\n' + msg4

                        for admin_id in admins_chat_id_list:
                            try:
                                await dp.bot.send_message(
                                    admin_id,
                                    msg
                                )
                            except Exception as e:
                                with open('journal.txt', 'a') as w:
                                    w.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M  ') + \
                                            'checkup.check_last_2min_logs:\n' + str(e) + '\n\n')
                                print('checkup.check_last_2min_logs:  ', str(e))


async def leave_late_comment_inline_button_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запуститься после того как пользователь нажал на inline кнопку "Оставить комментарии" (опоздание, отсутствие)
    :param state:
    :param callback_query:
    :return:
    """
    report_id = callback_query.data.replace('late_missing_comment', '')

    # Удаляем inline кнопку
    await callback_query.bot.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )

    # Сохраним report_id
    await state.update_data(report_id=report_id)

    # Установим статус
    await MyStates.waiting_for_late_comment.set()

    # Отправим сообщения "Можете оставить комментарии"
    msg = config['msg']['you_can_leave_comment']

    # Создадим кнопку "Отменить"
    button = button_creators.reply_keyboard_creator([[config['msg']['cancel']]], one_time=True)

    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def leaved_late_comment_handler(message: types.Message, state: FSMContext):
    """
    Запустится после того как опоздавший(отсутствующий) отправил причину используя inline кнопку
    :param message:
    :param state:
    :return:
    """
    # Если он нажал на кнопку "Отменить"
    if message.text == config['msg']['cancel']:
        await state.finish()
        msg = config['msg']['leave_comment_cancaled']

        await message.answer(msg)
    else:
        comment = message.text
        all_data = await state.get_data()
        report_id = all_data['report_id']
        await state.update_data(comment=comment)

        # Поменяем статус и ждем пока опоздавший не отправит геолокацию
        #await MyStates.waiting_for_late_location.set()
        await state.finish()

        # Запишем комментарию в таблицу report
        sql_handler.comment_writer(report_id, comment)

        # Сообщим пользователю что комментария сохранена и попросим от него отправить геолокацию
        #geolocation_button = button_creators.geolocation_button(config['msg']['geolocation_button_text'])
        #msg1 = config['msg']['comment_saved']
        #msg2 = config['msg']['send_geolocation']
        #msg = f"{msg1}. {msg2}"
        #await message.answer(msg, reply_markup=geolocation_button)
        msg = config['msg']['comment_saved']
        button_remove = button_creators.hide_reply_buttons()
        await message.answer(msg, reply_markup=button_remove)

        # Составим сообщения чтобы отправить админам
        # Получит (user_id, date, time) из таблицы "report"
        latecomer_info = sql_handler.get_user_id_data_time_from_report(report_id)
        user_name = sql_handler.get_user_name(latecomer_info[0])

        lines = config['msg']['three_lines']
        msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
        msg2 = f"<b>{user_name}</b> {config['msg']['latecomer_leaved_comment']}"
        msg3 = f"<b>{config['msg']['date']}</b> {latecomer_info[1].strftime('%d.%m.%Y')}"
        msg4 = f"{config['msg']['reason']} {comment}"
        msg = msg1 + '\n' + msg2 + '\n' + msg3 + '\n' + msg4

        # Получаем список [(chat_id, first_name, notification), ...] админов где столбец comment_notification = 1
        admins_list = sql_handler.get_admins_where_notification_on('comment_notification')

        # Отправим админам у кого comment_notification == 1
        for admin in admins_list:
            # Отправим составленное сообщение
            await message.bot.send_message(
                admin[0],
                msg
            )


# Not working for now
async def leaved_late_location_handler(message: types.Message, state: FSMContext):
    """
    Запустится после того как опоздавший отправил геолокацию
    :param message:
    :param state:
    :return:
    """
    all_data = await state.get_data()
    report_id = all_data['report_id']
    comment = all_data['comment']

    # Отключаем state
    await state.finish()

    latitude = message.location.latitude
    longitude = message.location.longitude
    location = str(latitude) + ',' + str(longitude)
    # Запишем геолокацию в таблицу report
    sql_handler.late_missed_location_writer(report_id, location)

    # Отправим опоздавшему сообщение что геолокация успешно сохранено
    msg = config['msg']['thanks_for_comment']
    await message.answer(msg)


    # Составим сообщения чтобы отправить админам
    # Получит (user_id, date, time) из таблицы "report"
    latecomer_info = sql_handler.get_user_id_data_time_from_report(report_id)
    user_name = sql_handler.get_user_name(latecomer_info[0])

    lines = config['msg']['three_lines']
    msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
    msg2 = f"<b>{user_name}</b> {config['msg']['latecomer_leaved_comment']}"
    msg3 = f"<b>{config['msg']['date']}</b> {latecomer_info[1].strftime('%d.%m.%Y')}"
    msg4 = f"{config['msg']['reason']} {comment}"
    try:
        # С помощью модуля geopy используя координати определяем адрес
        location_text = geolocator.reverse(f"{latitude}, {longitude}")
        # Удаляем из полученного адреса индекс почти и страну(Узбекистан)
        location_list = location_text.address.split(', ')
        location_text = ', '.join(location_list[:-2])
        msg5 = f"\n{config['msg']['address']} {location_text}"
    except:
        msg5 = ''

    msg = msg1 + '\n' + msg2 + '\n\n' + msg3 + '\n' + msg4 + msg5

    # Получаем список [(chat_id, first_name, notification), ...] админов где столбец latecomer_send_comment_notification = 1
    admins_list = sql_handler.get_admins_where_notification_on('comment_notification')

    # Отправим админам у кого latecomer_send_comment_notification == 1
    for admin in admins_list:
        # Отправим сперва геолокацию, потом сообщения
        location_message = await message.bot.send_location(
            admin[0],
            latitude=latitude,
            longitude=longitude
        )
        # Отправим составленное сообщение
        await message.bot.send_message(
            admin[0],
            msg,
            reply_to_message_id=location_message.message_id
        )


async def check_end_of_the_day(dp: Dispatcher):
    """
    Функция в конце дня проверяет кто ушел до конца рабочего дня и отправит админам список
    :param dp:
    :return:
    """
    today = datetime.datetime.today()
    # Получит число от 1-7. Если 1 значит сегодня понидельник, а если 7 значит воскресенье
    day_of_week = datetime.datetime.isoweekday(today)
    # Если сегодня выходной то скрипт остановиться
    if str(day_of_week) in config['time']['day_off']:
        return

    # Получим dict тех кто ушел раньше: {id(int): (ID(00000012), date, time), ...}
    early_leaved_users_dict = sql_handler.get_early_leaved_users()

    # msg2 в виде листа
    msg2_list = []
    # Заполняем msg2_list с данными: [(ФИО, Ушел в: 15:05, Ушел раньше чем: 03:55), ...]
    for user_id, leaved_user_info in early_leaved_users_dict.items():
        # Запишем тех кто ушел раньше в таблицу early_leaved(report_id, user_id, date, time).
        # early_leaved_writer сам создает report id и возвращает его. Он нам понадобиться при создании inline кнопки,
        # чтобы рано ушедшие могли оставить комментарии.
        report_id = sql_handler.early_leaved_writer(user_id, leaved_user_info[1], leaved_user_info[2])

        # Определим на сколько часов и минут он ушел раньше
        end_time_delta = datetime.timedelta(hours=int(config['time']['end_hour']),
                                            minutes=int(config['time']['end_minute']))
        leaved_time_delta = datetime.timedelta(
            hours=leaved_user_info[2].hour,
            minutes=leaved_user_info[2].minute,
            seconds=leaved_user_info[2].second
        )
        early_seconds = end_time_delta - leaved_time_delta
        early_time_hour = (datetime.datetime.min + early_seconds).time()

        hour = str(early_time_hour.hour)
        minute = str(early_time_hour.minute)
        if hour == '0':
            early_time = f"{minute} мин."
        else:
            early_time = f"{hour.lstrip('0')} час. {minute} мин."

        # Получаем информацию рабочего (id, name, who, chat_id)
        user_data = sql_handler.get_user_info_by_id(user_id)
        msg2_1 = user_data[1]
        msg2_2 = config['msg']['leaved'] + ' ' + leaved_user_info[2].strftime('%H:%M')
        msg2_3 = config['msg']['early_leaved'] + ' ' + early_time
        msg = msg2_1 + '\n' + msg2_2 + '\n' + msg2_3
        msg2_list.append(msg)

        # Это функция отправит человеку кто ушел раньше сообщение с inline кнопкой 'Оставить комментарий"
        await send_notification_to_early_leaver(dp, report_id, user_data)

    # Составим сообщения чтобы отправить админам
    lines = config['msg']['three_lines']
    msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
    msg2 = config['msg']['early_leaved_users']
    # Если хоть кто-то ушел раньше времени
    if msg2_list:
        msg3 = '\n\n'.join(msg2_list)
    # Если все ушли после окончания дня(нету нарушений)
    else:
        msg3 = config['msg']['empty']
    msg = msg1 + '\n' + msg2 + '\n' + msg3

    # Отправим админам кто ушел раньше
    # Получаем список [(chat_id, first_name, notification), ...] админов где столбец early_leave_notification = 1
    admins_list = sql_handler.get_admins_where_notification_on('early_leave_notification')

    # Отправим сообщение всем админам список тех кто ушел раньше и на сколько
    for admin in admins_list:
        try:
            await dp.bot.send_message(
                admin[0],
                msg
            )
        except Exception as e:
            with open('journal.txt', 'a') as w:
                w.write(datetime.datetime.now().strftime('%d.%m.%Y %H:%M  ') + \
                        'checkup.check_end_of_the_day:\n' + str(e) + '\n\n')


async def send_notification_to_early_leaver(dp: Dispatcher, report_id, early_leaver_info):
    """
    Сперва создает строку в таблице "early_leaved": ID(8 значное код), user_id(ID того кто опоздал), date(сегодняшнее число), time
    а столбец comment останется пустым.
    Отправит сообщения всем кто ушел раньше сообщения что они ушли раньше времени с inline кнопкой "Оставить комментарии",
    callback_data кнопки будет хранить "report.ID"
    :param dp:
    :param report_id: хранит 8 значное сгенерированный код
    :param early_leaver_info: хранит в себе (id, name, who, chat_id)  # ID это early_leaver_id
    :return:
    """

    # Создадим inline кнопку "Оставить комментарии"
    leave_comment_button = button_creators.inline_keyboard_creator(
        [[[config['msg']['leave_comment'], f'early_leave_comment{report_id}']]])

    # теперь отправим сообщения тому кто-ушел раньше чтобы он мог оставить комментарий о том почему ушел раньше
    msg1 = f"{config['msg']['date']} {datetime.date.today().strftime('%d.%m.%Y')}"
    msg2 = f"<b>{early_leaver_info[1]}</b> {config['msg']['early_leave_question']}"
    msg = msg1 + '\n' + msg2

    # Отправим сообщения с inline кнопкой "Оставить комментарии" опоздавшему
    await dp.bot.send_message(
        early_leaver_info[3],
        msg,
        reply_markup=leave_comment_button
    )


async def early_leave_comment_inline_button_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запустится если сотрудник нажал на "Оставить комментарий" при раннем уходе
    :param callback_query:
    :param state:
    :return:
    """
    report_id = callback_query.data.replace('late_missing_comment', '')

    # Удаляем inline кнопку
    await callback_query.bot.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )

    # Сохраним report_id
    await state.update_data(report_id=report_id)

    # Установим статус
    await MyStates.waiting_for_early_leave_comment.set()

    # Отправим сообщения "Можете оставить комментарии"
    msg = config['msg']['you_can_leave_comment']

    # Создадим кнопку "Отменить"
    button = button_creators.reply_keyboard_creator([[config['msg']['cancel']]], one_time=True)

    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def early_leaved_comment_handler(message: types.Message, state: FSMContext):
    """
    Запустится после того как рано ушедший оставил комментарию
    :param message:
    :param state:
    :return:
    """
    # Если нажал на кнопку Отменить вместо того чтобы ответить
    if message.text == config['msg']['cancel']:
        await state.finish()

        msg = config['msg']['leave_comment_cancaled']
        await message.answer(msg)
    else:
        comment = message.text
        all_data = await state.get_data()
        report_id = all_data['report_id']

        # Сохраним комментарию в state
        # await state.update_data(comment=comment)

        # Запишем комментарию в таблицу early_leaved
        sql_handler.early_leaved_comment_writer(report_id, comment)

        # Меняем статус на waiting_for_early_leave_comment
        # await MyStates.waiting_for_early_leave_location.set()
        await state.finish()

        # Сообщим пользователю что комментария сохранена и попросим от него отправить геолокацию
        #geolocation_button = button_creators.geolocation_button(config['msg']['geolocation_button_text'])
        #msg1 = config['msg']['comment_saved']
        #msg2 = config['msg']['send_geolocation']
        #msg = f"{msg1}. {msg2}"
        #await message.answer(msg, reply_markup=geolocation_button)
        msg = config['msg']['comment_saved']
        button_remove = button_creators.hide_reply_buttons()
        await message.answer(msg, reply_markup=button_remove)

        # Составим сообщения чтобы отправить админам
        # Получит (user_id, date, time) из таблицы "early_leaved"
        early_leaved_worker_info = sql_handler.get_user_name_leaved_data_time_from_early_leaved(report_id)
        user_name = sql_handler.get_user_name(early_leaved_worker_info[0])

        lines = config['msg']['three_lines']
        msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
        msg2 = f"<b>{user_name}</b> {config['msg']['early_leaver_leaved_comment']}"
        msg3 = f"<b>{config['msg']['date']}</b> {early_leaved_worker_info[1].strftime('%d.%m.%Y')}"
        msg4 = f"{config['msg']['leaved']} {early_leaved_worker_info[2].strftime('%H:%M')}"
        msg5 = f"{config['msg']['reason']} {comment}"
        msg = msg1 + '\n' + msg2 + '\n' + msg3 + '\n' + msg4 + '\n' + msg5

        # Получаем список [(chat_id, first_name, notification), ...] админов где столбец comment_notification = 1
        admins_list = sql_handler.get_admins_where_notification_on('comment_notification')

        # Отправим админам у кого comment_notification == 1
        for admin in admins_list:
            # Отправим составленное сообщение
            await message.bot.send_message(
                admin[0],
                msg
            )


# Not working for now
async def early_leaved_geolocation_handler(message: types.Message, state: FSMContext):
    """
    Запустится после того как рано ушедший отправил свою геолокацию
    :param message:
    :param state:
    :return:
    """
    all_data = await state.get_data()
    comment_id = all_data['report_id']
    comment = all_data['comment']

    # Отключаем state
    await state.finish()

    latitude = message.location.latitude
    longitude = message.location.longitude
    geolocation = str(latitude) + ',' + str(longitude)
    # Запишем геолокацию в таблицу early_leaved
    sql_handler.early_leaved_geolocation_writer(comment_id, geolocation)

    # Отправим раноушедшему сообщение что геолокация успешно сохранено
    msg = config['msg']['thanks_for_comment']
    await message.answer(msg)

    # Составим сообщения чтобы отправить админам
    # Получит (user_id, date, time) из таблицы "early_leaved"
    early_leaved_worker_info = sql_handler.get_user_name_leaved_data_time_from_early_leaved(comment_id)
    user_name = sql_handler.get_user_name(early_leaved_worker_info[0])

    lines = config['msg']['three_lines']
    msg1 = lines + ' ' + datetime.date.today().strftime('%d.%m.%Y') + ' ' + lines
    msg2 = f"<b>{user_name}</b> {config['msg']['early_leaver_leaved_comment']}"
    msg3 = f"<b>{config['msg']['date']}</b> {early_leaved_worker_info[1].strftime('%d.%m.%Y')}"
    msg4 = f"{config['msg']['leaved']} {early_leaved_worker_info[2].strftime('%H:%M')}"
    msg5 = f"{config['msg']['reason']} {comment}"
    try:
        # С помощью модуля geopy используя координати определяем адрес
        location_text = geolocator.reverse(f"{latitude}, {longitude}")
        # Удаляем из полученного адреса индекс почти и страну(Узбекистан)
        location_list = location_text.address.split(', ')
        location_text = ', '.join(location_list[:-2])
        msg6 = f"\n{config['msg']['address']} {location_text}"
    except:
        msg6 = ''
    msg = msg1 + '\n' + msg2 + '\n\n' + msg3 + '\n' + msg4 + '\n' + msg5 + msg6

    # Получаем список [(chat_id, first_name, notification), ...] админов где столбец early_leave_notification = 1
    admins_list = sql_handler.get_admins_where_notification_on('comment_notification')

    # Отправим админам у кого early_leaver_send_comment_notification == 1
    for admin in admins_list:
        # Отправим сперва геолокацию, потом сообщения
        location_message = await message.bot.send_location(
            admin[0],
            latitude=latitude,
            longitude=longitude
        )
        # Отправим составленное сообщение
        await message.bot.send_message(
            admin[0],
            msg,
            reply_to_message_id=location_message.message_id
        )


async def schedule_jobs(dp):
    start_hour = int(config['time']['start_hour'])
    start_minute = int(config['time']['start_minute'])

    end_hour = int(config['time']['end_hour'])
    end_minute = int(config['time']['end_minute'])

    scheduler.add_job(check_users_in_logs, 'cron', hour=start_hour, minute=start_minute, args=(dp,))
    scheduler.add_job(check_last_2min_logs, 'cron', minute='*/1', args=(dp,))
    scheduler.add_job(check_end_of_the_day, 'cron', hour=end_hour, minute=end_minute, args=(dp,))


def register_handlers(dp: Dispatcher):
    # Если сотрудник нажал на "Оставить комментарий" при опоздании или если не пришел
    dp.register_callback_query_handler(
        leave_late_comment_inline_button_handler,
        lambda c: c.data.startswith('late_missing_comment')
    )

    # Если сотрудник нажал на "Оставить комментарий" при раннем уходе
    dp.register_callback_query_handler(
        early_leave_comment_inline_button_handler,
        lambda c: c.data.startswith('early_leave_comment')
    )

    dp.register_message_handler(
        leaved_late_comment_handler,
        content_types=['text'],
        state=MyStates.waiting_for_late_comment
    )

    # Если рано ушедший нажал на reply кнопку "Отменить" вместо того чтобы написать комментарию
    dp.register_message_handler(
        early_leaved_comment_handler,
        content_types=['text'],
        state=MyStates.waiting_for_early_leave_comment
    )

    dp.register_message_handler(
        early_leaved_geolocation_handler,
        content_types=['location'],
        state=MyStates.waiting_for_early_leave_location
    )
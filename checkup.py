from aiogram import Dispatcher, types
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import button_creators
import sql_handler
import configparser
import datetime

scheduler = AsyncIOScheduler()

config = configparser.ConfigParser()
config.read('config.ini')


class MyStates(StatesGroup):
    waiting_for_comment = State()


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

        # Получаем список [(chat_id, first_name), ...] админов чтобы отправить список опоздавших
        admins_list = sql_handler.get_admins_list()

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

        # Получаем список [(chat_id, first_name), ...] админов чтобы отправить список тех кто пришел в выходные
        admins_list = sql_handler.get_admins_list()
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
        [[[config['msg']['leave_comment'], f'comment{report_id}']]])

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

    activate_time = datetime.time(start_hour, start_minute + 11, 0)
    end_time = datetime.time(end_hour, end_minute, 0)

    # Если время в промежутке 9:05 - 19:00
    now = datetime.datetime.now().time()
    today = datetime.datetime.today()
    # Получит число от 1-7. Если 1 значит сегодня понидельник, а если 7 значит воскресенье
    day_of_week = datetime.datetime.isoweekday(today)

    # if activate_time <= now < end_time and str(day_of_week) not in config['time']['day_off']:
    if activate_time <= now < end_time:
        # Получим список ID в виде МНОЖЕСТВО: "{'00000011', '00000026', ...}" тех кто зашел или ушел за последние 2мин
        last_2min_logs = sql_handler.get_last_2min_logins()

        # Если за последние 2 минуты кто-то пришел или ушел
        if last_2min_logs:
            for user in last_2min_logs:
                # Проверим опоздавшего на control/uncontrol
                control = sql_handler.check_control(int(user[0]))
                # Если опоздавший имеет статус Control, тогда админам отправим что он пришел только что пришел
                if control:
                    # Чтобы узнать первый раз ли он зашел получим количество логов рабочего за сегодня
                    all_logs_count = sql_handler.get_user_today_logs_count(user[0])

                    # Если это его первый раз за сегодня значит он только что пришел. Отправим админам что он пришел
                    if all_logs_count == 1:
                        admins = sql_handler.get_admins_list()
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


async def leave_comment_inline_button_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запуститься после того как пользователь нажал на inline кнопку "Оставить комментарии"
    :param state:
    :param callback_query:
    :return:
    """
    report_id = callback_query.data.replace('comment', '')

    # Удаляем inline кнопку
    await callback_query.bot.edit_message_reply_markup(
        callback_query.message.chat.id,
        callback_query.message.message_id
    )

    # Сохраним report_id
    await state.update_data(report_id=report_id)

    # Установим статус
    await MyStates.waiting_for_comment.set()

    # Отправим сообщения "Можете оставить комментарии"
    msg = config['msg']['you_can_leave_comment']

    # Создадим кнопку "Отменить"
    button = button_creators.reply_keyboard_creator([[config['msg']['cancel']]], one_time=True)

    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )


async def leaved_comment_handler(message: types.Message, state: FSMContext):
    # Если он нажал на кнопку "Отменить"
    if message.text == config['msg']['cancel']:
        await state.finish()
        msg = config['msg']['leave_comment_cancaled']

        await message.answer(msg)
    else:
        comment = message.text
        all_data = await state.get_data()
        comment_id = all_data['report_id']

        # Отключаем state
        await state.finish()

        # Запишем комментарию в таблицу report
        sql_handler.comment_writer(comment_id, comment)

        # Сообщим пользователю что комментария сохранена
        button_hider = button_creators.hide_reply_buttons()
        msg = config['msg']['comment_saved']
        await message.answer(msg, reply_markup=button_hider)


async def check_end_of_the_day(dp: Dispatcher):
    """
    Функция в конце дня проверяет кто ушел до конца рабочего дня, тогда запишет в таблицу "early_leaved" и отправит админам список
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
        # Запишем тех кто ушел раньше в таблицу early_leaved(id, date, time)
        sql_handler.early_leaved_writer(user_id, leaved_user_info[1], leaved_user_info[2])

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
    # Получаем список [(chat_id, first_name, notification), ...] админов где notification = 1
    admins_list = sql_handler.get_admins_where_notification_on()

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


async def schedule_jobs(dp):
    start_hour = int(config['time']['start_hour'])
    start_minute = int(config['time']['start_minute'])

    end_hour = int(config['time']['end_hour'])
    end_minute = int(config['time']['end_minute'])

    scheduler.add_job(check_users_in_logs, 'cron', hour=start_hour, minute=start_minute + 10, args=(dp,))
    scheduler.add_job(check_last_2min_logs, 'interval', seconds=60, args=(dp,))
    scheduler.add_job(check_end_of_the_day, 'cron', hour=end_hour, minute=end_minute, args=(dp,))


def register_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        leave_comment_inline_button_handler,
        lambda c: c.data.startswith('comment')
    )

    dp.register_message_handler(
        leaved_comment_handler,
        state=MyStates.waiting_for_comment
    )

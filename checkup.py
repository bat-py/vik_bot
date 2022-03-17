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
    # Получаем ID тех кто пришел в 9:01 каждый день
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

    # Составляет сообщение чтобы отправить админам
    msg1 = config['msg']['list_of_latecomers']
    msg2 = '\n'.join(latecommer_users_names)
    msg = msg1 + '\n' + msg2

    # Получаем список [(chat_id, first_name), ...] админов чтобы отправить список опоздавших
    admins_list = sql_handler.get_admins_list()

    # Отправляет сообщения всем админам
    for i in admins_list:
        await dp.bot.send_message(
            i[0],
            msg
        )

    # Каждому опоздавщему отправим сообщение чтобы он ответил почему опаздывает
    for user in latecommer_users:
        # Так как он будет отправлять каждому опоздавшему сообщения, но если кто-то заблокировал бот, он его пропустит
        try:
            await send_notification_to_latecomer(dp, user)
        except:
            pass


async def send_notification_to_latecomer(dp: Dispatcher, latecomer_info):
    """
    Сперва создает строку в таблице "report": ID(8 значное код), user_id(ID того кто опоздал), date(сегодняшнее число),
    а столбец comment останется пустым.
    Отправит сообщения всем опоздавшим сообщения что они опоздали с inline кнопкой "Оставить комментарии",
    callback_data кнопки будет хранить "report.ID"
    latecomer_info хранит в себе (ID, Name, chat_id)  # ID это latecomer_id
    :param dp:
    :param latecomer_id:
    :return:
    """
    # report_creator создает запись в таблице report(id, user_id, date) и возвращает генерированный код(id)
    report_id = sql_handler.report_creator(latecomer_info[0])

    # Создадим inline кнопку "Оставить комментарии"
    leave_comment_button = button_creators.inline_keyboard_creator(
        [[[config['msg']['leave_comment'], f'comment{report_id}']]])

    # Составим сообщение
    msg = f"<b>{latecomer_info[1]}</b> {config['msg']['you_late']}"

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

    activate_time = datetime.time(start_hour, start_minute + 5, 0)
    end_time = datetime.time(end_hour, end_minute, 0)

    # Если время в промежутке 9:05 - 19:00
    now = datetime.datetime.now().time()
    if activate_time <= now < end_time:
        # Получим список ID в виде МНОЖЕСТВО: "{'00000011', '00000026', ...}" тех кто зашел или ушел за последние 2мин
        last_2min_logs = sql_handler.get_last_2min_logins()

        # Если за последние 2 минуты кто-то пришел или ушел
        if last_2min_logs:
            for user in last_2min_logs:
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
                    print(user[0])
                    print(user[1])
                    print(user[1].hour)
                    print(user[1].minute)
                    now_time = datetime.time(user[1].hour, user[1].minute, user[1].second)
                    now_delta = datetime.timedelta(hours=user[1].hour, minutes=user[1].minute, seconds=user[1].second)
                    late_second = now_delta - beginning_delta
                    late_time_hour = (datetime.datetime.min + late_second).time()
                    late_time = late_time_hour.strftime("%H:%M:%S")

                    if late_time_hour.hour == 0:
                        hour_or_minute = config['msg']['minute']
                    else:
                        hour_or_minute = config['msg']['hour']

                    # Составим сообщения чтобы отправить админам
                    msg1 = f'<b>{user_info[1]}</b> '
                    msg2 = config['msg']['latecomer_came']
                    msg3 = f"{config['msg']['arrival_time']} {now_time.strftime('%H:%M:%S')}"
                    msg4 = f"{config['msg']['late_by']} {late_time}"
                    msg = msg1 + msg2 + '\n\n' + msg3 + '\n\n' + msg4

                    for admin_id in admins_chat_id_list:
                        await dp.bot.send_message(
                            admin_id,
                            msg
                        )


async def leave_comment_inline_button_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запуститься после того как пользователь нажал на inline кнопку "Оставить комментарии"
    :param callback_query:
    :return:
    """
    report_id = callback_query.data.replace('comment', '')

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

        # Запишем комментарию в таблицу report
        sql_handler.comment_writer(comment_id, comment)

        # Сообщим пользователю что комментария сохранена
        button_hider = button_creators.hide_reply_buttons()
        msg = config['msg']['comment_saved']
        await message.answer(msg, reply_markup=button_hider)


async def schedule_jobs(dp):
    hour = int(config['time']['start_hour'])
    minute = int(config['time']['start_minute'])

    scheduler.add_job(check_users_in_logs, 'cron', day_of_week='mon-sat', hour=hour, minute=minute, args=(dp,))
    scheduler.add_job(check_last_2min_logs, 'interval', seconds=120, args=(dp,))


def register_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(
        leave_comment_inline_button_handler,
        lambda c: c.data.startswith('comment')
    )

    dp.register_message_handler(
        leaved_comment_handler,
        state=MyStates.waiting_for_comment
    )

from aiogram import Dispatcher, types
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import sql_handler
import configparser
import datetime

scheduler = AsyncIOScheduler()

config = configparser.ConfigParser()
config.read('config.ini')


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


async def check_last_2min_logs(dp: Dispatcher):
    start_hour = int(config['time']['start_hour'])
    start_minute = int(config['time']['start_minute'])
    end_hour = int(config['time']['end_hour'])
    end_minute = int(config['time']['end_minute'])

    activate_time = datetime.time(start_hour, start_minute+5, 0)
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


async def schedule_jobs(dp):
    hour = int(config['time']['start_hour'])
    minute = int(config['time']['start_minute'])

    scheduler.add_job(check_users_in_logs, 'cron', day_of_week='mon-sat', hour=hour, minute=minute, args=(dp, ))
    scheduler.add_job(check_last_2min_logs, 'interval', seconds=120, args=(dp, ))


import pypyodbc
import random
import datetime
import configparser

config = configparser.ConfigParser()
config.read('config.ini')


def connection_creator():
    """
    :return: connect object
    """
    connection = pypyodbc.connect(f"Driver={config['sql']['driver']};"
                                  f"Server={config['sql']['server']};"
                                  f"Database={config['sql']['database']};"
                                  f"uid={config['sql']['uid']};"
                                  f"pwd={config['sql']['pwd']};")

    return connection


def get_all_users():
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM "user"')
    users_list = cursor.fetchall()

    connection.close()
    return users_list


def get_all_users_id(control=False):
    connection = connection_creator()
    cursor = connection.cursor()

    if control:
        cursor.execute('SELECT ID FROM "user" WHERE Who = ?', ('Control',))
    else:
        cursor.execute('SELECT ID FROM "user"')
    users_list = cursor.fetchall()

    connection.close()
    return users_list


def get_user_name(user_id):
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT Name FROM "user" WHERE ID = ?;', (user_id,))
    users_name = cursor.fetchone()

    try:
        name = users_name[0]
    except:
        name = '?????'

    connection.close()
    return name


def get_user_name_and_who(user_id):
    """
    :param user_id:
    :return: user_name, who(Control/Uncontrol)
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT Name, Who FROM "user" WHERE ID = ?;', (user_id,))
    users_name = cursor.fetchone()

    connection.close()

    if users_name:
        return users_name
    else:
        return '?????', 'Control'


def update_chat_id(chat_id: int, user_id: int):
    """
    Updates chat_id in table "user"
    :param user_id:
    :param chat_id:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('UPDATE "user" SET chat_id = ? WHERE ID = ?', (chat_id, user_id))
    connection.commit()

    connection.close()


def get_todays_logins():
    """
    :return: ID пользователей кто пришел сегодня. С помощью DISTINCT избавились от дубликатов ID,
    """
    connection = connection_creator()
    cursor = connection.cursor()

    # Получаем сегодняшные записи
    cursor.execute(
        'SELECT DISTINCT ID FROM ivms WHERE date >= cast(getdate() as date) and date < cast(getdate()+1 as date) ORDER BY ID;')
    logins = cursor.fetchall()

    connection.close()
    return logins


def get_present_workers_list():
    """
    :return: Список тех кто пришел сегодня(последный запись за сегодня): [(id, time, DeviceNo, name), ].
    Если DeviceNo == out значит он вышел на улицу и не в офисе
    """
    connection = connection_creator()
    cursor = connection.cursor()

    # Получаем сегодняшные записи
    cursor.execute("""
    SELECT ID, time, DeviceNo
    FROM ivms WHERE date >= cast(getdate() as date) and date < cast(getdate()+1 as date)
    ORDER BY datetime DESC;
    """)
    all_data = cursor.fetchall()

    # Тут хранится самый последний сегодняшний запись о пользователей: [(user_id, time, DeviceNo, user_name), ....]
    all_workers_last_log = []

    added_users = []
    for i in all_data:
        # Если еще нету id этого человека в added_users, тогда его запищим
        if i[0] not in added_users:
            # Добавим id сотрудника в added_users. Следующий раз его проверять не будем
            added_users.append(i[0])

            # Получает имя сотрудника и Who(Control/Uncontrol)
            name_and_who = get_user_name_and_who(int(i[0]))

            # Если человек находится в Control, значит его добавим в all_workers_last_log
            if name_and_who[1] == 'Control':
                all_workers_last_log.append((*i, name_and_who[0]))

    connection.close()
    return all_workers_last_log


def get_users_name_chat_id(id_list):
    connection = connection_creator()
    cursor = connection.cursor()

    if len(id_list) == 1:
        cursor.execute('SELECT ID, Name, chat_id FROM "user" WHERE ID = ?', (id_list[0], ))
    else:
        cursor.execute('SELECT ID, Name, chat_id FROM "user" WHERE ID IN {}'.format(tuple(id_list)))

    users_list = cursor.fetchall()

    connection.close()
    return users_list


def add_new_admin(chat_id, first_name):
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('INSERT INTO "admins" VALUES(?, ?, ?)', (chat_id, first_name, 0))
    connection.commit()

    connection.close()


def get_admins_list():
    """
    :return: admins list: [(chat_id, first_name, notification), ...]
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM "admins";')
    admins_list = cursor.fetchall()

    connection.close()
    return admins_list


def get_admins_where_notification_on(type_of_notification):
    """
    :param type_of_notification: Тут передаешь имя столбца уведомления(их 4) из таблицы admins
    :return: admins chat_id list where type_of_notification is on: [(chat_id,), ...]
    """
    connection = connection_creator()
    cursor = connection.cursor()

    #cursor.execute('SELECT * FROM "admins" WHERE {} = 1;'.format(type_of_notification))
    cursor.execute('SELECT chat_id FROM "admins" WHERE {} = 1;'.format(type_of_notification))

    admins_list = cursor.fetchall()

    connection.close()
    return admins_list


print(get_admins_where_notification_on('comment_notification'))


def check_admin_exist(chat_id):
    """
    Проверяет существует ли этот пользователь в списке админов
    :param chat_id:
    :return:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT chat_id FROM "admins" WHERE chat_id = ?;', (chat_id,))
    admin = cursor.fetchone()

    connection.close()
    return admin


def get_admin_notification_status(chat_id):
    """
    :param chat_id:
    :return: Возвращает 3 статуса: (0, 1, 0)
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""
    SELECT late_come_notification, latecomer_came_notification, comment_notification, early_leave_notification
    FROM "admins" 
    WHERE chat_id = ?;""", (chat_id,))
    status = cursor.fetchone()

    connection.close()
    return status


def update_admin_notification_status(chat_id, status):
    """
    :param chat_id:
    :param status: Тут будет кортеж с 3 статусами: (0, 1, 0)
    :return:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""
    UPDATE "admins"
    SET late_come_notification = ?, latecomer_came_notification = ?, comment_notification = ?, early_leave_notification = ?
    WHERE chat_id = ?;""", (*status, chat_id))
    connection.commit()

    connection.close()


def get_admin_menu_password():
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT data FROM "data" WHERE data_name = 'password';""")
    password = cursor.fetchone()[0]

    connection.close()
    return password


def get_last_2min_logins():
    """
    :return: Вернет ID тех людей кто зашел или ушел последние за 2мин
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT ID, time FROM ivms WHERE datetime >= DATEADD(minute, -1 , GETDATE());""")
    # cursor.execute("""SELECT time FROM ivms WHERE datetime >= DATEADD(minute, -5, GETDATE());""")

    logins = cursor.fetchall()
    id = []
    clean_logins = []

    for login in logins:
        if not (login[0] in id):
            clean_logins.append(login)
            id.append(login[0])

    connection.close()
    return clean_logins


def get_user_today_logs_count(user_id):
    """
    :return: Вернет список ID всех входов и выходов. Например [1,1, ..., 5,5,5,5] Тут человек с ID 5 2 раза зашел и 2 раза выходил
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT COUNT(ID) FROM ivms WHERE ivms.date = CONVERT(date, GETDATE()) AND ID = ?;""",
                   (user_id,)
                   )
    todays_logs_count = cursor.fetchone()[0]

    connection.close()

    return todays_logs_count


def get_user_info_by_id(user_id):
    """
    :param user_id:
    :return: User info: (id, name, who, chat_id)
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT * FROM "user" WHERE ID = ?""", (user_id,))
    user_info = cursor.fetchone()

    connection.close()

    return user_info


def report_creator(user_id):
    connection = connection_creator()
    cursor = connection.cursor()

    date = datetime.date.today()

    symbols = []
    symbols.extend(list(map(chr, range(ord('A'), ord('Z') + 1))))
    symbols.extend(list(map(chr, range(ord('a'), ord('z') + 1))))
    symbols.extend(list(str(i) for i in range(0, 10)))

    while True:
        # Рандомно генерируем 8 код
        generated_id = ''.join([random.choice(symbols) for i in range(8)])

        # Создаем новый запись в таблице
        try:
            cursor.execute("""INSERT INTO "report"(id, user_id, date) VALUES(?, ?, ?);""",
                           (generated_id, user_id, date))
            connection.commit()
            break
        # Если генерированный код уже есть в таблице, тогда выйдет ошибка и цикл опять заработает
        except:
            pass

    connection.close()

    return generated_id


def get_report_by_id(report_id):
    """
    :param report_id:
    :return: Возвращает найденный report по id: (id, user_id, date, comment, time, location)
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT * FROM "report" WHERE id = ?""", (report_id,))
    report = cursor.fetchone()

    connection.close()
    return report


def comment_writer(comment_id, comment):
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""UPDATE "report" SET comment = ? WHERE id = ? """, (comment, comment_id))
    connection.commit()

    connection.close()


def location_writer(comment_id, latitude, longitude):
    connection = connection_creator()
    cursor = connection.cursor()

    location = str(latitude) + ',' + str(longitude)

    cursor.execute("""UPDATE "report" SET location = ? WHERE id = ? """, (location, comment_id))
    connection.commit()

    connection.close()


def get_all_workers():
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM "user" WHERE Who = ?', ('Control',))
    users_list = cursor.fetchall()

    connection.close()
    return users_list


def get_data_by_term(user_id, term):
    """
    :param user_id:
    :param term:
    :return: Возвращает записи из таблицы "report" работника в указанном сроке: [(id, user_id, date, comment, time, locatoin), ]
    """
    connection = connection_creator()
    cursor = connection.cursor()
    term = int(term) - 1

    # Получаем  записи
    cursor.execute("""
        SELECT * FROM "report" 
        WHERE date >= cast(getdate()-? as date) AND
        date < cast(getdate()+1 as date) AND 
        user_id = ? 
        ORDER BY ID;
        """, (term, user_id)
                   )
    data = cursor.fetchall()

    connection.close()
    return data


def late_time_writer(user_id, come_time):
    """
    Эта функция запишет в столбец time таблицы report время прихода опоздавшего.
    :param come_time:
    :param user_id:
    :return:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""
    UPDATE report SET time = ?
    WHERE date >= cast(getdate() as date) AND
    date < cast(getdate()+1 as date) AND
    user_id = ?;""", (come_time, user_id))
    connection.commit()

    connection.close()


def check_control(user_id):
    """
    Возвращает True если указанный user имеет статус Control
    :param user_id:
    :return:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT ID FROM "user" WHERE ID = ? AND Who = ?;', (user_id, 'Control'))
    user_checked = cursor.fetchone()

    connection.close()
    return user_checked


def get_early_leaved_users():
    """
    Возвращает список людей кто ушел раньше сегодня
    :return: Возвращает dict:  {id: (ID(00000012), date, time), ...}
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""
                    SELECT ID, date, time FROM ivms
                    WHERE date >= cast(getdate() as date) AND date < cast(getdate()+1 as date) AND
                    DeviceNo = ?
                    ORDER BY time DESC;
                    """,
                   (config['device']['out_device'],)
                   )
    today_data = cursor.fetchall()

    # Берем самые последные выходы работников за сегодня
    early_leaved_users_dict = {}
    for out in today_data:
        if int(out[0]) not in early_leaved_users_dict:
            early_leaved_users_dict[int(out[0])] = out

    # Создаем новый dict тех кто ушел раньше
    early_leaved_users_dict_clear = {}
    for user_id, out in early_leaved_users_dict.items():
        # Проверяем user на control. Если в 'user.Who' у него uncontrol, тогда его пропустим
        if not check_control(user_id):
            continue

        end_time_delta = datetime.timedelta(hours=int(config['time']['end_hour']),
                                            minutes=int(config['time']['end_minute'])-10)
        leaved_time_delta = datetime.timedelta(hours=out[2].hour, minutes=out[2].minute)
        if leaved_time_delta < end_time_delta:
            early_leaved_users_dict_clear[user_id] = out

    connection.close()
    return early_leaved_users_dict_clear


###
def early_leaved_writer(user_id, date, time):
    """
    Создает новую строку в таблице early_leaved
    :param user_id:
    :param date:
    :param time:
    :return:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""INSERT INTO "early_leaved" VALUES(?, ?, ?)""", (user_id, date, time))
    connection.commit()

    connection.close()


###
def early_leaved_user_history(user_id, term):
    """
    :param term:
    :param user_id:
    :return: Возвращает историю(на сколько рано ушел) указанного рабочего в указанном периоде: [(id, date, time), ...]

    """
    connection = connection_creator()
    cursor = connection.cursor()

    term = int(term) - 1

    cursor.execute("""
                    SELECT * FROM "early_leaved" 
                    WHERE date >= cast(getdate()-? as date) AND
                    date < cast(getdate()+1 as date) AND 
                    id = ?;""",
                   (term, user_id)
                   )

    user_history = cursor.fetchall()

    connection.close()
    return user_history


def get_user_in_out_history(user_id, date):
    """
    Может возвращать 3 варианта:
    Когда нету входа: False
    Когда есть входа в выхода нет: (in_time, False)
    Когда есть вход и выход: (in_time, out_time)
    :param date:
    :param user_id:
    :return: Возвращает самый первый вход и последний выход указанного дня: (in_time, out_time). Если не пришел в тот день, тогда false

    """
    connection = connection_creator()
    cursor = connection.cursor()

    in_device = config['device']['in_device']
    out_device = config['device']['out_device']

    cursor.execute("""
                    SELECT time FROM "ivms" 
                    WHERE date = ? AND ID LIKE ? AND DeviceNo = ?
                    ORDER BY datetime;
                    """,
                   (date, '%000'+str(user_id), in_device)
                   )
    # Берем самый первый элемент из списка, так как нам нужен только время входа
    user_in = cursor.fetchone()

    # Если он пришел хотя бы один вход в выбранный день
    if user_in:
        in_time = user_in[0]

        # Получим out_time. Для этого берем самый последний запись в выбранном числе
        cursor.execute("""
                        SELECT time FROM "ivms" 
                        WHERE date = ? AND ID LIKE ? AND DeviceNo = ?
                        ORDER BY datetime DESC;
                        """,
                       (date, '%0' + str(user_id), out_device)
                       )
        # Получаем время выхода
        user_out = cursor.fetchone()

        # Если получили хотябы один выход в выбранном числе. Иногда бывает вход есть, а выхода нет. Поэтому нужно проверять
        if user_out:
            out_time = user_out[0]
        else:
            out_time = False

        connection.close()
        return in_time, out_time
    else:
        connection.close()
        return False


def get_user_in_history(user_id, date):
    """
    Может возвращать 2 варианта:
    Когда есть входа: in_time
    Когда нету входа: False
    :param date:
    :param user_id:
    :return: Возвращает самый первый вход

    """
    connection = connection_creator()
    cursor = connection.cursor()

    in_device = config['device']['in_device']

    cursor.execute("""
                    SELECT time FROM "ivms" 
                    WHERE date = ? AND ID LIKE ? AND DeviceNo = ?
                    ORDER BY datetime;
                    """,
                   (date, '%000'+str(user_id), in_device)
                   )
    # Берем самый первый элемент из списка, так как нам нужен только время входа
    user_in = cursor.fetchone()

    connection.close()
    return user_in


def get_user_out_history(user_id, date):
    """
    Может возвращать 2 варианта:
    Когда есть выход: out_time
    Когда нету выхода: False
    :param date:
    :param user_id:
    :return: Возвращает самый последний выход указанного дня: out_time. Если не пришел в тот день, тогда false
    """

    connection = connection_creator()
    cursor = connection.cursor()

    out_device = config['device']['out_device']

    # Получим out_time. Для этого берем самый последний запись в выбранном числе
    cursor.execute("""
                    SELECT time FROM "ivms" 
                    WHERE date = ? AND ID LIKE ? AND DeviceNo = ?
                    ORDER BY datetime DESC;
                    """,
                   (date, '%0' + str(user_id), out_device)
                   )
    # Получаем время выхода
    user_out = cursor.fetchone()

    connection.close()
    return user_out


def get_all_in_outs_one_day(user_id, date):
    """
    Возвращает все in out указанного дня: [(datetime.time(9, 6, 47), 'DeviceNo'), ...]. Если ничего не найдено, тогда: []
    :param user_id:
    :param date:
    :return:
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""
                        SELECT time, DeviceNo FROM "ivms" 
                        WHERE date = ? AND ID LIKE ?
                        ORDER BY datetime;
                        """,
                   (date, '%0' + str(user_id))
                   )

    all_in_outs_one_day = cursor.fetchall()

    return all_in_outs_one_day



def test():
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT datetime, date, time, DeviceNo FROM "ivms";""")
    user_history = cursor.fetchall()

    connection.close()
    return user_history


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

    connection.close()
    return users_name[0]


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


def get_users_name_chat_id(id_list):
    connection = connection_creator()
    cursor = connection.cursor()

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
    :return: admins list: [(chat_id, first_name), ...]
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM "admins";')
    admins_list = cursor.fetchall()

    connection.close()
    return admins_list


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
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT notification FROM "admins" WHERE chat_id = ?;', (chat_id,))
    admin = cursor.fetchone()[0]

    connection.close()
    return admin


def update_admin_notification_status(chat_id, status):
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('UPDATE "admins" SET notification = ? WHERE chat_id = ?;', (status, chat_id))
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

    cursor.execute("""SELECT ID, time FROM ivms WHERE datetime >= DATEADD(minute, -2 , GETDATE());""")
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


def comment_writer(comment_id, comment):
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""UPDATE "report" SET comment = ? WHERE id = ? """, (comment, comment_id))
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
    :return: Возвращает записи из таблицы "report" работника в указанном сроке
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

import pypyodbc


def connection_creator():
    """
    :return: connect object
    """
    connection = pypyodbc.connect('Driver={ODBC Driver 17 for SQL Server};'
                                  'Server=84.54.115.2;'
                                  'Database=telegrambot;'
                                  'uid=sa;'
                                  'pwd=sherxan@123#;')

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

    cursor.execute('SELECT Name FROM "user" WHERE ID = ?;', (user_id, ))
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
    cursor.execute('SELECT DISTINCT ID FROM ivms WHERE date >= cast(getdate() as date) and date < cast(getdate()+1 as date) ORDER BY id;')
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

    cursor.execute('INSERT INTO "admins" VALUES(?, ?)', (chat_id, first_name))
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

    cursor.execute('SELECT chat_id FROM "admins" WHERE chat_id = ?;', (chat_id, ))
    admin = cursor.fetchone()

    connection.close()
    return admin


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

    cursor.execute("""SELECT ID FROM ivms WHERE datetime >= DATEADD(minute, -2 , GETDATE());""")
    #cursor.execute("""SELECT time FROM ivms WHERE datetime >= DATEADD(minute, -5, GETDATE());""")

    logins = set([i[0] for i in cursor.fetchall()])

    connection.close()
    return logins


def get_user_today_logs_count(user_id):
    """
    :return: Вернет список ID всех входов и выходов. Например [1,1, ..., 5,5,5,5] Тут человек с ID 5 2 раза зашел и 2 раза выходил
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute("""SELECT COUNT(ID) FROM ivms WHERE ivms.date = CONVERT(date, GETDATE()) AND ID = ?;""",
                   (user_id, )
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

    cursor.execute("""SELECT * FROM "user" WHERE ID = ?""", (user_id, ))
    user_info = cursor.fetchone()

    connection.close()

    return user_info


print(get_user_info_by_id(1))
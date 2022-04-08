def get_admins_where_notification_on():
    """
    :return: admins list where notification is on: [(chat_id, first_name, notification), ...]
    """
    connection = connection_creator()
    cursor = connection.cursor()

    cursor.execute('SELECT * FROM "admins" WHERE notification = ?;', (1,))
    admins_list = cursor.fetchall()

    connection.close()
    return admins_list
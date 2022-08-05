import sql_handler

admins = sql_handler.get_admins_where_notification_on('latecomer_came_notification')
admins_chat_id_list = list(map(lambda i: i[0], admins))

print(admins_chat_id_list)

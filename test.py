
def on_off_menu_handler_buttons_creator(admin_status):
    """
    Функцию передаем лист: [0, 1, 1, 0]. Исходя из этого он создает нам кнопки
    :param admin_status:
    :return: Вернет созданные кнопки меню "Вкл/Выкл уведомление"
    """
    on = config['msg']['on']
    off = config['msg']['off']

    statues = []
    for i in admin_status:
        # Если "Уведомление об опоздавших" включен
        if i:
            statues.append(on)
        else:
            statues.append(off)

    but1_msg = f"{config['msg']['late_come_notification']} (Статус: {statues[0]})"
    but2_msg = f"{config['msg']['latecomer_came_notification']} (Статус: {statues[1]})"
    but3_msg = f"{config['msg']['comment_notification']} (Статус: {statues[2]})"
    but4_msg = f"{config['msg']['early_leave_notification']} (Статус: {statues[3]})"
    but5_msg = config['msg']['main_menu']

    # Создаем inline кнопки
    buttons = button_creators.inline_keyboard_creator([
        [[but1_msg, 'notification_button1']],
        [[but2_msg, 'notification_button2']],
        [[but3_msg, 'notification_button3']],
        [[but4_msg, 'notification_button4']],
        [[but5_msg, 'main_menu']]
    ]
    )

    return buttons


async def on_off_menu_handler(message: types.Message):
    """
    Запустится после того как пользователь нажал на "Вкл/Выкл уведомление"
    :param message:
    :return:
    """
    check_admin = sql_handler.check_admin_exist(message.chat.id)

    # Если он зарегистрирован и есть в базе
    if check_admin:
        # Удаляем 2 последные сообщения
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        # В меню "Вкл/Выкл уведомление" будет 3 inline кнопки
        msg = config['msg']['on_off_menu']

        # Берем 3 статуса из таблицы admin и выходя из него создадим inline кнопки. Получит лист типа: (1, 0, 1, 0):
        # (late_come_notification, latecomer_came_notification, comment_notification, early_leave_notification)
        admin_status = sql_handler.get_admin_notification_status(message.chat.id)

        # Функция on_off_menu_handler_buttons_creator создает нам кнопки
        buttons = on_off_menu_handler_buttons_creator(admin_status)

        await message.bot.send_message(
            message.chat.id,
            msg,
            reply_markup=buttons
        )


async def on_off_buttons_handler(callback_query: types.CallbackQuery):
    """
    Отвечает за кнопки(Уведом. об опоздавших, Уведом. о приходе опоздавших, Уведом. о рано ушедших) меню
    "Вкл/Выкл уведомление"
    :param callback_query:
    :return:
    """
    chosen_button = callback_query.data.replace('notification_button', '')

    # Получаем все 4 статуса: [0, 1, 1, 0]
    all_notification_status = list(sql_handler.get_admin_notification_status(callback_query.from_user.id))

    # Если нажал на 1-кнопку: Уведом. об опоздавших
    if chosen_button == '1':
        # Если статус включен тогда его выключим
        if all_notification_status[0] == 1:
            all_notification_status[0] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[0] = 1

    # Если нажал на 2-кнопку: Уведом. о приходе опоздавших
    elif chosen_button == '2':
        # Если статус включен тогда его выключим
        if all_notification_status[1] == 1:
            all_notification_status[1] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[1] = 1

    # Если нажал на 3-кнопку: Уведом. об оставленном комментарии(геолокация)
    elif chosen_button == '3':
        # Если статус включен тогда его выключим
        if all_notification_status[2] == 1:
            all_notification_status[2] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[2] = 1

    # Если нажал на 4-кнопку: Уведом. о рано ушедших
    elif chosen_button == '4':
        # Если статус включен тогда его выключим
        if all_notification_status[3] == 1:
            all_notification_status[3] = 0
        # Если выключен тогда его включим
        else:
            all_notification_status[3] = 1

    # Сохраним изменения в базе
    sql_handler.update_admin_notification_status(callback_query.from_user.id, all_notification_status)

    # Создаем новые inline кнопки
    new_inline_buttons = on_off_menu_handler_buttons_creator(all_notification_status)

    # Изменим inline кнопки, чтобы админ видел что
    await callback_query.message.edit_reply_markup(new_inline_buttons)

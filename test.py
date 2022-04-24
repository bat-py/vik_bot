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
    admins_list = sql_handler.get_admins_where_notification_on('early_leaver_send_comment_notification')

    # Отправим админам у кого early_leaver_send_comment_notification == 1
    for admin in admins_list:
        # Отправим сперва геолокацию, потом сообщения
        await message.bot.send_location(
            admin[0],
            latitude=latitude,
            longitude=longitude
        )
        # Отправим составленное сообщение
        await message.bot.send_message(
            admin[0],
            msg
        )

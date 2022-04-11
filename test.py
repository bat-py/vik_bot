async def all_workers_late_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запустится если нажал на "🗂 Отчет всех сотрудников"  ->  "Опоздание"
    :param callback_query:
    :param state:
    :return:
    """
    # Удаляем 2 последние сообщения
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.all_workers_waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном диапазоне (1-30):
    chosen_term = all_data['term']

    # Получаем список всех рабочих(who=control): [(ID, name, Who, chat_id), ...]
    all_workers = sql_handler.get_all_workers()

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    # Каждый цыкл составит сообщение:
    # "--- 28.03.2022 ---\n Абдувосиков Жавохир (Приход 9:10)\n Шерибаев Азизбек (Приход 10:40)\n ..."
    for day in chosen_days:
        # Библиотека рабочих кто опоздал в указанном дне: {time: "Абдувосиков Жавохир (Приход 9:10)", ...}
        latecomer_users_in_day = {}
        # Каждый цыкл составит одну строку про одного опоздавшего челевека: "Абдувосиков Жавохир (Приход 9:10)"
        for worker in all_workers:
            # Получаем время приходауказанной даты: in_time или False если не пришел
            in_time = sql_handler.get_user_in_history(worker[0], day)

            # Если in_out_time не равно False
            if in_time:
                # Теперь определим опоздал ли он или нет
                start_hour = int(config['time']['start_hour'])
                start_minute = int(config['time']['start_hour']) + 10
                start_time = datetime.timedelta(hours=start_hour, minutes=start_minute)

                came_time = datetime.timedelta(
                    hours=in_time[0].hour,
                    minutes=in_time[0].minute,
                    seconds=in_time[0].second
                )

                # Если время прихода больше чем время начала работы(+10мин), значит он опоздал
                if came_time > start_time:
                    came_time_str = in_time[0].strftime('%H:%M')
                    # В latecomer_users_in_day добавим: "Абдувосиков Жавохир (Приход 9:10)"
                    mesg1 = f"{worker[1]} ({config['msg']['came_no_bold']} {came_time_str})"
                    latecomer_users_in_day[in_time[0]] = mesg1

        msg2_1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                 config['msg']['three_lines'] + '</b>\n'

        # Если данное число(date) выходной, тогда напишем: "🗓 Выходные\n Время прихода | Время ухода или просто "🗓 Выходные\n Не пришел"
        if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
            msg2_2 = config['msg']['weekend'] + '\n'
        else:
            msg2_2 = ''

        # Если в указанном дне хоть кто-то опоздал
        if latecomer_users_in_day:
            # Сортируем список опоздавших по возрастанию времени
            # Хранит [(time, "Абдувосиков Жавохир (Приход 9:10)"), ...]
            latecomer_users_list = list(latecomer_users_in_day.items())
            latecomer_users_list.sort(key=lambda item: item[0])
            latecomer_users_list = list(map(lambda it: it[1], latecomer_users_list))

            msg2_3 = '\n'.join(latecomer_users_list)
        else:
            msg2_3 = config['msg']['no_latecomers']

        msg2_block_list.append(msg2_1 + msg2_2 + msg2_3)

    msg1 = f"<b>{config['msg']['late_report_type']}</b>"
    msg2 = '\n\n'.join(msg2_block_list)
    msg = msg1 + '\n\n' + msg2

    # Кнопки "Назад" и "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])

    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )

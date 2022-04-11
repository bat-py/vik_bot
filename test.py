async def missed_days_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Запустится если нажал на "🗂 Отчет всех сотрудников"  ->  "Пропущенные дни"
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

    # Отправим всплывающее сообщение: Секундочку
    await callback_query.answer(
        config['msg']['wait']
    )

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
    # "--- 28.03.2022 ---\n Абдувосиков Жавохир \n Шерибаев Азизбек\n ..."
    for day in chosen_days:
        msg2_1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                 config['msg']['three_lines'] + '</b>\n'

        # Если данное число(date) выходной, тогда напишем: "--- 10.04.2022 ---\n 🗓 Выходные"
        if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
            msg2_2 = config['msg']['weekend']
            msg2_block_list.append(msg2_1 + msg2_2)
        else:
            # Библиотека рабочих кто не пришел
            missed_users_in_day = []

            # Каждый цыкл составит одну строку про одного опоздавшего челевека: "9:10  Абдувосиков Жавохир"
            for worker in all_workers:
                # Получаем время приходауказанной даты: in_time или False если не пришел
                in_time = sql_handler.get_user_in_history(worker[0], day)

                # Если in_time равно False, значит он не пришел
                if not in_time:
                    # В latecomer_users_in_day добавим: "Абдувосиков Жавохир"
                    missed_users_in_day.append(worker[1])

            # Если в указанном дне хоть кто-то не пришел
            if missed_users_in_day:
                msg2_3 = '\n'.join(missed_users_in_day)
            else:
                msg2_3 = config['msg']['no_missed']

            msg2_block_list.append(msg2_1 + msg2_3)

        msg1 = f"<b>{config['msg']['missed_days_report_type']}</b>"
        msg2 = '\n\n'.join(msg2_block_list)
        msg = msg1 + '\n\n' + msg2

        # Кнопки "Назад" и "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])

        await callback_query.bot.send_message(
            callback_query.from_user.id,
            msg,
            reply_markup=button
        )

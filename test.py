async def presence_time_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    """
    Если выбрал 5 пункт: Время присутствия
    :param state:
    :param callback_query:
    :return:
    """
    try:
        for i in range(2):
            await callback_query.bot.delete_message(
                callback_query.message.chat.id,
                callback_query.message.message_id - i
            )
    except:
        pass

    # Установим новое состояние чтобы кнопка Назад после показа отчета работал
    await MyStates.waiting_report_page_buttons.set()

    all_data = await state.get_data()
    # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
    chosen_worker = all_data['chosen_worker']
    chosen_term = all_data['term']

    # Хранит суммарное время присутствии
    total_presence_time = datetime.timedelta()

    # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
    chosen_days = []
    for i in range(int(chosen_term)):
        day = datetime.datetime.now().date() - datetime.timedelta(days=i)
        chosen_days.append(day)
    chosen_days.reverse()

    msg2_block_list = []
    for day in chosen_days:
        # Получим все in/out указанного дня: [(datetime.time(9, 6, 47), 'DeviceNo'), ...] или если ничего не найдено: []
        all_in_outs_one_day = sql_handler.get_all_in_outs_one_day(chosen_worker[0], day)

        in_device = config['device']['in_device']
        out_device = config['device']['out_device']

        in_time = 0
        # Тут храним время присутствия одного дня
        day_presence_time_delta = datetime.timedelta()
        mesg2 = str()
        # Если в all_in_outs_one_day есть 2 in и 2 out, значит составим 2 строки: "in | out\n in | out"
        for i in all_in_outs_one_day:
            # Если in_time пуст, значит мы ожидаем in_time.
            # !!! Но иногда после in может быть опять in если сотрудник при выходе не использовал faceid
            if not in_time:
                # Если получили in_device когда in_time пуст, значит всё в порядке
                if i[1] == in_device:
                    in_time = i[0]
            # Если in_time не пуст значит мы ожидаем out_time
            # !!! Но иногда после out может быть опять out если сотрудник при входе не использовал faceid
            else:
                # Если получили out_device когда in_time не пуст, значит всё в порядке
                if i[1] == out_device:
                    # Рассчитываем сколько часов был внутри и добавляем в суммарное время присутствии
                    in_time_delta = datetime.timedelta(hours=in_time.hour, minutes=in_time.minute, seconds=in_time.second)
                    out_time_delta = datetime.timedelta(hours=i[0].hour, minutes=i[0].minute, seconds=i[0].second)
                    presence_time_delta = out_time_delta - in_time_delta
                    day_presence_time_delta += presence_time_delta

                    # Онулируем in_time
                    in_time = 0
                # Если получили in_device когда in_time не пуст, значит после прихода опять идет приход и уход между
                # ними утерен из-за того что сотрудник не использовал faceid. В таком случаи мы не добавляем время в day_presence_time
                else:
                    # Запишем время в in_time чтобы в следующем цыкле не запустился "if not in_time"
                    in_time = i[0]

        # Время присутствия одного дня в общую время присутствия
        total_presence_time += day_presence_time_delta

        # Из дельта переводим на обычный время опозданий
        day_presence_time = datetime.datetime.min + day_presence_time_delta

        # Вместо "Время присутствия: 07:52" создаем "Время присутствия: 7 часов 52 минуты"
        hour = str(day_presence_time.hour)
        minute = str(day_presence_time.minute)
        if hour == '0':
            time = f"{minute} минут"
        else:
            time = f"{hour.lstrip('0')} часов {minute} минут"
        mesg6 = config['msg']['presence_time'] + ' ' + time


    # Из дельта переводим на обычный время общего присутствия
    presence_time = datetime.datetime.min + total_presence_time
    if presence_time.day == 1:
        total_presence = presence_time.strftime('%H:%M')
    else:
        day = int(presence_time.strftime('%d')) - 1
        total_presence = presence_time.strftime(f'{str(day)} дней %H:%M')
        total_presence = total_presence.lstrip('0')

    msg1 = config['msg']['you_chose'] + chosen_worker[1]
    msg2 = '\n\n'.join(msg2_block_list)
    # Создаем часть сообщения: "Итого время присутствия: 31:24"
    msg3 = config['msg']['total_presence_time'] + ' ' + total_presence

    msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3

    # Кнопки "Назад" и "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
    await callback_query.bot.send_message(
        callback_query.from_user.id,
        msg,
        reply_markup=button
    )
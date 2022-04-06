async def all_data_report_type_handler(callback_query: types.CallbackQuery, state: FSMContext):
    str_numbers = [str(i) for i in range(1, 31)]

    # Если нажал на кнопку Главное меню
    if message.text == config['msg']['main_menu']:
        # Удаляем 2 последние сообщения
        try:
            for i in range(3):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        await main_menu(message, state)
    # Если нажал на кнопку Назад вместо количество дней
    elif message.text == config['msg']['back']:
        # Удаляем 2 последние сообщения
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        await MyStates.waiting_for_worker_number.set()
        await report_handler(message, state=state)

    # Если отправил число от 1 до 30
    elif message.text.strip() in str_numbers:
        # Удаляем 2 последние сообщения
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        # Установим новое состояние чтобы кнопка Назад после показа
        await MyStates.waiting_report_page_buttons.set()

        all_data = await state.get_data()
        # Получаем информацию о выбранном пользователе: (ID, name, Who, chat_id)
        chosen_worker = all_data['chosen_worker']
        chosen_term = message.text.strip()

        # Суммарное время опозданий
        total_late_hours = datetime.timedelta()
        # Хранит суммарное время(раньше времени)
        total_early_lived_time = datetime.timedelta()
        # Количество дней который не пришел
        missed_days = 0

        # Получаем из таблицы "report" все информации об опоздании по id этого человека за выбранный срок:  [(id, user_id, date, comment, time), ...], где каждый элемент это отдельный день
        worker_report_list = sql_handler.get_data_by_term(chosen_worker[0], chosen_term)
        # Из worker_report_list создадим библиотеку: {date: (id, user_id, date, comment, time), ...}
        worker_report_dict = {}
        for day in worker_report_list:
            worker_report_dict[day[2]] = day

        # Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
        chosen_days = []
        for i in range(int(chosen_term)):
            day = datetime.datetime.now().date() - datetime.timedelta(days=i)
            chosen_days.append(day)
        chosen_days.reverse()

        msg2_block_list = []
        for day in chosen_days:
            # Если при процессе сбора данных одного дня выйдет ошибка, тогда в это число напишем что пустые строки: "Приход: | Уход: "
            if True:
                # Получаем время прихода и ухода указанной даты:  (in_time, out_time) или (in_time, False) или False
                in_out_time = sql_handler.get_user_in_out_history(chosen_worker[0], day)

                # Если данное число(date) выходной, тогда напишем: "🗓 Выходные\n Время прихода | Время ухода или просто "🗓 Выходные\n Не пришел"
                if str(datetime.date.isoweekday(day)) in config['time']['day_off']:
                    mesg1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                            config['msg']['three_lines'] + '</b>'
                    mesg2 = config['msg']['weekend']

                    # Если в in_out_time: False
                    if not in_out_time:
                        mesg3 = config['msg']['dont_came']
                    # Если в in_out_time: (in_time, out_time)
                    elif in_out_time[0] and in_out_time[1]:
                        mesg3_1 = config['msg']['came'] + ' ' + in_out_time[0].strftime('%H:%M')
                        mesg3_2 = config['msg']['leaved'] + ' ' + in_out_time[1].strftime('%H:%M')
                        mesg3 = mesg3_1 + '  <b>|</b>  ' + mesg3_2
                    # Если в in_out_time: (in_time, False)
                    else:
                        mesg3_1 = config['msg']['came'] + ' ' + in_out_time[0].strftime('%H:%M')
                        mesg3_2 = config['msg']['leaved']
                        mesg3 = mesg3_1 + '  <b>|</b>  ' + mesg3_2

                    # Составим сообщение
                    msg2 = mesg1 + '\n' + mesg2 + '\n' + mesg3

                    # Добавим созданную часть сообщения в msg2_block_list
                    msg2_block_list.append(msg2)

                    # Все что внизу пропустим
                    continue

                if day in worker_report_dict:
                    # Если он пришел с опозданием, составим об этом сообщение. worker_report_dict[day] хранит (id, user_id, date, comment, time)
                    if worker_report_dict[day][4]:
                        mesg1 = config['msg']['came'] + ' ' + str(worker_report_dict[day][4].strftime("%H:%M"))

                        # Определим на сколько часов и минут он опоздал
                        beginning_delta = datetime.timedelta(hours=int(config['time']['start_hour']),
                                                             minutes=int(config['time']['start_minute']))
                        came_time = worker_report_dict[day][4]
                        came_time_delta = datetime.timedelta(hours=came_time.hour, minutes=came_time.minute,
                                                             seconds=came_time.second)
                        late_time_in_seconds = came_time_delta - beginning_delta
                        late_time = (datetime.datetime.min + late_time_in_seconds).time()
                        late_time_str = late_time.strftime("%H:%M")
                        mesg3 = config['msg']['late_by'] + ' ' + late_time_str

                        # Прибавим время опоздания в суммарную delta
                        total_late_hours += late_time_in_seconds

                        if worker_report_dict[day][3]:
                            mesg4 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                        else:
                            mesg4 = config['msg']['reason']

                        if in_out_time:
                            # Получит (msg, timedelta): "Ушел в: 19:20" или "Ушел в: 15:20\n Ушел раньше чем: 3:40" или "Ушел в: Нету данных"
                            # timedelta: чтобы определить суммарное время
                            out_check = early_leave_check(in_out_time[1])
                            # Если есть время ухода и раннего ухода
                            mesg2_5 = out_check[0]
                            if '#' in mesg2_5:
                                ms = mesg2_5.split('#')
                                mesg2 = ms[0]
                                mesg5 = f"\n{ms[1]}"
                            else:
                                mesg2 = mesg2_5
                                mesg5 = ''
                            # Прибовляем время в суммарное время раннего ухода(если он ушел раньше. А если нет то timedelta = 0)
                            total_early_lived_time += out_check[1]
                        else:
                            mesg2 = config['msg']['leaved']
                            mesg5 = ''
                            total_early_lived_time += datetime.timedelta(0)

                        # Хранит в себе "Приход:\n Опоздал на:\n Причина:\n Ушел в:"
                        msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + '\n' + mesg3 + '\n' + mesg4 + mesg5
                    # Так как столбец time пуст, значит он не пришел
                    else:
                        mesg1 = config['msg']['did_not_come']

                        if worker_report_dict[day][3]:
                            mesg2 = config['msg']['reason'] + ' ' + worker_report_dict[day][3]
                        else:
                            mesg2 = config['msg']['reason']

                        msg2_2 = mesg1 + '\n' + mesg2
                        missed_days += 1
                # Если в таблице report не найден данный день, значит он пришел во время
                else:
                    if in_out_time:
                        mesg1 = config['msg']['came'] + ' ' + in_out_time[0].strftime("%H:%M")

                        # Получит (msg, timedelta): "Ушел в: 19:20" или "Ушел в: 15:20\n Ушел раньше чем: 3:40" или "Ушел в: Нету данных"
                        # timedelta: чтобы определить суммарное время
                        out_check = early_leave_check(in_out_time[1])
                        # Если есть время ухода и раннего ухода
                        mesg2_5 = out_check[0]
                        if '#' in mesg2_5:
                            ms = mesg2_5.split('#')
                            mesg2 = ms[0]
                            mesg3 = f"\n{ms[1]}"
                        else:
                            mesg2 = mesg2_5
                            mesg3 = ''
                        # Прибовляем время в суммарное время раннего ухода(если он ушел раньше. А если нет то timedelta = 0)
                        total_early_lived_time += out_check[1]
                    else:
                        mesg1 = config['msg']['came']

                        mesg2 = config['msg']['leaved']
                        mesg3 = ''
                        total_early_lived_time += datetime.timedelta(0)

                    # Хранит в себе "Приход:\n Ушел в: "
                    msg2_2 = mesg1 + '  <b>|</b>  ' + mesg2 + mesg3

                msg2_1 = '<b>📍 ' + config['msg']['three_lines'] + ' ' + str(day.strftime('%d.%m.%Y')) + ' ' + \
                         config['msg']['three_lines'] + '</b>'
                msg2 = msg2_1 + '\n' + msg2_2

                # Добавим созданную часть сообщения в msg2_block_list
                msg2_block_list.append(msg2)

        # Из дельта переводим на обычный время опозданий
        total_late_time = datetime.datetime.min + total_late_hours

        if total_late_time.day == 1:
            total_late = total_late_time.strftime('%H:%M')
        else:
            total_late = total_late_time.strftime('%d дней %H:%M')
        # Из дельта переводим на обычный время раннего ухода
        total_early_time = datetime.datetime.min + total_early_lived_time
        if total_early_time.day == 1:
            total_early = total_early_time.strftime('%H:%M')
        else:
            total_early = total_early_time.strftime('%d дней %H:%M')

        msg3_1 = config['msg']['total_late'] + ' ' + total_late
        msg3_2 = config['msg']['total_early'] + ' ' + total_early
        msg3_3 = config['msg']['total_missed'] + ' ' + str(missed_days)

        msg1 = config['msg']['you_chose'] + chosen_worker[1]
        msg2 = '\n\n'.join(msg2_block_list)
        msg3 = msg3_1 + '\n' + msg3_2 + '\n' + msg3_3
        msg = msg1 + '\n\n' + msg2 + '\n' + config['msg']['lines'] + '\n' + msg3

        # Кнопка "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
        await message.answer(
            msg,
            reply_markup=button
        )

    # Если отправил неправильное число или текст
    else:
        # Создадим кнопку "Главное меню"
        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
        # Удаляем 2 последние сообщения
        try:
            for i in range(2):
                await message.bot.delete_message(message.chat.id, message.message_id - i)
        except:
            pass

        msg = config['msg']['wrong_term']
        await message.answer(msg, reply_markup=button)

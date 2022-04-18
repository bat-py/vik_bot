async def excel_report_type_handler(callback_query_or_message, state: FSMContext):
    """
    Запустится после того как админ нажал на кнопку "📊 Отчет в excel" excel_report или вернулся из следующего меню
    :param callback_query_or_message:
    :param state:
    :return: Excel файл с отчетом 30 дней
    """
    try:
        message_id = callback_query_or_message.message.message_id
    except:
        message_id = callback_query_or_message.message_id

    try:
        for i in range(2):
            await callback_query_or_message.bot.delete_message(
                callback_query_or_message.from_user.id,
                message_id - i
            )
    except:
        pass

    # Меняем статус на waiting_for_term
    await MyStates.excel_waiting_for_term.set()

    # Создадим кнопку "Главное меню"
    button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])

    # Составим сообщения: Сколько дней хотите посмотреть (1-30 дней):
    msg = config['msg']['term']

    await callback_query_or_message.bot.send_message(
        callback_query_or_message.from_user.id,
        msg,
        reply_markup=button
    )



#async def excel_chosen_term_handler(message: types.Message, state: FSMContext):
    """
    Запуститься после того как пользователь в меню "📊 Отчет в excel" выбрал сколько дней отчета надо показать(1-31).
    :param message:
    :param state:
    :return:
    """
#    all_data = await state.get_data()
#    str_numbers = [str(i) for i in range(1, 31)]

    # Если нажал на кнопку Главное меню
#    if message.text == config['msg']['main_menu']:
        # Удаляем 2 последние сообщения
#        try:
#            for i in range(3):
#                await message.bot.delete_message(message.chat.id, message.message_id - i)
#        except:
#            pass

#        await main_menu(message, state)

    # Если отправил число от 1 до 30 или если вернулся назад из следующего меню
#    elif message.text.strip() in str_numbers:
        # Сохраним выбранный диапазон
        # await state.update_data(term=message.text.strip())

        # Меняем статус на excel_file_sended
#        await MyStates.excel_file_sended.set()

        # Создаем отчет в виде excel файла
#        excel_file = excel_creator(message.text.strip())

        # Удаляем 2 последние сообщения
#        try:
#            for i in range(2):
#                await message.bot.delete_message(
#                    message.chat.id,
#                    message.message_id - i
#                )
#        except:
#            pass

    # Если нажал на кнопку Назад вместо количество дней, тогда вернем report_menu
#    elif message.text == config['msg']['back']:
        # На всякие случаи аннулируем значение term
        # await state.update_data(term=None)

        # Удаляем 2 последние сообщения
#        try:
#            for i in range(2):
#                await message.bot.delete_message(
#                    message.chat.id,
#                    message.message_id - i
#                )
#        except:
#            pass

#        await report_menu(message, state)

    # Если отправил неправильное число или текст
#    else:
        # Создадим кнопку "Главное меню"
#        button = button_creators.reply_keyboard_creator([[config['msg']['back'], config['msg']['main_menu']]])
        # Удаляем 2 последние сообщения
#        try:
#            for i in range(2):
#                await message.bot.delete_message(message.chat.id, message.message_id - i)
#        except:
#            pass

#        msg = config['msg']['wrong_term']
#        await message.answer(msg, reply_markup=button)




    dp.register_message_handler(
        excel_chosen_term_handler,
        content_types=['text'],
        state=MyStates.excel_waiting_for_term
    )









    def get_chosen_days(self):
        """
        Составим список дней с объектами date() указанного периода для цикла: [..., datetime.datetime.now().date()]
        """
        chosen_days = []
        # chosen_days_str нужен чтобы даты можно было записать в excel файл в виде str
        chosen_days_str = []

        for i in range(int(self.term)):
            day = datetime.datetime.now().date() - datetime.timedelta(days=i)
            chosen_days.append(day)
            chosen_days_str.append(day.strftime('%d.%m.%Y'))

        chosen_days.reverse()
        chosen_days_str.reverse()

        return chosen_days, chosen_days_str

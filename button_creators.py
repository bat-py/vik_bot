from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import sql_handler


def inline_keyboard_creator(buttons_list, row_width=2):
    """
    Args:
        buttons_list: Получает такой массив: [ [ [button_name, callback_data]... ], [ []... ], [ []... ] ]
        row_width:

    Returns:

    """

    ready_buttons = InlineKeyboardMarkup(row_width=row_width)

    for i in buttons_list:
        ready_row = []
        for j in i:
            button = InlineKeyboardButton(j[0], callback_data=j[1])
            ready_row.append(button)

        ready_buttons.add(*ready_row)

    return ready_buttons


def reply_keyboard_creator(buttons_list, one_time=False):
    ready_buttons = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=one_time)

    for i in buttons_list:
        row = [KeyboardButton(j) for j in i]
        ready_buttons.add(*row)

    return ready_buttons


def hide_reply_buttons():
    hide_buttons = ReplyKeyboardRemove()

    return hide_buttons

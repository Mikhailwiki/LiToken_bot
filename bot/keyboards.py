from aiogram import types

kb_start = [
    [types.KeyboardButton(text='Баланс💵')],
    [types.KeyboardButton(text='Помощь📖')]
]

keyboard_start = types.ReplyKeyboardMarkup(keyboard=kb_start, resize_keyboard=True)
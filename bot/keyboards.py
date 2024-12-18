from aiogram import types

kb_balance = [
    [types.KeyboardButton(text='Баланс💵')]
]
keyboard_balance = types.ReplyKeyboardMarkup(keyboard=kb_balance, resize_keyboard=True)

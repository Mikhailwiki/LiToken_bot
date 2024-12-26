import os
import asyncio
import nest_asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, filters, F
from aiogram.utils import keyboard
from dotenv import load_dotenv
from db_manager import Database
from utils import make_qrcode, agree_with_num, get_table
from bot.keyboards import *
from bot.middlewares.trottling import ThrottlingMiddleware

load_dotenv()
nest_asyncio.apply()
TOKEN = os.getenv('BOT_TOKEN')
admins = os.getenv('ADMINS').split(',')

bot = Bot(token=TOKEN)
dp = Dispatcher()
logger = logging.getLogger(__name__)
database = Database('Users', os.getenv('USER_STORAGE_URL'), os.getenv('AWS_ACCESS_KEY_ID'),
                    os.getenv('AWS_SECRET_ACCESS_KEY'))


async def correct_user(message: types.Message) -> bool:
    """Проверяем зарегистрирован ли пользователь и обновляем username(если он был изменен)"""
    if not database.user_exist(message.from_user.id):
        await message.answer('Вы не зарегистрированы')
        return False
    if message.from_user.username is None:
        await message.answer('@username не должен быть пустым')
        return False
    if not database.is_username_correct(message.from_user.id, message.from_user.username):
        database.update_username(message.from_user.id, message.from_user.username)
    return True


@dp.message(filters.Command('start'))
async def cmd_start(message: types.Message):
    if message.from_user.username is None:
        await message.answer('@username не должен быть пустым')
        return
    if not database.user_exist(message.from_user.id):
        await register_user(message)
        await message.answer('Вы успешно зарегистрированы')
    if not database.is_username_correct(message.from_user.id, message.from_user.username):
        database.update_username(message.from_user.id, message.from_user.username)

    if message.text.split('_')[0].startswith('/start send'):
        await cmd_send(message)
    else:
        await message.reply('''
        Привет! В этом боте вы можете обмениваться токенами. Для получения подробной информации и инструкций по использованию бота, нажмите 'Помощь📖'.
        ''', reply_markup=keyboard_start)


@dp.message(F.text == 'Помощь📖')
async def cmd_help(message: types.Message):
    if not await correct_user(message):
        return
    await message.answer('''
Привет в это боте ты можешь обмениваться токенами посредством сканирования qr кодов 
/start - если нет кнопки баланса
/get <количество> для получения qr кода на запрос определенного количества монет, например:
/get 50
Если бот не отвечает - нужно подождать
delay = 2 сек''')


dp.message.register(cmd_help, filters.Command('help'))


@dp.message(filters.Command('get'))
async def cmd_get(message: types.Message):
    if not await correct_user(message):
        return
    data = message.text.split()
    if len(data) != 2 or not data[-1].isdigit():
        await message.answer('Неправильный ввод')
        return
    to_id = message.from_user.id
    amount = int(data[1])
    buf, url = await make_qrcode(to_id, amount)
    await message.answer_photo(
        photo=types.BufferedInputFile(
            file=buf.getvalue(),
            filename=f"{message.from_user.first_name}-profile.png",
        ), caption=f'QR code на получение {amount} {await agree_with_num("Токенов", amount)}\n{url}')


dp.message.register(cmd_get, filters.Command('get'))


@dp.message(F.text == 'Баланс💵')
async def show_balance(message: types.Message):
    if not await correct_user(message):
        return
    balance = database.get_balance(message.from_user.id)
    await message.answer(f'На вашем балансе {balance} {await agree_with_num("Токен", balance)}')


dp.message.register(show_balance, F.text == 'Баланс💵')


async def cmd_send(message: types.Message):
    if not await correct_user(message):
        return
    args = message.text.split('_')
    if len(args) != 3 or not args[1].isdigit() or not args[2].isdigit():
        await message.answer('Неверная ссылка')
        return
    to_id, amount = int(args[1]), int(args[2])
    id_ = message.from_user.id
    if not database.user_exist(to_id):
        await message.answer('Такого пользователя не существует')
        return
    confirm_builder = keyboard.InlineKeyboardBuilder().add(types.InlineKeyboardButton(
        text='Подтвердить',
        callback_data=f'confirm_{id_}_{to_id}_{amount}')
    )
    await message.answer(
        f'Вы точно хотите отправить пользователю @{database.get_username(to_id)} {amount} {await agree_with_num("Токенов", int(amount))}',
        reply_markup=confirm_builder.as_markup()
    )


@dp.callback_query(F.data.startswith('confirm_'))
async def send_tokens(callback: types.CallbackQuery):
    args = callback.data.split('_')
    id_ = int(args[1])
    to_id = int(args[2])
    amount = int(args[3])
    if database.transaction(id_, to_id, amount):
        await callback.message.edit_text(
            f'Пользователю @{database.get_username(to_id)} отправлено {amount} {await agree_with_num("Токенов", int(amount))}')
        await bot.send_message(chat_id=to_id,
                               text=f'Получено {amount} {await agree_with_num("Токенов", int(amount))} от @{callback.from_user.username}')
    else:
        await callback.message.edit_text('Недостаточно средств')


dp.message.register(send_tokens, F.data.startswith('confirm_'))


async def register_user(message: types.Message):
    """Добавляем id чата, username и стартовое количество токенов(500)"""
    username = message.from_user.username
    chat_id = message.from_user.id
    coins = 500
    database.add_user(chat_id, coins, username)


@dp.message(filters.Command('add'))
async def cmd_add(message: types.Message):
    if not await correct_user(message):
        return
    data = message.text.split()
    if len(data) != 3 or not data[1].isdigit():
        await message.answer('Неправильный ввод')
        return
    if message.from_user.username in admins:
        amount = int(data[1])
        username = data[-1]
        id_ = database.get_chat_id(username)
        if not database.user_exist(id_):
            await message.answer('Такого пользователя не существует')
            return
        database.add_coins(id_, amount)
        await message.answer(
            f'Пользователю @{username} успешно добавлено {amount} {await agree_with_num("Токенов", int(amount))}')
    else:
        await message.answer('У вас нет прав для этой команды')


dp.message.register(cmd_add, filters.Command('add'))


@dp.message(filters.Command('sub'))
async def cmd_sub(message: types.Message):
    if not await correct_user(message):
        return
    data = message.text.split()
    if len(data) != 3 or not data[1].isdigit():
        await message.answer('Неправильный ввод')
        return
    if message.from_user.username in admins:
        amount = int(data[1])
        username = data[-1]
        id_ = database.get_chat_id(username)
        if not database.user_exist(id_):
            await message.answer('Такого пользователя не существует')
            return
        if database.get_transaction_verdict(id_, amount):
            database.subtract_coins(id_, amount)
            cur_balance = amount
        else:
            cur_balance = database.get_balance(id_)
            database.subtract_coins(id_, cur_balance)
            await message.answer(
                f'Вычитаемый баланс превышает действительный. Баланс обнулен'
            )
        await message.answer(
            f'У пользователя @{username} успешно вычтено {cur_balance} {await agree_with_num("Токенов", int(amount))}')
    else:
        await message.answer('У вас нет прав для этой команды')


dp.message.register(cmd_sub, filters.Command('sub'))


@dp.message(filters.Command('table'))
async def cmd_table(message: types.Message):
    if not await correct_user(message):
        return
    if message.from_user.username not in admins:
        await message.answer('У вас нет прав для этой команды')
        return

    excel_file = await get_table(database.get_data())
    await message.answer_document(
        document=types.BufferedInputFile(excel_file.read(), filename='пользователи и балансы.xlsx'))
    excel_file.close()


dp.message.register(cmd_table, filters.Command('table'))


async def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    dp.message.middleware(ThrottlingMiddleware())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('Exit')

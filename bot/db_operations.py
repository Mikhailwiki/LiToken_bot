import sqlite3
from typing import NoReturn, Union


class Database:
    def __init__(self, db: str):
        self.conn = sqlite3.connect(db)
        self.cur = self.conn.cursor()

    async def user_exist(self, chat_id: int) -> tuple[int, int, str]:
        return self.cur.execute('''SELECT * FROM users WHERE chat_id = ?''', (chat_id,)).fetchone()

    async def add_user(self, chat_id: int, coins: int, username: str) -> NoReturn:
        try:
            self.cur.execute('''INSERT INTO users(chat_id, coins, username) VALUES (?, ?, ?)''',
                         (chat_id, coins, username))
            self.conn.commit()
        except Exception as e:
            print('add_user')
            print(f'Error {e} with values {chat_id} {username} {coins}')

    async def is_username_correct(self, chat_id: int, username: str) -> bool:
        try:
            current_username = self.cur.execute('''SELECT username FROM users WHERE chat_id = ?''', (chat_id,)).fetchone()
            if current_username and current_username[0] == username:
                return True
            else:
                return False
        except Exception as e:
            print('is_username_correct')
            print(f'Error {e} with values {chat_id} {username}')

    async def update_username(self, chat_id: int, new_username: str) -> None:
        try:
            self.cur.execute('''UPDATE users SET username = ? WHERE chat_id = ?''', (new_username, chat_id))
            self.conn.commit()
        except Exception as e:
            print('update_username')
            print(f'Error {e} with values {chat_id} {new_username}')

    async def add_coins(self, chat_id: int, amount: int) -> None:
        try:
            coins = self.cur.execute('''SELECT coins FROM users WHERE chat_id = ?''', (chat_id,)).fetchone()
            self.cur.execute('''UPDATE users SET coins = ? WHERE chat_id = ?''', (coins[0] + amount, chat_id))
            self.conn.commit()
        except Exception as e:
            print('add_coins')
            print(f'Error {e} with values {chat_id} {amount}')

    async def subtract_coins(self, chat_id: int, amount: int) -> None:
        try:
            coins = self.cur.execute(f'''SELECT coins FROM users WHERE chat_id = ?''', (chat_id,)).fetchone()
            self.cur.execute('''UPDATE users SET coins = ? WHERE chat_id = ?''', (coins[0] - amount, chat_id))
            self.conn.commit()
        except Exception as e:
            print('subtract_coins')
            print(f'Error {e} with values {chat_id} {amount}')

    async def get_transaction_verdict(self, chat_id: int, amount: int) -> Union[int, None]:
        """Достаточно ли коинов на балансе отправителя"""
        try:
            coins = self.cur.execute(f'''SELECT coins FROM users WHERE chat_id = ?''', (chat_id,)).fetchone()
            if coins[0] < amount:
                return False
            return True
        except TypeError:
            return None
        except Exception as e:
            print('get_transaction_verdict')
            print(f'Error {e} with values {chat_id} {amount}')

    async def transaction(self, chat_id: int, to_chat_id: int, amount: int) -> bool:
        try:
            if await self.get_transaction_verdict(chat_id, amount):
                await self.add_coins(to_chat_id, amount)
                await self.subtract_coins(chat_id, amount)
                return True
            else:
                return False
        except Exception as e:
            print('transaction')
            print(f'Error {e} with values {chat_id} {to_chat_id} {amount}')

    async def get_username(self, chat_id: int) -> Union[str, None]:
        try:
            username = self.cur.execute('''SELECT username FROM users WHERE chat_id = ?''', (chat_id,)).fetchone()[0]
            return username
        except TypeError:
            return None
        except Exception as e:
            print('get_username')
            print(f'Error {e} with values {chat_id}')

    async def get_chat_id(self, username: str) -> Union[int, None]:
        try:
            chat_id = self.cur.execute('''SELECT chat_id FROM users WHERE username = ?''', (username,)).fetchone()[0]
            return chat_id
        except TypeError:
            return None
        except Exception as e:
            print('get_chat_id')
            print(f'Error {e} with values {username}')

    async def get_balance(self, chat_id: int) -> Union[int, None]:
        try:
            balance = self.cur.execute('''SELECT coins FROM users WHERE chat_id = ?''',(chat_id,)).fetchone()[0]
            return balance
        except TypeError:
            return None
        except Exception as e:
            print('get_balance')
            print(f'Error {e} with values {chat_id}')

    async def get_data(self) -> list[tuple[int, str]]:
        """Возвращает excel таблицу со всеми данными"""
        try:
            table = self.cur.execute('''SELECT coins, username FROM users''').fetchall()
            return table
        except Exception as e:
            print('get_table')
            print(f'Error {e}')

    def print_all(self) -> NoReturn:
        """Выводит все данные из таблицы users"""
        print(self.cur.execute('''SELECT * FROM users''').fetchall())

    def clear_all(self) -> NoReturn:
        """Очищает все данные из таблицы users"""
        self.cur.execute('''DELETE FROM users''')
        self.conn.commit()


db = Database('../data/users.db')
db.print_all()
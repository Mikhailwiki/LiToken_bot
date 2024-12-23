import boto3
from botocore.exceptions import ClientError

from typing import Union, List, Tuple


class Database:
    def __init__(self, table_name: str, endpoint_url: str, access_key: str, secret_key: str):
        """
        Инициализация подключения к DynamoDB.
        :param table_name: Имя таблицы в DynamoDB.
        :param access_key: AWS Access Key ID.
        :param secret_key: AWS Secret Access Key.
        """
        self.table_name = table_name
        self.dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=endpoint_url,
            region_name='us-east-1',
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.table = self.dynamodb.Table(table_name)

    def user_exist(self, chat_id: int) -> Union[dict, None]:
        """
        Проверяет, существует ли пользователь с указанным chat_id.
        :param chat_id: Уникальный идентификатор пользователя.
        :return: Данные пользователя или None, если пользователь не найден.
        """
        try:
            response = self.table.get_item(Key={'chat_id': chat_id})
            return response.get('Item')
        except ClientError as e:
            print(f"Error in user_exist: {e}")
            return None

    def add_user(self, chat_id: int, coins: int, username: str) -> bool:
        """
        Добавляет нового пользователя в таблицу.
        :param chat_id: Уникальный идентификатор пользователя.
        :param coins: Количество монет.
        :param username: Имя пользователя.
        :return: True, если операция успешна, иначе False.
        """
        try:
            self.table.put_item(
                Item={
                    'chat_id': chat_id,
                    'coins': coins,
                    'username': username
                }
            )
            return True
        except ClientError as e:
            print(f"Error in add_user: {e}")
            return False

    def is_username_correct(self, chat_id: int, username: str) -> bool:
        """
        Проверяет, совпадает ли текущее имя пользователя с указанным.
        :param chat_id: Уникальный идентификатор пользователя.
        :param username: Имя пользователя для проверки.
        :return: True, если имя совпадает, иначе False.
        """
        try:
            user = self.user_exist(chat_id)
            return user and user.get('username') == username
        except ClientError as e:
            print(f"Error in is_username_correct: {e}")
            return False

    def update_username(self, chat_id: int, new_username: str) -> bool:
        """
        Обновляет имя пользователя.
        :param chat_id: Уникальный идентификатор пользователя.
        :param new_username: Новое имя пользователя.
        :return: True, если операция успешна, иначе False.
        """
        try:
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression='SET username = :username',
                ExpressionAttributeValues={':username': new_username}
            )
            return True
        except ClientError as e:
            print(f"Error in update_username: {e}")
            return False

    def add_coins(self, chat_id: int, amount: int) -> bool:
        """
        Добавляет монеты к балансу пользователя.
        :param chat_id: Уникальный идентификатор пользователя.
        :param amount: Количество монет для добавления.
        :return: True, если операция успешна, иначе False.
        """
        try:
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression='SET coins = coins + :amount',
                ExpressionAttributeValues={':amount': amount}
            )
            return True
        except ClientError as e:
            print(f"Error in add_coins: {e}")
            return False

    def subtract_coins(self, chat_id: int, amount: int) -> bool:
        """
        Вычитает монеты из баланса пользователя.
        :param chat_id: Уникальный идентификатор пользователя.
        :param amount: Количество монет для вычитания.
        :return: True, если операция успешна, иначе False.
        """
        try:
            self.table.update_item(
                Key={'chat_id': chat_id},
                UpdateExpression='SET coins = coins - :amount',
                ExpressionAttributeValues={':amount': amount}
            )
            return True
        except ClientError as e:
            print(f"Error in subtract_coins: {e}")
            return False

    def get_transaction_verdict(self, chat_id: int, amount: int) -> Union[bool, None]:
        """
        Проверяет, достаточно ли монет на балансе пользователя для транзакции.
        :param chat_id: Уникальный идентификатор пользователя.
        :param amount: Количество монет для проверки.
        :return: True, если баланс достаточен, иначе False или None в случае ошибки.
        """
        try:
            user = self.user_exist(chat_id)
            if user and user.get('coins') >= amount:
                return True
            return False
        except ClientError as e:
            print(f"Error in get_transaction_verdict: {e}")
            return None

    def transaction(self, chat_id: int, to_chat_id: int, amount: int) -> bool:
        """
        Выполняет транзакцию между двумя пользователями.
        :param chat_id: Уникальный идентификатор отправителя.
        :param to_chat_id: Уникальный идентификатор получателя.
        :param amount: Количество монет для перевода.
        :return: True, если транзакция успешна, иначе False.
        """
        try:
            if self.get_transaction_verdict(chat_id, amount):
                self.subtract_coins(chat_id, amount)
                self.add_coins(to_chat_id, amount)
                return True
            return False
        except ClientError as e:
            print(f"Error in transaction: {e}")
            return False

    def get_username(self, chat_id: int) -> Union[str, None]:
        """
        Получает имя пользователя по chat_id.
        :param chat_id: Уникальный идентификатор пользователя.
        :return: Имя пользователя или None, если пользователь не найден.
        """
        try:
            user = self.user_exist(chat_id)
            return user.get('username') if user else None
        except ClientError as e:
            print(f"Error in get_username: {e}")
            return None

    def get_chat_id(self, username: str) -> Union[int, None]:
        """
        Получает chat_id по имени пользователя.
        :param username: Имя пользователя.
        :return: chat_id или None, если пользователь не найден.
        """
        try:
            response = self.table.scan(FilterExpression='username = :username',
                                       ExpressionAttributeValues={':username': username})
            items = response.get('Items')
            return items[0].get('chat_id') if items else None
        except ClientError as e:
            print(f"Error in get_chat_id: {e}")
            return None

    def get_balance(self, chat_id: int) -> Union[int, None]:
        """
        Получает баланс пользователя по chat_id.
        :param chat_id: Уникальный идентификатор пользователя.
        :return: Баланс или None, если пользователь не найден.
        """
        try:
            user = self.user_exist(chat_id)
            return user.get('coins') if user else None
        except ClientError as e:
            print(f"Error in get_balance: {e}")
            return None

    def get_data(self) -> List[Tuple[int, str]]:
        """
        Возвращает все данные из таблицы.
        :return: Список кортежей с данными (coins, username).
        """
        try:
            response = self.table.scan()
            items = response.get('Items')
            return [(item['coins'], item['username']) for item in items]
        except ClientError as e:
            print(f"Error in get_data: {e}")
            return []

    def print_all(self):
        """
        Выводит все данные из таблицы.
        """
        try:
            response = self.table.scan()
            items = response.get('Items')
            print(items)
        except ClientError as e:
            print(f"Error in print_all: {e}")

    def clear_all(self):
        """
        Удаляет все данные из таблицы.
        """
        try:
            response = self.table.scan()
            items = response.get('Items')
            for item in items:
                self.table.delete_item(Key={'chat_id': item['chat_id']})
        except ClientError as e:
            print(f"Error in clear_all: {e}")

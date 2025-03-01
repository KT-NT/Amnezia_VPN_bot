import sqlite3
from datetime import datetime, timedelta

class Database:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        """Создание таблиц в базе данных, если они не существуют."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 0
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS configs (
                config_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                port INTEGER,
                end_date TEXT,
                public_key TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
        ''')

        self.connection.commit()

    def user_exists(self, user_id):
        """Проверяет, существует ли пользователь в базе данных."""
        self.cursor.execute('SELECT user_id FROM users WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone() is not None

    def add_user(self, user_id):
        """Добавляет нового пользователя в базу данных."""
        if not self.user_exists(user_id):
            self.cursor.execute('INSERT INTO users (user_id) VALUES (?)', (user_id,))
            self.connection.commit()

    def update_balance(self, user_id, amount):
        """Обновляет баланс пользователя."""
        self.cursor.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, user_id))
        self.connection.commit()

    def get_balance(self, user_id):
        """Возвращает баланс пользователя."""
        self.cursor.execute('SELECT balance FROM users WHERE user_id = ?', (user_id,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def add_config(self, user_id, duration, port, public_key=None):
        """Добавляет новую конфигурацию VPN для пользователя."""
        end_date = (datetime.now() + timedelta(days=30 * duration)).isoformat()
        self.cursor.execute('''
            INSERT INTO configs (user_id, port, end_date, public_key)
            VALUES (?, ?, ?, ?)
        ''', (user_id, port, end_date, public_key))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_config(self, config_id):
        """Возвращает конфигурацию по её ID."""
        self.cursor.execute('''
            SELECT config_id, user_id, port, end_date, public_key
            FROM configs
            WHERE config_id = ?
        ''', (config_id,))
        result = self.cursor.fetchone()
        if result:
            return {
                'config_id': result[0],
                'user_id': result[1],
                'port': result[2],
                'end_date': result[3],
                'public_key': result[4]
            }
        return None

    def get_configs(self, user_id):
        """Возвращает все конфигурации пользователя."""
        self.cursor.execute('''
            SELECT config_id, port, end_date
            FROM configs
            WHERE user_id = ?
        ''', (user_id,))
        return [{
            'config_id': row[0],
            'port': row[1],
            'end_date': row[2]
        } for row in self.cursor.fetchall()]

    def delete_config(self, config_id):
        """Удаляет конфигурацию по её ID."""
        self.cursor.execute('DELETE FROM configs WHERE config_id = ?', (config_id,))
        self.connection.commit()

    def extend_config(self, config_id, duration):
        """Продлевает срок действия конфигурации."""
        self.cursor.execute('''
            UPDATE configs
            SET end_date = ?
            WHERE config_id = ?
        ''', ((datetime.now() + timedelta(days=30 * duration)).isoformat(), config_id))
        self.connection.commit()

    def close(self):
        """Закрывает соединение с базой данных."""
        self.connection.close()

import aiosqlite
import logging
from datetime import datetime
from typing import Optional, List
from .models import User, Driver, Document, BotSetting, Transaction, AdminAction
from config import settings

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = settings.DATABASE_PATH
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.create_tables()
        logger.info("Database connected successfully")

    async def close(self):
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")

    async def create_tables(self):
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                phone TEXT,
                language TEXT DEFAULT 'uz',
                role TEXT DEFAULT 'driver',
                registration_status TEXT DEFAULT 'not_started',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS drivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                yandex_driver_id TEXT,
                name TEXT,
                callsign TEXT,
                car_model TEXT,
                balance REAL DEFAULT 0.0,
                last_trip_date TIMESTAMP,
                last_trip_sum REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                last_sync TIMESTAMP,
                last_manual_sync TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                document_type TEXT NOT NULL,
                file_id TEXT NOT NULL,
                message_id INTEGER,
                chat_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                transaction_type TEXT DEFAULT 'withdrawal',
                status TEXT DEFAULT 'pending',
                card_number TEXT,
                payme_transaction_id TEXT,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        ''')

        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER NOT NULL,
                action_type TEXT NOT NULL,
                target_id INTEGER NOT NULL,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        await self.conn.commit()
        logger.info("Database tables created successfully")

    async def get_user(self, telegram_id: int) -> Optional[User]:
        cursor = await self.conn.execute(
            'SELECT * FROM users WHERE telegram_id = ?',
            (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            return User(**dict(row))
        return None

    async def create_user(self, user: User) -> User:
        await self.conn.execute(
            '''INSERT INTO users (telegram_id, phone, language, role, registration_status)
               VALUES (?, ?, ?, ?, ?)''',
            (user.telegram_id, user.phone, user.language, user.role, user.registration_status)
        )
        await self.conn.commit()
        return await self.get_user(user.telegram_id)

    async def update_user(self, telegram_id: int, **kwargs):
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [telegram_id]
        await self.conn.execute(
            f'UPDATE users SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?',
            values
        )
        await self.conn.commit()

    async def get_driver(self, telegram_id: int) -> Optional[Driver]:
        cursor = await self.conn.execute(
            'SELECT * FROM drivers WHERE telegram_id = ?',
            (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Driver(**dict(row))
        return None

    async def get_driver_by_yandex_id(self, yandex_driver_id: str) -> Optional[Driver]:
        cursor = await self.conn.execute(
            'SELECT * FROM drivers WHERE yandex_driver_id = ?',
            (yandex_driver_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Driver(**dict(row))
        return None

    async def create_driver(self, driver: Driver) -> Driver:
        cursor = await self.conn.execute(
            '''INSERT INTO drivers (telegram_id, yandex_driver_id, name, callsign, car_model, balance)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (driver.telegram_id, driver.yandex_driver_id, driver.name,
             driver.callsign, driver.car_model, driver.balance)
        )
        await self.conn.commit()
        return await self.get_driver(driver.telegram_id)

    async def update_driver(self, telegram_id: int, **kwargs):
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [telegram_id]
        await self.conn.execute(
            f'UPDATE drivers SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?',
            values
        )
        await self.conn.commit()

    async def get_all_drivers(self) -> List[Driver]:
        cursor = await self.conn.execute('SELECT * FROM drivers')
        rows = await cursor.fetchall()
        return [Driver(**dict(row)) for row in rows]

    async def get_active_drivers(self) -> List[Driver]:
        cursor = await self.conn.execute('SELECT * FROM drivers WHERE is_active = 1')
        rows = await cursor.fetchall()
        return [Driver(**dict(row)) for row in rows]

    async def get_inactive_drivers(self, days: int = 7) -> List[Driver]:
        cursor = await self.conn.execute(
            '''SELECT * FROM drivers
               WHERE last_trip_date IS NULL
               OR datetime(last_trip_date) < datetime('now', '-' || ? || ' days')''',
            (days,)
        )
        rows = await cursor.fetchall()
        return [Driver(**dict(row)) for row in rows]

    async def save_document(self, doc: Document) -> Document:
        cursor = await self.conn.execute(
            '''INSERT INTO documents (telegram_id, document_type, file_id, message_id, chat_id)
               VALUES (?, ?, ?, ?, ?)''',
            (doc.telegram_id, doc.document_type, doc.file_id, doc.message_id, doc.chat_id)
        )
        await self.conn.commit()
        doc.id = cursor.lastrowid
        return doc

    async def get_documents(self, telegram_id: int) -> List[Document]:
        cursor = await self.conn.execute(
            'SELECT * FROM documents WHERE telegram_id = ? ORDER BY created_at',
            (telegram_id,)
        )
        rows = await cursor.fetchall()
        return [Document(**dict(row)) for row in rows]

    async def delete_documents(self, telegram_id: int):
        await self.conn.execute(
            'DELETE FROM documents WHERE telegram_id = ?',
            (telegram_id,)
        )
        await self.conn.commit()

    async def get_setting(self, key: str) -> Optional[str]:
        cursor = await self.conn.execute(
            'SELECT value FROM settings WHERE key = ?',
            (key,)
        )
        row = await cursor.fetchone()
        return row['value'] if row else None

    async def set_setting(self, key: str, value: str):
        await self.conn.execute(
            '''INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP''',
            (key, value, value)
        )
        await self.conn.commit()

    async def get_all_settings(self) -> dict:
        cursor = await self.conn.execute('SELECT key, value FROM settings')
        rows = await cursor.fetchall()
        return {row['key']: row['value'] for row in rows}

    async def get_admin_ids(self) -> List[int]:
        value = await self.get_setting('admin_ids')
        if value:
            return [int(id.strip()) for id in value.split(',') if id.strip()]
        return []

    async def set_admin_ids(self, ids: List[int]):
        await self.set_setting('admin_ids', ','.join(map(str, ids)))

    async def create_transaction(self, transaction: Transaction) -> Transaction:
        cursor = await self.conn.execute(
            '''INSERT INTO transactions (telegram_id, amount, transaction_type, status, card_number)
               VALUES (?, ?, ?, ?, ?)''',
            (transaction.telegram_id, transaction.amount, transaction.transaction_type,
             transaction.status, transaction.card_number)
        )
        await self.conn.commit()
        transaction.id = cursor.lastrowid
        return transaction

    async def update_transaction(self, transaction_id: int, **kwargs):
        fields = ', '.join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [transaction_id]
        await self.conn.execute(
            f'UPDATE transactions SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            values
        )
        await self.conn.commit()

    async def get_transaction(self, transaction_id: int) -> Optional[Transaction]:
        cursor = await self.conn.execute(
            'SELECT * FROM transactions WHERE id = ?',
            (transaction_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Transaction(**dict(row))
        return None

    async def get_all_transactions(self) -> List[Transaction]:
        cursor = await self.conn.execute(
            'SELECT * FROM transactions ORDER BY created_at DESC'
        )
        rows = await cursor.fetchall()
        return [Transaction(**dict(row)) for row in rows]

    async def log_admin_action(self, action: AdminAction):
        await self.conn.execute(
            '''INSERT INTO admin_actions (admin_id, action_type, target_id, reason)
               VALUES (?, ?, ?, ?)''',
            (action.admin_id, action.action_type, action.target_id, action.reason)
        )
        await self.conn.commit()

    async def get_user_count(self) -> int:
        cursor = await self.conn.execute('SELECT COUNT(*) as count FROM users')
        row = await cursor.fetchone()
        return row['count']

    async def get_driver_count(self) -> int:
        cursor = await self.conn.execute('SELECT COUNT(*) as count FROM drivers')
        row = await cursor.fetchone()
        return row['count']

    async def get_pending_registrations_count(self) -> int:
        cursor = await self.conn.execute(
            "SELECT COUNT(*) as count FROM users WHERE registration_status = 'pending'"
        )
        row = await cursor.fetchone()
        return row['count']

    async def get_driver_by_yandex_id(self, yandex_driver_id: str) -> Optional[Driver]:
        cursor = await self.conn.execute(
            'SELECT * FROM drivers WHERE yandex_driver_id = ?',
            (yandex_driver_id,)
        )
        row = await cursor.fetchone()
        if row:
            return Driver(**dict(row))
        return None

    async def search_drivers(self, query: str) -> List[Driver]:
        q = f'%{query}%'
        cursor = await self.conn.execute(
            '''SELECT * FROM drivers WHERE
               name LIKE ? OR
               callsign LIKE ? OR
               car_model LIKE ? OR
               yandex_driver_id LIKE ?
               LIMIT 20''',
            (q, q, q, q)
        )
        rows = await cursor.fetchall()
        return [Driver(**dict(row)) for row in rows]

    async def backup_database(self, backup_path: str):
        backup_conn = await aiosqlite.connect(backup_path)
        await self.conn.backup(backup_conn)
        await backup_conn.close()
        logger.info(f"Database backed up to {backup_path}")

import sqlite3
import logging
from datetime import datetime, timedelta
from contextlib import contextmanager

# Настраиваем базовое логирование, чтобы видеть, что происходит в базе
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class DatabaseManager:
    """
    Класс для управления базой данных SQLite, содержащей информацию
    о заказах из чатов и сборочных заданиях.
    """

    def __init__(self, db_path="orders.db"):
        self.db_path = db_path
        # Создаем обе таблицы при инициализации объекта
        self._create_tables()

    @contextmanager
    def _get_cursor(self):
        """Контекстный менеджер для безопасной работы с БД."""
        try:
            conn = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            )
            conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
            cursor = conn.cursor()
            yield cursor
        except sqlite3.Error as e:
            logging.error(f"Ошибка подключения к БД: {e}")
            if "conn" in locals() and conn:
                conn.rollback()
            raise
        else:
            conn.commit()
        finally:
            if "conn" in locals() and conn:
                conn.close()

    def _create_tables(self):
        """Создает таблицы, если они не существуют."""
        try:
            with self._get_cursor() as cursor:
                # 1. Таблица для заказов, связанных с чатами (ключ - gNumber)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS orders (
                        gNumber TEXT PRIMARY KEY,
                        nmID INTEGER,
                        client_name TEXT,
                        order_date TEXT,
                        chat_id TEXT,
                        status TEXT DEFAULT 'new',
                        photo_received BOOLEAN DEFAULT FALSE,
                        is_empty BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
                # 2. Таблица для сборочных заданий (ключ - rid)
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS assembly_tasks (
                        rid TEXT PRIMARY KEY,
                        orderUid TEXT,
                        nmId INTEGER,
                        article TEXT,
                        price REAL,
                        status TEXT DEFAULT 'new',
                        createdAt TEXT,
                        processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                    """
                )
            logging.info("База данных и таблицы успешно инициализированы.")
        except sqlite3.Error as e:
            logging.critical(f"Не удалось создать таблицы в БД: {e}")
            raise

    # --- Методы для таблицы 'orders' (заказы из чатов) ---

    def add_order(self, gNumber, nmID, client_name, order_date, chat_id):
        """Добавляет или обновляет заказ в таблице 'orders'."""
        with self._get_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO orders (gNumber, nmID, client_name, order_date, chat_id, last_updated)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(gNumber) DO UPDATE SET
                    nmID=excluded.nmID, client_name=excluded.client_name,
                    order_date=excluded.order_date, chat_id=excluded.chat_id,
                    last_updated=excluded.last_updated;
                """,
                (gNumber, nmID, client_name, order_date, chat_id, datetime.now()),
            )
        logging.info(f"Заказ (gNumber: {gNumber}) добавлен/обновлен в базе.")

    def get_order(self, gNumber):
        """Получает данные заказа по gNumber."""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM orders WHERE gNumber=?", (gNumber,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def update_order_chat_id(self, gNumber, chat_id):
        """Обновляет chat_id для существующего заказа по gNumber."""
        with self._get_cursor() as cursor:
            cursor.execute(
                "UPDATE orders SET chat_id = ?, last_updated = CURRENT_TIMESTAMP WHERE gNumber = ?",
                (chat_id, gNumber),
            )
        logging.info(f"Для заказа {gNumber} установлен chat_id: {chat_id}")

    def get_empty_orders(self, hours=24):
        """Получает заказы, для которых не получено фото в течение `hours` часов."""
        time_threshold = datetime.now() - timedelta(hours=hours)
        with self._get_cursor() as cursor:
            cursor.execute(
                "SELECT gNumber FROM orders WHERE photo_received = FALSE AND is_empty = FALSE AND created_at < ?",
                (time_threshold,),
            )
            return [row["gNumber"] for row in cursor.fetchall()]

    def mark_as_empty(self, gNumber):
        """Помечает заказ как 'empty'."""
        with self._get_cursor() as cursor:
            cursor.execute(
                "UPDATE orders SET is_empty = TRUE, status = 'empty', last_updated = CURRENT_TIMESTAMP WHERE gNumber = ?",
                (gNumber,),
            )
        logging.info(f"Заказ {gNumber} помечен как 'empty'.")

    def get_statistics(self):
        """Получение статистики по таблице 'orders'."""
        try:
            with self._get_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN status = 'new' THEN 1 ELSE 0 END) as active,
                        SUM(CASE WHEN status != 'new' THEN 1 ELSE 0 END) as processed
                    FROM orders
                """
                )
                stats = cursor.fetchone()
                return (
                    dict(stats) if stats else {"total": 0, "active": 0, "processed": 0}
                )
        except sqlite3.Error as e:
            logging.error(f"Ошибка получения статистики по заказам: {e}")
            return {"total": 0, "active": 0, "processed": 0}

    # --- Методы для таблицы 'assembly_tasks' (сборочные задания) ---

    def add_assembly_task(self, rid, orderUid, nmId, article, price, createdAt):
        """Добавляет новое сборочное задание. Игнорирует, если rid уже существует."""
        with self._get_cursor() as cursor:
            cursor.execute(
                "INSERT OR IGNORE INTO assembly_tasks (rid, orderUid, nmId, article, price, createdAt, processed_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (rid, orderUid, nmId, article, price, createdAt, datetime.now()),
            )
        logging.info(f"Сборочное задание (rid: {rid}) обработано и добавлено в базу.")

    def get_task_by_rid(self, rid):
        """Получает данные сборочного задания по rid."""
        with self._get_cursor() as cursor:
            cursor.execute("SELECT * FROM assembly_tasks WHERE rid=?", (rid,))
            row = cursor.fetchone()
            return dict(row) if row else None

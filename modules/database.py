import logging
import sqlite3


class DatabaseManager:
    def __init__(self, db_path="wb_orders.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS assembly_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rid TEXT UNIQUE,
                orderUid TEXT,
                nmId INTEGER,
                article TEXT,
                price REAL,
                createdAt TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                moved_to_empty INTEGER DEFAULT 0
            )
        """
        )
        self.conn.commit()
        logging.info("Таблица assembly_tasks создана или уже существует")

    def add_assembly_task(
        self, rid, orderUid, nmId, article, price, createdAt, status="new"
    ):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO assembly_tasks
                (rid, orderUid, nmId, article, price, createdAt, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (rid, orderUid, nmId, article, price, createdAt, status),
            )
            self.conn.commit()
            logging.info(
                f"Сборочное задание (rid: {rid}) обработано и добавлено в базу."
            )
            return True
        except Exception as e:
            logging.error(f"Ошибка добавления задания в БД: {e}")
            return False

    def get_task_by_rid(self, rid):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM assembly_tasks WHERE rid = ?", (rid,))
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка поиска задания по rid: {e}")
            return None

    def get_task_by_order_uid(self, order_uid):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT * FROM assembly_tasks WHERE orderUid = ?", (order_uid,)
            )
            result = cursor.fetchone()
            if result:
                logging.info(
                    f"Найден заказ по orderUid: {order_uid} -> {result[1]}"
                )
            return result
        except Exception as e:
            logging.error(f"Ошибка поиска задания по orderUid: {e}")
            return None

    def debug_database(self):
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM assembly_tasks ORDER BY id DESC LIMIT 5")
            recent_tasks = cursor.fetchall()

            logging.info("ДИАГНОСТИКА БАЗЫ ДАННЫХ:")
            for task in recent_tasks:
                logging.info(f"   Запись: {task}")
        except Exception as e:
            logging.error(f"Ошибка диагностики БД: {e}")

    def update_last_activity(self, rid):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE assembly_tasks 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE rid = ?
            """,
                (rid,),
            )
            self.conn.commit()
            logging.info(f"Обновлена активность для заказа: {rid}")
            return True
        except Exception as e:
            logging.error(f"Ошибка обновления активности: {e}")
            return False

    def get_inactive_orders(self, hours=24):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                SELECT rid, article, createdAt 
                FROM assembly_tasks 
                WHERE moved_to_empty = 0 
                AND datetime(last_activity) < datetime('now', ? || ' hours')
            """,
                (f"-{hours}",),
            )
            return cursor.fetchall()
        except Exception as e:
            logging.error(f"Ошибка получения неактивных заказов: {e}")
            return []

    def mark_as_moved(self, rid):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """
                UPDATE assembly_tasks 
                SET moved_to_empty = 1 
                WHERE rid = ?
            """,
                (rid,),
            )
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Ошибка отметки перемещения: {e}")
            return False
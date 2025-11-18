# modules/database.py
import sqlite3
import logging
import os

class DatabaseManager:
    def __init__(self, db_path="wb_orders.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()
        # УБЕРИТЕ этот вызов отсюда:
        # self.debug_database()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assembly_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rid TEXT UNIQUE,
                orderUid TEXT,
                nmId INTEGER,
                article TEXT,
                price REAL,
                createdAt TEXT,
                status TEXT DEFAULT 'new',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()
        logging.info("✅ Таблица assembly_tasks создана или уже существует")

    def add_assembly_task(self, rid, orderUid, nmId, article, price, createdAt, status='new'):
        """Добавляет сборочное задание в базу данных"""
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO assembly_tasks 
                (rid, orderUid, nmId, article, price, createdAt, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (rid, orderUid, nmId, article, price, createdAt, status))
            self.conn.commit()
            logging.info(f"Сборочное задание (rid: {rid}) обработано и добавлено в базу.")
            return True
        except Exception as e:
            logging.error(f"Ошибка добавления задания в БД: {e}")
            return False

    def get_task_by_rid(self, rid):
        """Находит задание по rid"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM assembly_tasks WHERE rid = ?", (rid,))
            return cursor.fetchone()
        except Exception as e:
            logging.error(f"Ошибка поиска задания по rid: {e}")
            return None

    def get_task_by_order_uid(self, order_uid):
        """Находит задание по orderUid"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM assembly_tasks WHERE orderUid = ?", (order_uid,))
            result = cursor.fetchone()
            if result:
                logging.info(f"      🔍 Найден заказ по orderUid: {order_uid} -> {result[1]}")
            return result
        except Exception as e:
            logging.error(f"Ошибка поиска задания по orderUid: {e}")
            return None

    # ДОБАВЬТЕ этот метод ВНУТРИ класса:
    def debug_database(self):
        """Диагностика базы данных"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("SELECT * FROM assembly_tasks ORDER BY id DESC LIMIT 5")
            recent_tasks = cursor.fetchall()
            
            logging.info("🔍 ДИАГНОСТИКА БАЗЫ ДАННЫХ:")
            for task in recent_tasks:
                logging.info(f"   Запись: {task}")
        except Exception as e:
            logging.error(f"❌ Ошибка диагностики БД: {e}")
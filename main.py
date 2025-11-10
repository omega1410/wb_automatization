import os
import time
import logging
from datetime import datetime
from dotenv import load_dotenv

# <-- 1. ДОБАВИТЬ ВСЕ ИМПОРТЫ
from modules.database import DatabaseManager
from modules.wb_orders_api import WBOrdersAPI
from modules.yandex_disk import YandexDiskManager
from modules.wb_chat import WBChatAPI

# Настраиваем логирование, чтобы видеть все шаги в консоли и/или файле
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Загружаем переменные из .env файла
load_dotenv()


class WBAutoBot:
    def __init__(self):
        """Инициализация бота и всех его компонентов."""
        logging.info("🚀 ИНИЦИАЛИЗАЦИЯ WB AUTO BOT")

        # Получаем ключи из .env файла
        wb_key = os.getenv("WB_API_KEY")
        yandex_token = os.getenv("YANDEX_DISK_TOKEN")
        # Возможно, у вас отдельный ключ для чатов
        wb_chat_key = os.getenv(
            "WB_CHAT_API_KEY", wb_key
        )  # Если нет, используем основной

        # Проверяем, что ключи загрузились, иначе выбрасываем исключение
        if not wb_key:
            raise ValueError(
                "❌ Критическая ошибка: WB_API_KEY не найден в .env файле."
            )
        if not yandex_token:
            raise ValueError(
                "❌ Критическая ошибка: YANDEX_DISK_TOKEN не найден в .env файле."
            )

        logging.info("✅ Ключи API успешно загружены из .env файла.")

        # <-- 2. ИНИЦИАЛИЗИРОВАТЬ ВСЕ API
        self.db = DatabaseManager()
        self.disk = YandexDiskManager(yandex_token)
        self.orders_api = WBOrdersAPI(wb_key)
        self.chat_api = WBChatAPI(wb_chat_key)

        logging.info("✅ Все модули бота успешно инициализированы.")

    def process_new_tasks(self):
        """Обработка новых сборочных заданий."""
        logging.info("🔄 Начинаем обработку новых сборочных заданий...")
        tasks = self.orders_api.get_new_orders()

        if not tasks:
            logging.info("Новых сборочных заданий не найдено.")
            return

        processed_count = 0
        for task in tasks:
            # В API WB v3 поле "id" является числовым rid
            rid = str(task.get("id"))
            if not rid:
                logging.warning(f"Получено задание без id (rid): {task}")
                continue

            # Проверяем, обрабатывали ли уже это задание
            if self.db.get_task_by_rid(rid):
                continue  # Если уже есть в базе, пропускаем

            # Создаем папку на Диске.
            if self.disk.create_folder(f"WB_Orders/{rid}"):
                # Сохраняем в таблицу assembly_tasks
                self.db.add_assembly_task(
                    rid=rid,
                    orderUid=task.get("orderUid"),
                    nmId=task.get("nmId"),
                    article=task.get("article"),
                    price=task.get("price") / 100,  # Цена обычно приходит в копейках
                    createdAt=task.get("createdAt"),
                )
                processed_count += 1
            else:
                logging.error(
                    f"Не удалось создать папку для задания {rid}. Запись в БД пропущена."
                )

        logging.info(f"📦 Обработано новых заданий в этом цикле: {processed_count}")

    def process_chat_events(self):
        """Обработка новых событий в чатах для связки заказа и чата."""
        logging.info("💬 Проверяем новые события в чатах...")
        events_data = self.chat_api.get_chat_events()

        if not events_data or "events" not in events_data:
            logging.info("Новых событий в чатах нет.")
            return

        updated_count = 0
        for event in events_data.get("events", []):
            if event.get("type") == "order" and "order" in event:
                chat_id = event.get("chatId")
                gNumber = event["order"].get("gNumber")

                if gNumber and chat_id:
                    order_in_db = self.db.get_order(gNumber)
                    # Обновляем, только если заказ есть в нашей базе и у него еще нет chat_id
                    if order_in_db and not order_in_db.get("chat_id"):
                        self.db.update_order_chat_id(gNumber, chat_id)
                        updated_count += 1

        if updated_count > 0:
            logging.info(f"✅ Обновлено {updated_count} заказов с новыми chat_id.")

    def start(self, interval_seconds=300):
        """Запуск основного цикла бота."""
        logging.info("\n🎯 ЗАПУСК АВТОМАТИЗАЦИИ WB")
        logging.info(
            f"Бот будет проверять новые задания и чаты каждые {interval_seconds // 60} минут."
        )
        logging.info("Для остановки нажмите Ctrl+C\n")

        try:
            iteration = 0
            while True:
                iteration += 1
                logging.info(
                    f"\n{'='*50}\nЦИКЛ #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

                # <-- 3. ВЫЗВАТЬ ОБА МЕТОДА В ЦИКЛЕ
                self.process_new_tasks()
                self.process_chat_events()

                logging.info(
                    f"⏰ Следующая проверка через {interval_seconds // 60} минут..."
                )
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logging.info("\n⏹️  ОСТАНОВКА БОТА по команде пользователя.")
        except Exception as e:
            logging.critical(f"КРИТИЧЕСКАЯ ОШИБКА в основном цикле: {e}", exc_info=True)


if __name__ == "__main__":
    try:
        bot = WBAutoBot()
        bot.start()
    except ValueError as e:
        # Ловим ошибку отсутствия ключей при инициализации
        logging.critical(e)

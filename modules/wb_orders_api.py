# modules/wb_orders_api.py (ЭТАЛОННАЯ ВЕРСИЯ)

import logging
from .base_api import BaseAPIClient  # Убедитесь, что этот импорт правильный


# В этой строке ОБЯЗАТЕЛЬНО должно быть (BaseAPIClient)
class WBOrdersAPI(BaseAPIClient):

    def __init__(self, api_key):
        """
        Инициализирует API-клиент для сборочных заданий.
        """
        # Эта строка вызывает конструктор родительского класса BaseAPIClient
        super().__init__(
            api_key=api_key, base_url="https://marketplace-api.wildberries.ru/api/v3"
        )

    def get_new_orders(self):
        """
        Получение новых сборочных заданий.
        """
        logging.info("Запрос новых сборочных заданий...")
        data = self._request("GET", "/orders/new")

        if data and isinstance(data, dict) and "orders" in data:
            tasks = data["orders"]
            logging.info(f"✅ Получено новых сборочных заданий: {len(tasks)}")
            return tasks

        logging.warning("Не удалось получить новые сборочные задания или список пуст.")
        return []

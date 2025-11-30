import logging

from .base_api import BaseAPIClient


class WBOrdersAPI(BaseAPIClient):

    def __init__(self, api_key):
        super().__init__(
            api_key=api_key, base_url="https://marketplace-api.wildberries.ru/api/v3"
        )

    def get_new_orders(self):
        logging.info("Запрос новых сборочных заданий...")
        data = self._request("GET", "/orders/new")

        if data and isinstance(data, dict) and "orders" in data:
            tasks = data["orders"]
            logging.info(f"Получено новых сборочных заданий: {len(tasks)}")
            return tasks

        logging.warning("Не удалось получить новые сборочные задания или список пуст.")
        return []

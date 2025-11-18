# modules/wb_marketplace_api.py
import logging
from .base_api import BaseAPIClient

class WBMarketplaceAPI(BaseAPIClient):
    def __init__(self, api_key):
        """
        Инициализирует API-клиент для Marketplace API Wildberries.
        Использует marketplace-api.wildberries.ru
        """
        super().__init__(
            api_key=api_key, 
            base_url="https://marketplace-api.wildberries.ru/api/v3"
        )
        logging.info("✅ WBMarketplaceAPI инициализирован")

    def get_new_orders(self):
        """
        Получение новых сборочных заданий через Marketplace API.
        Возвращает список заказов или пустой список при ошибке.
        """
        logging.info("🔄 Запрос новых заказов через Marketplace API...")
        data = self._request("GET", "/orders/new")

        if data and isinstance(data, dict) and "orders" in data:
            orders = data["orders"]
            logging.info(f"✅ Получено новых заказов через Marketplace API: {len(orders)}")
            return orders

        logging.warning("📭 Не удалось получить заказы или список пуст.")
        return []
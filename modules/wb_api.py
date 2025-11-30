import logging
from datetime import datetime, timedelta

from .base_api import BaseAPIClient


class WildberriesAPI(BaseAPIClient):
    def __init__(self, api_key):
        super().__init__(
            api_key, base_url="https://marketplace-api.wildberries.ru/api/v3"
        )

    def get_recent_orders(self, days=1):
        date_from = (datetime.now() - timedelta(days=days)).isoformat()
        params = {"dateFrom": date_from}
        data = self._request("GET", "/orders/new", params=params)

        if not data:
            return []

        active_orders = [
            order for order in data.get("orders", []) if not order.get("isCancel")
        ]
        logging.info(
            f"Получено {len(data.get('orders', []))} заказов, из них активных: {len(active_orders)}"
        )
        return active_orders

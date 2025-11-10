from .base_api import BaseAPIClient
import logging


class WBChatAPI(BaseAPIClient):
    def __init__(self, api_key):
        super().__init__(
            api_key=api_key,
            base_url="https://178.170.196.25/api/v1/seller",
            host_header="buyer-chat-api.wildberries.ru",
        )

    def get_chat_events(self, next_timestamp=None):
        """Получение событий из чатов с 'правильным' таймаутом."""
        endpoint = "/events"
        params = {}
        if next_timestamp:
            params["next"] = next_timestamp

        # ---> ВОТ ИЗМЕНЕНИЕ <---
        # Устанавливаем таймаут чуть меньше, чем у сервера WB (~60s).
        # Теперь запрос будет завершаться по нашему таймауту, а не по обрыву соединения сервером.
        data = self._request("GET", endpoint, params=params, timeout=55)

        return data.get("result", {}) if data else {}

    def send_message(self, chat_id, message_text):
        # Для отправки сообщения длинный таймаут не нужен, используется стандартный.
        payload = {"chatId": chat_id, "text": message_text}
        data = self._request("POST", "/chat/send", json=payload)

        if data:
            logging.info(f"Сообщение успешно отправлено в чат {chat_id}")
            return True
        else:
            logging.error(f"Не удалось отправить сообщение в чат {chat_id}")
            return False

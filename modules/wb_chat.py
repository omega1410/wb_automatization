import logging
import uuid
import requests
from .base_api import BaseAPIClient

class WBChatAPI(BaseAPIClient):
    def __init__(self, api_key):
        self.api_key = api_key
        base_url = "https://buyer-chat-api.wildberries.ru"

        super().__init__(
            api_key=api_key,
            base_url=base_url,
            host_header="buyer-chat-api.wildberries.ru",
            timeout=15,
        )
        self.session.headers["Authorization"] = api_key
        logging.info("WBChatAPI инициализирован")

    def get_chats_list(self):
        try:
            url = "https://buyer-chat-api.wildberries.ru/api/v1/seller/chats"
            headers = {"Authorization": self.api_key, "Content-Type": "application/json"}
            response = requests.get(url, headers=headers, timeout=10, verify=False)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            logging.error(f"Ошибка получения списка чатов: {e}")
        return None

    def get_chat_events(self, next_timestamp=None):
        endpoint = "/api/v1/seller/events"
        params = {}
        if next_timestamp:
            params["next"] = next_timestamp
        data = self._request("GET", endpoint, params=params, timeout=10)
        return data

    def send_message(self, chat_id, text, reply_sign=None):
        try:
            url = "https://buyer-chat-api.wildberries.ru/api/v1/seller/message"

            if not reply_sign or reply_sign.startswith("chat_"):
                reply_sign = self._get_reply_sign_from_chat(chat_id)

            payload = {
                "id": str(uuid.uuid4()),
                "chatID": chat_id,
                "text": text,
                "message": text,
                "type": "text",
                "replySign": reply_sign
            }

            headers = {
                "Authorization": self.api_key,
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }

            logging.info(f"Отправка в чат {chat_id}")
            logging.info(f"Payload ID: {payload['id']}")

            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                logging.info(f"УСПЕХ (200 OK)")
                return True
            else:
                logging.error(f"Ошибка: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logging.error(f"Ошибка send_message: {e}")
            return False

    def _get_reply_sign_from_chat(self, chat_id):
        try:
            events_data = self.get_chat_events()
            candidates = []
            if events_data and "events" in events_data:
                for event in events_data["events"]:
                    if event.get("chatID") == chat_id and "replySign" in event:
                        candidates.append(event["replySign"])

            if candidates:
                return candidates[-1]

            chats_data = self.get_chats_list()
            if chats_data and "result" in chats_data and "chats" in chats_data["result"]:
                for chat in chats_data["result"]["chats"]:
                    if chat.get("chatID") == chat_id and "replySign" in chat:
                        return chat["replySign"]

            return f"chat_{chat_id}"
        except Exception:
            return f"chat_{chat_id}"

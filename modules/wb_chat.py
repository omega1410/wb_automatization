from .base_api import BaseAPIClient
import logging

from .base_api import BaseAPIClient
import logging

class WBChatAPI(BaseAPIClient):
    def __init__(self, api_key):
        base_url = "https://buyer-chat-api.wildberries.ru"
        
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            host_header="buyer-chat-api.wildberries.ru",
            timeout=15
        )
        
        logging.info("🔧 WBChatAPI инициализирован для работы с чатами")

    def get_chats_list(self):
        """Получить список всех чатов - БЕЗ ЛОГИРОВАНИЯ"""
        endpoint = "/api/v1/seller/chats"
        data = self._request("GET", endpoint, timeout=10)
        return data  # Просто возвращаем данные, без логирования

    def get_chat_events(self, next_timestamp=None):
        """Получить события чатов с пагинацией"""
        endpoint = "/api/v1/seller/events"
        
        params = {}
        if next_timestamp:
            params["next"] = next_timestamp
            
        data = self._request("GET", endpoint, params=params, timeout=10)
        return data

    def get_all_recent_events(self, limit=50):
        """Получить несколько последних событий"""
        all_events = []
        next_timestamp = None
        
        # Получаем события пачками, пока не наберем limit
        for _ in range(5):  # максимум 5 запросов
            events_data = self.get_chat_events(next_timestamp)
            
            if not events_data or "events" not in events_data:
                break
                
            events_list = events_data.get("events", [])
            all_events.extend(events_list)
            
            # Если набрали достаточно событий или нет следующих
            if len(all_events) >= limit or not events_data.get("next"):
                break
                
            next_timestamp = events_data.get("next")
            time.sleep(0.1)  # небольшая пауза
        
        return {
            "events": all_events[:limit],
            "totalEvents": len(all_events[:limit])
        }

    def check_api_access(self):
        """Проверка доступности API чатов"""
        endpoint = "/api/v1/seller/chats"
        
        logging.info("🔍 Проверка доступности API чатов...")
        data = self._request("GET", endpoint, timeout=10)
        
        if data is not None:
            logging.info("✅ API чатов доступен")
            return True
        else:
            logging.error("❌ API чатов недоступен")
            return False
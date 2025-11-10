# modules/yandex_disk.py (улучшенная версия)
import requests
import logging
from .base_api import BaseAPIClient  # Условный импорт


# Вместо наследования от BaseAPIClient (т.к. логика ответа отличается),
# применим те же принципы: сессия в __init__ и единый метод для запросов.
class YandexDiskManager:
    def __init__(self, token):
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"OAuth {token}",
                "Content-Type": "application/json",
            }
        )
        # Здесь также стоит решить проблему с сертификатами, а не отключать проверку
        self.session.verify = False
        if not self.session.verify:
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )

        self.ensure_root_folders()

    def _request(self, method, url, **kwargs):
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            # Для Я.Диска нам часто важен сам статус, а не только JSON
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка запроса к Yandex.Disk ({url}): {e}")
            return None

    def create_folder(self, path):
        """Создает папку. Возвращает True, если папка создана или уже существует."""
        response = self._request("PUT", self.base_url, params={"path": path})

        if response is None:
            return False

        if response.status_code in [
            201,
            409,
        ]:  # 201 - Created, 409 - Conflict (уже существует)
            logging.info(f"Папка '{path}' успешно создана или уже существует.")
            return True
        else:
            logging.error(
                f"Ошибка создания папки '{path}': {response.status_code} - {response.text}"
            )
            return False

    def ensure_root_folders(self):
        """Гарантирует наличие корневых папок."""
        logging.info("Проверка наличия корневых папок на Яндекс.Диске...")
        self.create_folder("WB_Orders")
        self.create_folder("WB_Empty_Orders")

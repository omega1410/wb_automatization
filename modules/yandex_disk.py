# modules/yandex_disk.py
import requests
import logging
import time
import urllib3
from requests.exceptions import RequestException

# Отключаем предупреждения SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class YandexDiskManager:
    def __init__(self, token):
        self.base_url = "https://cloud-api.yandex.net/v1/disk/resources"
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"OAuth {token}",
            "Content-Type": "application/json",
        })
        
        # Отключаем проверку SSL
        self.session.verify = False
        
        # Проверяем токен
        if not self.check_token_validity():
            logging.error("❌ Проблема с токеном Яндекс.Диска!")
        else:
            logging.info("✅ Токен Яндекс.Диска валиден")
        
        self.ensure_root_folders()

    def check_token_validity(self):
        """Проверяет валидность токена Яндекс.Диска"""
        try:
            response = self.session.get(
                "https://cloud-api.yandex.net/v1/disk/",
                timeout=10
            )
            
            if response.status_code == 200:
                logging.info("✅ Токен Яндекс.Диска валиден")
                return True
            elif response.status_code == 401:
                logging.error("❌ Неверный токен Яндекс.Диска")
                return False
            else:
                logging.error(f"❌ Ошибка доступа к Яндекс.Диску: {response.status_code}")
                return False
        except Exception as e:
            logging.error(f"❌ Ошибка проверки токена: {e}")
            return False

    def create_folder(self, path):
        """Создает папку на Яндекс.Диске"""
        try:
            # Убедимся, что путь начинается с /
            if not path.startswith('/'):
                path = '/' + path
                
            response = self.session.put(
                "https://cloud-api.yandex.net/v1/disk/resources",
                params={"path": path},
                timeout=10
            )

            if response.status_code in [201, 409]:
                logging.info(f"✅ Папка создана: '{path}'")
                return True
            else:
                logging.error(f"❌ Ошибка создания папки '{path}': {response.status_code} - {response.text}")
                return False
                    
        except Exception as e:
            logging.error(f"❌ Ошибка при создании папки '{path}': {e}")
            return False

    def upload_file_from_memory(self, file_content, disk_path):
        """Загружает файл на Яндекс.Диск из памяти"""
        try:
            if not disk_path.startswith('/'):
                disk_path = '/' + disk_path
                
            logging.info(f"🔄 Загрузка файла на Яндекс.Диск: {disk_path}")
            
            # Шаг 1: Создаем папку
            folder_path = '/'.join(disk_path.split('/')[:-1])
            if folder_path:
                self.create_folder(folder_path)
                time.sleep(1)
            
            # Шаг 2: Получаем URL для загрузки
            response = self.session.get(
                "https://cloud-api.yandex.net/v1/disk/resources/upload",
                params={
                    "path": disk_path,
                    "overwrite": "true"
                },
                timeout=30
            )
            
            logging.info(f"📡 Статус получения URL: {response.status_code}")
            
            if response.status_code == 200:
                upload_url = response.json().get('href')
                if not upload_url:
                    logging.error("❌ Нет URL для загрузки в ответе")
                    return False
                
                # Шаг 3: Загружаем файл
                put_response = requests.put(upload_url, data=file_content, timeout=30, verify=False)
                
                logging.info(f"📤 Статус загрузки: {put_response.status_code}")
                
                if put_response.status_code in [200, 201]:
                    logging.info(f"✅ Файл успешно загружен на Яндекс.Диск: {disk_path}")
                    return True  # ← ВАЖНО: возвращаем True при успехе
                else:
                    logging.error(f"❌ Ошибка загрузки файла: {put_response.status_code} - {put_response.text}")
                    return False
            else:
                logging.error(f"❌ Ошибка получения URL: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logging.error(f"❌ Исключение при загрузке на Яндекс.Диск: {e}")
            return False

    def ensure_root_folders(self):
        """Гарантирует наличие корневых папок."""
        logging.info("Проверка наличия корневых папок на Яндекс.Диске...")
        self.create_folder("WB_Orders")
        self.create_folder("WB_Chats")
        logging.info("✅ Корневые папки созданы или уже существуют")

    def _request(self, method, url, **kwargs):
        """Базовый метод для запросов"""
        try:
            response = self.session.request(method, url, timeout=10, **kwargs)
            return response
        except requests.exceptions.RequestException as e:
            logging.error(f"Ошибка запроса к Yandex.Disk ({url}): {e}")
            return None
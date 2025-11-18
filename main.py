import os
import time
import logging
import subprocess
import sys
import requests
from datetime import datetime
from dotenv import load_dotenv

current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv()

from modules.database import DatabaseManager
from modules.wb_marketplace_api import WBMarketplaceAPI
from modules.yandex_disk import YandexDiskManager
from modules.wb_chat import WBChatAPI

print("✅ Все модули успешно импортированы")

def check_dns_resolution():
    domains = [
        "communications.wildberries.ru",
        "seller-chat-api.wildberries.ru", 
        "marketplace-api.wildberries.ru",
        "wildberries.ru"
    ]

    print("🔍 ПРОВЕРКА DNS РАЗРЕШЕНИЯ:")
    all_resolved = True

    for domain in domains:
        try:
            result = subprocess.run(
                ["nslookup", domain, "8.8.8.8"],
                capture_output=True, 
                text=True,
                timeout=10
            )
            if "Address" in result.stdout:
                lines = result.stdout.splitlines()
                ip_line = None
                for line in lines:
                    if "Address:" in line and "8.8.8.8" not in line:
                        ip_line = line.strip()
                        break
                
                if ip_line:
                    print(f"   ✅ {domain} - РАЗРЕШАЕТСЯ")
                    print(f"      {ip_line}")
                else:
                    print(f"   ⚠️  {domain} - DNS работает, но IP не найден")
                    all_resolved = False
            else:
                print(f"   ❌ {domain} - НЕ РАЗРЕШАЕТСЯ")
                all_resolved = False
        except subprocess.TimeoutExpired:
            print(f"   ⏰ {domain} - ТАЙМАУТ ПРОВЕРКИ")
            all_resolved = False
        except Exception as e:
            print(f"   ❌ {domain} - ОШИБКА: {e}")
            all_resolved = False
    
    print(f"📊 ИТОГ DNS ПРОВЕРКИ: {'ВСЕ РАБОТАЕТ' if all_resolved else 'ЕСТЬ ПРОБЛЕМЫ'}")
    return all_resolved

class WBAutoBot:
    def __init__(self):
        print("🚀 ИНИЦИАЛИЗАЦИЯ WB AUTO BOT")
        
        dns_working = check_dns_resolution()
        print(f"🎯 РЕЗУЛЬТАТ DNS ПРОВЕРКИ: {dns_working}")
        
        wb_key = os.getenv("WB_API_KEY")
        yandex_token = os.getenv("YANDEX_DISK_TOKEN")
        wb_chat_key = os.getenv("WB_CHAT_API_KEY", wb_key)

        if not wb_key:
            raise ValueError("❌ WB_API_KEY не найден в .env файле")
        if not yandex_token:
            raise ValueError("❌ YANDEX_DISK_TOKEN не найден в .env файле")

        print("✅ Ключи загружены из .env файла")

        print("🔄 Инициализация DatabaseManager...")
        self.db = DatabaseManager()
        print("🔄 Инициализация YandexDiskManager...")
        self.disk = YandexDiskManager(yandex_token)
        print("🔄 Инициализация WBMarketplaceAPI...")
        self.orders_api = WBMarketplaceAPI(wb_key)
        
        print("🔧 Инициализация WBChatAPI...")
        self.chat_api = WBChatAPI(wb_chat_key)

        self.processed_event_ids = set()
        self.last_check_time = int(time.time() * 1000)
        self.chat_rid_cache = {}

        print("✅ Все модули бота инициализированы")

    def process_new_tasks(self):
        logging.info("🔄 Начинаем обработку заказов через Marketplace API...")
        orders = self.orders_api.get_new_orders()

        if not orders:
            logging.info("📭 Новых заказов не найдено.")
            return

        processed_count = 0
        for order in orders:
            order_id = str(order.get("id"))
            if not order_id:
                continue

            if self.db.get_task_by_rid(order_id):
                continue

            logging.info(f"📦 НОВЫЙ ЗАКАЗ ОБНАРУЖЕН:")
            logging.info(f"   🆔 ID: {order_id}")
            logging.info(f"   📦 OrderUID: {order.get('orderUid', 'N/A')}")
            logging.info(f"   🏷️ Article: {order.get('article', 'N/A')}")
            logging.info(f"   📅 Дата: {order.get('createdAt', 'N/A')}")
            logging.info(f"   🏷️ nmId: {order.get('nmId', 'N/A')}")
            logging.info(f"   💵 Цена: {order.get('price', 'N/A')}")

            if self.disk.create_folder(f"WB_Orders/{order_id}"):
                self.db.add_assembly_task(
                    rid=order_id,
                    orderUid=order.get("orderUid"),
                    nmId=order.get("nmId"),
                    article=order.get("article"),
                    price=order.get("price", 0) / 100,
                    createdAt=order.get("createdAt"),
                )
                processed_count += 1
                logging.info(f"✅ Создана папка и запись для заказа: {order_id}")

        logging.info(f"📦 Обработано новых заказов: {processed_count}")

    def process_chat_events(self):
        try:
            chats_data = self.chat_api.get_chats_list()
            chats_count = len(chats_data["result"]) if chats_data and "result" in chats_data else 0
            logging.info(f"💬 Чатов: {chats_count}")
            
            events_data = self.chat_api.get_chat_events(self.last_check_time)
            
            new_messages_count = 0
            saved_media_count = 0
            
            if events_data and "result" in events_data:
                events_list = events_data["result"].get("events", [])
                
                for event in events_list:
                    event_id = event.get('eventID')
                    event_time = event.get('addTimestamp', 0)
                    
                    if event_id in self.processed_event_ids:
                        continue
                        
                    if event_time > self.last_check_time and event.get('eventType') == 'message':
                        self.processed_event_ids.add(event_id)
                        
                        if event.get('sender') == 'client':
                            new_messages_count += 1
                            text = event.get('message', {}).get('text', '')
                            client_name = event.get('clientName', 'Клиент')
                            time_str = event.get('addTime', '')[:19]
                            chat_id = event.get('chatID', 'unknown')
                            
                            if text:
                                logging.info(f"   💬 НОВОЕ СООБЩЕНИЕ от {client_name}: {text}")
                            else:
                                logging.info(f"   📎 НОВОЕ МЕДИА-СООБЩЕНИЕ от {client_name}")
                            
                            logging.info(f"      ⏰ {time_str}")
                            logging.info(f"      💬 ID чата: {chat_id}")
                            
                            if not text:
                                logging.info(f"      🔍 ДИАГНОСТИКА МЕДИА-СООБЩЕНИЯ:")
                                logging.info(f"      🔍 event keys: {list(event.keys())}")
                                logging.info(f"      🔍 message keys: {list(event.get('message', {}).keys())}")
                                logging.info(f"      🔍 attachments: {event.get('message', {}).get('attachments', {})}")

                            rid = None
                            found_by = None
                            
                            if chat_id in self.chat_rid_cache:
                                rid = self.chat_rid_cache[chat_id]
                                found_by = "кэша чата"
                                logging.info(f"      📦 Найден RID из {found_by}: {rid}")
                            else:
                                message_data = event.get('message', {})
                                attachments = message_data.get('attachments', {})
                                good_card = attachments.get('goodCard')
                                
                                if good_card:
                                    rid = good_card.get('rid')
                                    if rid:
                                        found_by = "goodCard текущего сообщения"
                                        nm_id = good_card.get('nmID')
                                        logging.info(f"      📦 Найден RID из {found_by}: {rid} (арт. {nm_id})")

                                if not rid and text:
                                    extracted_rid = self.extract_order_from_text(text)
                                    if extracted_rid:
                                        rid = extracted_rid
                                        found_by = "текста сообщения"
                                        logging.info(f"      📦 Найден RID из {found_by}: {rid}")

                                if not rid:
                                    rid_from_current = self.find_rid_in_current_events(chat_id, events_list)
                                    if rid_from_current:
                                        rid = rid_from_current
                                        found_by = "текущих событий"
                                        logging.info(f"      📦 Найден RID из {found_by}: {rid}")

                                if not rid:
                                    rid_from_history = self.find_any_rid_in_chat_history(chat_id)
                                    if rid_from_history:
                                        rid = rid_from_history
                                        found_by = "истории чата"
                                        logging.info(f"      📦 Найден RID из {found_by}: {rid}")

                                if rid:
                                    self.chat_rid_cache[chat_id] = rid
                                    logging.info(f"      💾 Сохранен RID в кэш для чата {chat_id}")

                            message_data = event.get('message', {})
                            attachments = message_data.get('attachments', {})
                            images = attachments.get('images', [])

                            logging.info(f"      🔍 Проверка медиа-вложений: {len(images)} изображений")

                            def clean_folder_name(name):
                                import re
                                cleaned = re.sub(r'[<>:"/\\|?*]', '_', name)
                                cleaned = cleaned.strip(' .')
                                return cleaned[:50]

                            client_name_clean = clean_folder_name(client_name)
                            
                            if rid:
                                matched_order_id = self.match_chat_rid_to_order(rid)
                                
                                if matched_order_id:
                                    order_folder = f"WB_Orders/{matched_order_id}"
                                    folder_type = "заказа"
                                    logging.info(f"      📁 Сохраняем в папку заказа: {matched_order_id}")
                                else:
                                    order_folder = f"WB_Orders/{rid}"
                                    folder_type = "заказа (по RID чата)"
                                    logging.info(f"      📁 Не найдено соответствие, используем RID чата: {rid}")
                            else:
                                clean_chat_id = clean_folder_name(chat_id)[-8:]
                                order_folder = f"WB_Chats/{client_name_clean}_{clean_chat_id}"
                                folder_type = "чата"
                                logging.info(f"      💬 RID не найден, сохраняем в папку чата")

                            if images:
                                logging.info(f"      🖼️ Обнаружены медиа-вложения...")
                                
                                if self.disk.create_folder(order_folder):
                                    time.sleep(1)
                                    saved_files = self.download_chat_media(event, order_folder, client_name)
                                    if saved_files:
                                        saved_media_count += len(saved_files)
                                        logging.info(f"      ✅ Сохранено файлов в папку {folder_type}: {len(saved_files)}")
                                    else:
                                        logging.error(f"      ❌ Не удалось сохранить медиа-файлы")
                                else:
                                    logging.error(f"      ❌ Не удалось создать папку: {order_folder}")
                            else:
                                logging.info(f"      🔍 Нет медиа-вложений для сохранения")
                
                self.last_check_time = int(time.time() * 1000)
                
                logging.info(f"📨 Новых сообщений: {new_messages_count}")
                if saved_media_count > 0:
                    logging.info(f"🖼️ Сохранено медиа-файлов: {saved_media_count}")
                
                if len(self.processed_event_ids) > 1000:
                    self.processed_event_ids = set()
                        
        except Exception as e:
            logging.error(f"❌ Ошибка обработки событий чата: {e}")

    def find_rid_in_chat_history(self, chat_id):
        try:
            return None
        except Exception as e:
            logging.error(f"Ошибка поиска RID в истории чата: {e}")
            return None

    def extract_order_from_text(self, text):
        import re
        
        if not text:
            return None
            
        patterns = [
            r'заказ[:\s]*([A-Z0-9]{10,})',
            r'сборочное[:\s]*([A-Z0-9]{10,})',
            r'\b([A-Z]{2,3}\d{7,9})\b',
            r'номер[:\s]*([A-Z0-9]{10,})',
            r'order[:\s]*([A-Z0-9]{10,})',
            r'DAy\.([a-f0-9]{32})',
            r'([a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                found = match.group(1)
                logging.info(f"      🔍 Найден номер в тексте: {found}")
                return found
        return None

    def find_rid_in_current_events(self, chat_id, current_events_list):
        try:
            for event in current_events_list:
                if event.get('chatID') == chat_id:
                    message_data = event.get('message', {})
                    if not message_data:
                        continue
                        
                    attachments = message_data.get('attachments', {})
                    good_card = attachments.get('goodCard')
                    
                    if good_card and good_card.get('rid'):
                        rid = good_card.get('rid')
                        nm_id = good_card.get('nmID')
                        logging.info(f"      📦 Найден RID в текущих событиях: {rid} (арт. {nm_id})")
                        return rid
            return None
        except Exception as e:
            logging.error(f"Ошибка поиска RID в текущих событиях: {e}")
            return None

    def find_any_rid_in_chat_history(self, chat_id):
        try:
            events_data = self.chat_api.get_chat_events()
            
            if events_data and "result" in events_data:
                events_list = events_data["result"].get("events", [])
                
                for event in events_list:
                    if event.get('chatID') == chat_id:
                        message_data = event.get('message', {})
                        if not message_data:
                            continue
                            
                        attachments = message_data.get('attachments', {})
                        good_card = attachments.get('goodCard')
                        
                        if good_card and good_card.get('rid'):
                            rid = good_card.get('rid')
                            nm_id = good_card.get('nmID')
                            logging.info(f"      📦 Найден RID из истории чата: {rid} (арт. {nm_id})")
                            return rid
                            
                logging.info(f"      🔍 RID не найден в истории чата {chat_id}")
            else:
                logging.info(f"      🔍 Нет истории для чата {chat_id}")
                
            return None
        except Exception as e:
            logging.error(f"Ошибка поиска любого RID в истории: {e}")
            return None

    def find_recent_order_by_client(self, client_name):
        try:
            return None

            orders = self.orders_api.get_new_orders()
            if orders and len(orders) > 0:
                latest_order = orders[0]
                latest_order_id = str(latest_order.get('id'))
 
                existing_task = self.db.get_task_by_rid(latest_order_id)
                if existing_task:
                    logging.info(f"      🔍 Найден последний заказ в базе: {latest_order_id}")
                    return latest_order_id
            
            return None
        except Exception as e:
            logging.error(f"Ошибка поиска заказа по клиенту: {e}")
            return None

    def match_chat_rid_to_order(self, chat_rid):
        try:
            if not chat_rid or '.' not in chat_rid:
                return None
                
            parts = chat_rid.split('.')
            if len(parts) >= 2:
                order_uid_from_chat = parts[1]
                
                order_from_db = self.db.get_task_by_order_uid(order_uid_from_chat)
                if order_from_db:
                    order_id = order_from_db[1]
                    logging.info(f"      🔗 Сопоставлен RID чата '{chat_rid}' с заказом '{order_id}'")
                    return order_id
            
            logging.info(f"      🔍 Не найдено соответствие для RID: {chat_rid}")
            return None
        except Exception as e:
            logging.error(f"Ошибка сопоставления RID: {e}")
            return None

    def start(self, interval_seconds=30):
        logging.info("\n🎯 ЗАПУСК АВТОМАТИЗАЦИИ WB")
        logging.info(f"Бот будет проверять новые задания и чаты каждые {interval_seconds} секунд.")
        logging.info("Для остановки нажмите Ctrl+C\n")

        try:
            iteration = 0
            while True:
                iteration += 1
                logging.info(f"\n{'='*50}")
                logging.info(f"ЦИКЛ #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                self.process_new_tasks()
                self.process_chat_events()

                logging.info(f"⏰ Следующая проверка через {interval_seconds} секунд...")
                time.sleep(interval_seconds)
                
        except KeyboardInterrupt:
            logging.info("\n⏹️  ОСТАНОВКА БОТА по команде пользователя")
        except Exception as e:
            logging.critical(f"❌ Критическая ошибка в основном цикле: {e}")

    def download_chat_media(self, message_event, folder_name, client_name=None):
        saved_files = []
        
        try:
            message_data = message_event.get('message', {})
            attachments = message_data.get('attachments', {})
            images = attachments.get('images', [])
            
            logging.info(f"      🔍 Начало обработки медиа: {len(images)} изображений")
            
            if not images:
                logging.info("      🔍 Нет изображений для скачивания")
                return []
                
            for i, image in enumerate(images):
                try:
                    image_url = image.get('url')
                    if not image_url:
                        logging.warning(f"      ⚠️ Нет URL у изображения {i+1}")
                        continue

                    logging.info(f"      📥 Скачивание медиа {i+1}...")
                    logging.info(f"      🔗 URL: {image_url[:100]}...")
                    
                    response = requests.get(image_url, timeout=30, verify=False)
                    
                    logging.info(f"      📡 Статус скачивания: {response.status_code}")
                    
                    if response.status_code == 200:
                        file_size = len(response.content)
                        logging.info(f"      📊 Размер файла: {file_size} байт")
                        
                        timestamp = int(time.time() * 1000)
                        file_extension = "jpg"
                        if '.' in image_url:
                            ext = image_url.split('.')[-1].lower()
                            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                                file_extension = ext
                        
                        if client_name:
                            filename = f"{client_name}_{timestamp}_{i+1}.{file_extension}"
                        else:
                            filename = f"photo_{timestamp}_{i+1}.{file_extension}"
                        
                        disk_path = f"{folder_name}/{filename}"
                        logging.info(f"      🚀 Загрузка на Яндекс.Диск: {disk_path}")
                        
                        if hasattr(self.disk, 'upload_file_from_memory'):
                            success = self.disk.upload_file_from_memory(response.content, disk_path)
                            if success:
                                saved_files.append(disk_path)
                                logging.info(f"      ✅ Файл загружен на Яндекс.Диск: {disk_path}")
                            else:
                                logging.error(f"      ❌ Ошибка загрузки на Яндекс.Диск: {disk_path}")
                        else:
                            logging.error(f"      ❌ Метод upload_file_from_memory не существует")
                    else:
                        logging.error(f"      ❌ Ошибка скачивания: {response.status_code}")
                        
                except Exception as e:
                    logging.error(f"      ❌ Ошибка обработки изображения {i+1}: {e}")
                    continue
                    
            logging.info(f"      📋 Итог: загружено на Яндекс.Диск {len(saved_files)} файлов")
            return saved_files
            
        except Exception as e:
            logging.error(f"❌ Общая ошибка сохранения медиа: {e}")
            return []

if __name__ == "__main__":
    try:
        bot = WBAutoBot()
        bot.start(interval_seconds=60)
    except ValueError as e:
        logging.critical(f"❌ Ошибка инициализации: {e}")
    except Exception as e:
        logging.critical(f"❌ Неожиданная ошибка: {e}")
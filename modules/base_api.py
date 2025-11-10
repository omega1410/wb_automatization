import requests
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import RequestException, ReadTimeout


class BaseAPIClient:
    def __init__(
        self, api_key, base_url, auth_scheme="Bearer", host_header=None, timeout=15
    ):
        """
        Инициализирует базовый API клиент.

        :param api_key: API ключ для аутентификации.
        :param base_url: Базовый URL для всех запросов.
        :param auth_scheme: Схема аутентификации ('Bearer', 'OAuth', и т.д.).
        :param host_header: Заголовок Host, если нужен (для обхода DNS).
        :param timeout: Таймаут для запросов по умолчанию.
        """
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session(api_key, auth_scheme, host_header)

    def _create_session(self, api_key, auth_scheme, host_header):
        """
        Создает и настраивает объект сессии requests.
        """
        session = requests.Session()

        # Настройка заголовков для аутентификации и типа контента
        session.headers.update(
            {
                "Authorization": f"{auth_scheme} {api_key}",
                "Content-Type": "application/json",
            }
        )

        # Добавление заголовка Host, если он указан (полезно для обхода DNS)
        if host_header:
            session.headers["Host"] = host_header

        # Настройка повторных попыток для повышения надежности сети
        # Повторяем запрос до 3 раз при ошибках сервера (5xx) с небольшой задержкой.
        retries = Retry(
            total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Важно: Попробуйте решить проблему с сертификатами, а не отключать проверку
        session.verify = False
        if not session.verify:
            # Отключаем предупреждения только если проверка выключена
            requests.packages.urllib3.disable_warnings(
                requests.packages.urllib3.exceptions.InsecureRequestWarning
            )

        return session

    def _request(self, method, endpoint, **kwargs):
        """
        Выполняет HTTP запрос и обрабатывает основные ошибки.
        """
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        # Устанавливаем таймаут по умолчанию, если он не передан в вызове
        kwargs.setdefault("timeout", self.timeout)

        try:
            response = self.session.request(method, url, **kwargs)
            logging.info(f"Запрос к {url} вернул статус {response.status_code}")

            # Вызовет исключение для кодов ошибок 4xx/5xx
            response.raise_for_status()

            # Проверяем, есть ли в ответе JSON
            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            # Если не JSON, возвращаем текст (может быть полезно для отладки)
            return response.text

        except ReadTimeout:
            # Обрабатываем таймаут ожидания ответа (актуально для Long Polling в чатах)
            logging.info(
                f"Таймаут ожидания ответа от {url}. Вероятно, нет новых данных."
            )
            return None

        except RequestException as e:
            # Обрабатываем все остальные ошибки сети (нет подключения, DNS и т.д.)
            logging.error(f"Ошибка API запроса к {url}: {e}")
            return None

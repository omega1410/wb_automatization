import logging

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BaseAPIClient:
    def __init__(
        self, api_key, base_url, auth_scheme="Bearer", host_header=None, timeout=15
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session(api_key, auth_scheme, host_header)

    def _create_session(self, api_key, auth_scheme, host_header):
        session = requests.Session()

        session.trust_env = False

        session.headers.update(
            {
                "Authorization": f"{auth_scheme} {api_key}",
                "Content-Type": "application/json",
            }
        )

        if host_header:
            session.headers["Host"] = host_header

        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"],
            respect_retry_after_header=True,
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        session.verify = False

        import urllib3

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        return session

    def _request(self, method, endpoint, **kwargs):
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"

        kwargs.setdefault("timeout", 15)
        kwargs.setdefault("proxies", {"http": None, "https": None})
        kwargs.setdefault("verify", False)

        try:
            logging.info(f"Запрос: {method} {url}")
            logging.info(f"Заголовки Host: {self.session.headers.get('Host')}")

            response = self.session.request(method, url, **kwargs)

            logging.info(f"Ответ: {response.status_code}")
            if response.status_code != 200:
                logging.info(f"Тело ответа: {response.text[:200]}...")

            response.raise_for_status()

            if "application/json" in response.headers.get("Content-Type", ""):
                return response.json()
            return response.text

        except Exception as e:
            logging.error(f"Ошибка: {e}")
            return None

import os
import requests
import urllib3
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def test_with_specific_dates():
    wb_key = os.getenv("WB_API_KEY")

    headers = {"Authorization": f"Bearer {wb_key}", "Content-Type": "application/json"}

    test_dates = [
        (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
        (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
        "2025-05-01",
    ]

    for date_from in test_dates:
        print(f"\n🔍 Запрос заказов с {date_from}:")

        try:
            session = requests.Session()
            session.trust_env = False

            response = session.get(
                "https://statistics-api.wildberries.ru/api/v1/supplier/orders",
                headers=headers,
                params={"dateFrom": date_from},
                verify=False,
                timeout=15,
                proxies={"http": None, "https": None},
            )

            print(f"📊 Статус: {response.status_code}")

            if response.status_code == 200:
                orders = response.json()
                print(f"📦 Заказов: {len(orders)}")

                if orders:
                    print("🎯 ПЕРВЫЙ ЗАКАЗ:")
                    first_order = orders[0]
                    for key, value in first_order.items():
                        print(f"   {key}: {value}")
                    break
            else:
                print(f"❌ Ошибка: {response.text}")

        except Exception as e:
            print(f"❌ Исключение: {e}")


if __name__ == "__main__":
    test_with_specific_dates()

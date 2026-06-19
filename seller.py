import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Получить список товаров магазина озон.

    Args:
        last_id (str): id последнего товара для пагинации.
        client_id (str): ID продавца.
        seller_token (str): Токен авторизации магазина на Ozon.

    Returns:
        dict: Словарь со списком товаров,total и last_id.

    Examples:
        >>> get_product_list("", "client_123", "token_abc")
        {'items': [{'product_id': 111, 'offer_id': 'art-001'}], 'last_id': 'bWFya2V0', 'total': 1}

        >>> get_product_list("", "client_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Получить артикулы товаров магазина озон.

    Args:
     client_id (str): ID продавца.
     seller_token (str): Токен авторизации магазина озон.

    Returns:
    list: Список артикулов товаров.

    Examples:
        >>> get_offer_ids("client_123", "token_abc")
        ['art-001', 'art-002', 'art-003']

        >>> get_offer_ids("client_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Обновить цены товаров.

    Args:
        prices (list): Список словарей с новыми ценами на товар.
        client_id (str): ID продавца.
        seller_token (str): Токен авторизации магазина на озон.

    Returns:
        dict: Словарь с результатом операции.

    Examples:
        >>> test_prices = [{'auto_action_enabled': 'UNKNOWN', 'currency_code': 'RUB', 'offer_id': '101', 'old_price': '0', 'price': '3500'}]
        >>> update_price(test_prices, "client_123", "token_abc")
        {'result': [{'offer_id': 'art-101', 'updated': True}]}

        >>> test_prices = [{'auto_action_enabled': 'UNKNOWN', 'currency_code': 'RUB', 'offer_id': '101', 'old_price': '0', 'price': '3500'}]
        >>> update_price(test_prices, "client_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновить остатки.
    Args:
        stocks (list): Список словарей с остатками товара.
        client_id (str): ID продавца.
        seller_token (str): Токен авторизации магазина на озон.

    Returns:
        dict: Словарь с результатом операции.

    Examples:
        >>> update_stocks([{'offer_id': 'art-001', 'stock': 10}], "client_123", "token_abc")
        {'result': [{'offer_id': 'art-001', 'updated': True}]}

        >>> update_stocks([{'offer_id': 'art-001', 'stock': 10}], "client_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачать файл ostatki с сайта casio.

    Returns:
        list: Список словарей с остатками товара.

    Examples:
        >>> download_stock()
        [{'Код': '101', 'Количество': '5', 'Цена': "3'500"}, {'Код': '102', 'Количество': '7', 'Цена': "4'200"}]

        >>> download_stock()
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    # Скачать остатки с сайта
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    # Создаем список остатков часов:
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")  # Удалить файл
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Собрать данные об остатках товара в магазине озон.

    Args:
        watch_remnants (list): Список остатков товара в магазине поставщике.
        offer_ids (list): Список артикулов товара в магазине озон.

    Returns:
        list: Список словарей с остатками товара в магазине озон.

    Examples:
        >>> create_stocks(([{'Код': '101', 'Количество': '5', 'Цена': "3'500"}], ['101']))
        [{'offer_id': 'art-001', 'stock': 10}, {'offer_id': 'art-002', 'stock': 12}]

        >>> create_stocks(([{'Код': '101', 'Количество': '5', 'Цена': "3'500"}], ['101']))
        Traceback (most recent call last):
        ValueError: invalid literal for int() with base 10: ...
    """

    # Уберем то, что не загружено в seller
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создать цены товарам магазина озон из цен остатков поставщика.

    Args:
        watch_remnants (list): Список остатков товара в магазине поставщике.
        offer_ids (list): Список артикулов товара в магазине озон.

    Returns:
        list: Список словарей с ценами товаров в магазине озон.

    Examples:

        >>> create_prices([{'Код': '101', 'Количество': '5', 'Цена': "3'500"}], ['101'])
        [{'auto_action_enabled': 'UNKNOWN', 'currency_code': 'RUB', 'offer_id': '101', 'old_price': '0', 'price': '3500'}]

        >>> create_prices([{'Код': '101', 'Количество': '5', 'Цена': "3'500"}], ['101'])
        Traceback (most recent call last):
        AttributeError: 'int' object has no attribute 'split'
    """

    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразовать цену. Пример: 5'990.00 руб. -> 5990

    Args:
        price (str): Строка с ценой, например "5'990.00 руб.".

    Returns:
        str: Строка только из цифр целой части цены, например "5990".

    Examples:
        >>> price_conversion("5'990.00")
        '5990'

        >>> price_conversion(5990)
        Traceback (most recent call last):
        AttributeError: 'int' object has no attribute 'split'
    """

    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Разделить список lst на части по n элементов.

    Args:
        lst (list): Список для разделения.
        n (int): Количество элементов.

    Returns:
        generator: Генератор, возвращающий части исходного списка.

    Examples:
        >>> divide([1, 2, 3, 4, 5], 2))
        [[1, 2], [3, 4], [5]]

        >>> divide([1, 2], 0))
        Traceback (most recent call last):
        ValueError: range() arg 3 must not be zero
    """

    for i in range(0, len(lst), n):
        yield lst[i: i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Выгрузить обновленные цены товаров в магазин озон.

    Args:
        watch_remnants (list): Остатки товаров на сайте поставщика.
        client_id (str): ID продавца.
        seller_token (str): Токен авторизации магазина на озон.

    Returns:
        list: Список обновленных цен.

    Examples:
        >>> test_remnants = [{'Код': '102', 'Количество': '7', 'Цена': "4'200"}]
        >>> await upload_prices(test_remnants, "client_123", "token_abc")
        [{'auto_action_enabled': 'UNKNOWN', 'currency_code': 'RUB', 'offer_id': '101', 'old_price': '0', 'price': '4200'}]

        >>> test_remnants = [{'Код': '102', 'Количество': '7', 'Цена': "4'200"}]
        >>> await upload_prices(test_remnants, "client_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Выгрузить обновленные остатки товаров в магазин озон.

    Args:
        watch_remnants (list): Остатки товаров на сайте поставщика.
        client_id (str): ID продавца.
        seller_token (str): Токен авторизации магазина на озон.

    Returns:
        tuple: Кортеж обновленных остатков.

    Examples:
        >>> test_remnants = [{'Код': '101', 'Количество': '5'}]
        >>> await upload_stocks(test_remnants, "client_123", "token_abc")
        ([{'offer_id': '101', 'stock': 5}], [{'offer_id': '101', 'stock': 5}])

        >>> test_remnants = [{'Код': '101', 'Количество': '5'}]
        >>> await upload_stocks(test_remnants, "client_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()

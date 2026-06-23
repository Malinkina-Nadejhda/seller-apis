import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """Получить список товаров Яндекс Маркета.
    Args:
        page (str): id страницы для пагинации.
        campaign_id (str): ID компании.
        access_token (str): Токен к API яндекса.

    Returns:
        dict: Словарь со списками товаров, токен следующей страницы для пагинации.

    Examples:
        >>> get_product_list("", "campaign_123", "token_abc")
        {'offerMappingEntries': [{'offer': {'shopSku': 'art-001'}}], 'paging': {'nextPageToken': 'page_2'}}

        >>> get_product_list("", "campaign_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """Обновить остатки.

    Args:
        stocks (list): Список словарей с остатками товара.
        campaign_id (str): ID компании.
        access_token (str): Токен к API яндекса.

    Returns:
        dict: Словарь с результатом операции.

    Examples:
        >>> test_stocks = [{'sku': '101', 'warehouseId': 999, 'items': [{'count': 5, 'type': 'FIT', 'updatedAt': '2026-06-20T11:11:00Z'}]}]
        >>> update_stocks(test_stocks, "id_123", "token_abc")
        {'status': 'OK'}

        >>> test_stocks = [{'sku': '101', 'warehouseId': 999, 'items': [{'count': 5, 'type': 'FIT', 'updatedAt': '2026-06-20T11:11:00Z'}]}]
        >>> update_stocks(test_stocks, "id_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """Обновить цены товаров.

    Args:
        prices (list): Список словарей с новыми ценами на товар.
        campaign_id (str): ID компании.
        access_token (str): Токен к API яндекса.

    Returns:
        dict: Словарь с результатом операции.

    Examples:
        >>> test_prices = [{'id': '101', 'price': {'value': 3500, 'currencyId': 'RUR'}}]
        >>> update_price(test_prices, "id_123", "token_abc")
        {'status': 'OK'}

        >>> test_prices = [{'id': '101', 'price': {'value': 3500, 'currencyId': 'RUR'}}]
        >>> update_price(test_prices, "id_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Получить артикулы товаров Яндекс маркета.
    Args:
        campaign_id (str): ID компании.
        market_token (str): Токен авторизации магазина яндекс.

    Returns:
        list: Список артикулов товаров.

    Examples:
        >>> get_offer_ids("campaign_123", "token_abc")
        ['art-001', 'art-002', 'art-003']

        >>> get_offer_ids("campaign_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Сформировать остатки товара в магазине яндекс.

    Args:
        watch_remnants (list): Список остатков товара в магазине поставщике.
        offer_ids (list): Список артикулов товара в магазине яндекс.
        warehouse_id (int): Id склада.

    Returns:
        list: Список словарей с остатками товара в магазине яндекс.

    Examples:
        >>> test_remnants = [{'Код': '101', 'Количество': '5'}]
        >>> create_stocks(test_remnants, ['101'], 999)
        [{'sku': '101', 'warehouseId': 999, 'items': [{'count': 5, 'type': 'FIT', 'updatedAt': '2026-06-20T11:11:00Z'}]}]

        >>> test_remnants_error = [{'Код': '101', 'Количество': 'много'}]
        >>> create_stocks(test_remnants_error, ['101'], 999)
        Traceback (most recent call last):
        ValueError: invalid literal for int() with base 10: ...
    """

    # Уберем то, что не загружено в market
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создать цены товарам магазина яндекс из цен остатков поставщика.

    Args:
        watch_remnants (list): Список остатков товара в магазине поставщике.
        offer_ids (list): Список артикулов товара в магазине яндекс.

    Returns:
        list: Список словарей с ценами товаров в магазине яндекс.

    Examples:
        >>> test_remnants = [{'Код': '101', 'Цена': "3'500"}]
        >>> create_prices(test_remnants, ['101'])
        [{'id': '101', 'price': {'value': 3500, 'currencyId': 'RUR'}}]

        >>> test_remnants = [{'Код': '101', 'Цена': "3'500"}]
        >>> create_prices(test_remnants, ['101'])
        Traceback (most recent call last):
        AttributeError: 'int' object has no attribute 'split'
    """

    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    """Выгрузить обновленные цены товаров в магазин яндекс.

    Args:
        watch_remnants (list): Остатки товаров на сайте поставщика.
        campaign_id (str): ID компании.
        market_token (str): Токен авторизации магазина яндекс.

    Returns:
        list: Список обновленных цен.

    Examples:
        >>> test_remnants = [{'Код': '101', 'Цена': "3'500"}]
        >>> await upload_prices(test_remnants, "id_123", "token_abc")
        [{'id': '101', 'price': {'value': 3500, 'currencyId': 'RUR'}}]

        >>> test_remnants = [{'Код': '101', 'Цена': "3'500"}]
        >>> await upload_prices(test_remnants, "id_123", "token_abc")
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    """Выгрузить обновленные остатки товаров в магазин яндекс.

    Args:
        watch_remnants (list): Остатки товаров на сайте поставщика.
        campaign_id (str): ID компании.
        market_token (str): Токен авторизации магазина яндекс.
        warehouse_id (int): ID склада.

    Returns:
        tuple: Кортеж обновленных остатков.

    Examples:
        >>> test_remnants = [{'Код': '101', 'Количество': '5'}]
        >>> await upload_stocks(test_remnants, "id_123", "token_abc", 999)
        ([{'sku': '101', 'warehouseId': 999, 'items': [{'count': 5, 'type': 'FIT', 'updatedAt': '2026-06-20T11:11:00Z'}]}],
        [{'sku': '101', 'warehouseId': 999, 'items': [{'count': 5, 'type': 'FIT', 'updatedAt': '2026-06-20T11:11:00Z'}]}])

        >>> test_remnants = [{'Код': '101', 'Количество': '5'}]
        >>> await upload_stocks(test_remnants, "id_123", "token_abc", 999)
        Traceback (most recent call last):
        requests.exceptions.ConnectionError: ...
    """

    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()

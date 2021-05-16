from typing import Any, Dict, Optional
import datetime as dt
import pytz
import tzlocal
import requests
import lxml.html
from telegram import message


def get_current_ticker_info(ticker: str) -> Optional[Dict[str, Any]]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?region=US&lang=en-US&includePrePost=false&interval=2m&useYfid=true&range=1d&corsDomain=finance.yahoo.com&.tsrc=finance"
    try:
        r = requests.get(url)
        meta = r.json()["chart"]["result"][0]["meta"]
        local_time_zone = tzlocal.get_localzone()
        market_time_zone = pytz.timezone(meta["exchangeTimezoneName"])
        last_update_datetime = dt.datetime.fromtimestamp(meta["regularMarketTime"], tz=local_time_zone).astimezone(tz=market_time_zone)
        current_price = meta["regularMarketPrice"]
        previous_close_price = meta["previousClose"]
        absolute_price_change = current_price - previous_close_price
        percentage_price_change = 100 * absolute_price_change / previous_close_price
        return {
            "current_price": current_price,
            "absolute_price_change": absolute_price_change,
            "percentage_price_change": percentage_price_change,
            "last_update_datetime": last_update_datetime,
        }
    except Exception as e:
        print(e)
        return None


def get_current_ticker_price_from_yahoo_finance(ticker: str) -> Optional[Dict[str, float]]:
    BASE_URL = "https://finance.yahoo.com/quote"
    CURRENT_PRICE_XPATH = "/html/body/div[1]/div/div/div[1]/div/div[2]/div/div/div[4]/div/div/div/div[3]/div[1]/div/span[1]/text()"
    PRICE_CHANGE_XPATH = "/html/body/div[1]/div/div/div[1]/div/div[2]/div/div/div[4]/div/div/div/div[3]/div[1]/div/span[2]/text()"
    url = f"{BASE_URL}/{ticker}"

    try:
        r = requests.get(url)
        root = lxml.html.fromstring(r.content)
        current_price_text = root.xpath(CURRENT_PRICE_XPATH)[0].translate({ord(c): None for c in ","})
        price_change_texts = root.xpath(PRICE_CHANGE_XPATH)[0].translate({ord(c): None for c in ",()%"}).split()
        current_price = float(current_price_text)
        absolute_price_change, percentage_price_change = float(price_change_texts[0]), float(price_change_texts[1])
        return {
            "current_price": current_price,
            "absolute_price_change": absolute_price_change,
            "percentage_price_change": percentage_price_change,
        }
    except Exception as e:
        print(e)
        return None

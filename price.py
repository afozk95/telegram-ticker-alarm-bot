from typing import Dict, Optional
import requests
import lxml.html


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

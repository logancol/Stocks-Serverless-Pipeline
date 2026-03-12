import logging
from datetime import date
import requests
import random
from time import sleep
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger()


def fetch_biggest_mover(watchlist: list[str], *, use_date: date = None, per_symbol_delay_seconds: float = 10) -> tuple[str, float, float]:
    """
    Gets open, close data and calculates biggest mover with retry

    Note that rate limit for free tier is 5 requests per minute https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis
    This might have to take about a minute relying on the given endpoint.

    Returns (symbol, percentage movement, closing price) for the biggest mover
    """
    if use_date is None:
        use_date = date.today()

    biggest_mover = ""
    biggest_movement = 0.0
    biggest_close_price = 0.0
    for symbol in watchlist:
        open_close = fetch_stock_data(symbol, use_date=use_date)
        movement = calculate_movement(open_close)
        if movement == None:
            continue
        if abs(movement) > abs(biggest_movement):
            biggest_movement = movement
            biggest_mover = symbol
            biggest_close_price = open_close[1]

        # sleep even on success to avoid hitting the rate limit
        if per_symbol_delay_seconds and per_symbol_delay_seconds > 0:
            jitter = random.uniform(0, 1.0)
            sleep(per_symbol_delay_seconds + jitter)
    
    return biggest_mover, biggest_movement, biggest_close_price
    

def fetch_stock_data(symbol: str, use_date = None, max_attempts: int = 5):
    """
    Fetching open/close data per symbol with retry

    Returns a tuple containing the open and close prices for that day
    """
    if use_date is None:
        use_date = date.today()

    logger.info(f"Fetching open/close for symbol: {symbol}, date: {use_date}")
    api_key = os.getenv("MASSIVE_API_KEY")
    if not api_key:
        logger.error("MASSIVE_API_KEY is not set")
        return None

    params = {"apiKey": api_key}
    url = f"https://api.massive.com/v1/open-close/{symbol}/{use_date}"
    for call_attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            open_price = float(data["open"])
            close_price = float(data["close"])
            logger.info(f"Successful open/close retrieval for symbol: {symbol} date: {use_date}")
            return (open_price, close_price)

        except Exception as e:
            if call_attempt == max_attempts:
                logger.error(f"Could not fetch data for symbol: {symbol}, in {max_attempts} attempts")
                return None
            else:
                # Avoid logging exception text because requests may include the full URL.
                logger.warning(f"Problem fetching Massive open/close symbol={symbol} date={use_date}, retrying")
                jitter = random.uniform(0, 3.0)
                sleep(10 + jitter)
    return None

def calculate_movement(data):
    """
    Calculates movement percentage based on given formula

    Returns percentage
    """
    if not data:
        return None
    open_price, close_price = data
    return ((close_price - open_price) / open_price) * 100
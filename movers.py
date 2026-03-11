import logging
from datetime import date, timedelta
import requests
import random
from time import sleep
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger()


def fetch_biggest_mover(watchlist: list[str]) -> tuple:
    """
    Fetching open, close data and calculating biggest mover with retry

    Note that rate limit for free tier is 5 requests per minute https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis
    This might have to take about a minute relying on the given endpoint.

    Returns the symbol and percentage movement for the biggest mover
    """
    biggest_mover = ""
    biggest_movement = 0.0
    for symbol in watchlist:
        open_close = fetch_stock_data(symbol)
        movement = calculate_movement(open_close)
        if movement == None:
            continue
        if abs(movement) > abs(biggest_movement):
            biggest_movement = movement
            biggest_mover = symbol
    
    return biggest_mover, biggest_movement
    

def fetch_stock_data(symbol: str, date = None, max_attempts: int = 5):
    """
    Fetching open/close data per symbol with retry

    Returns a tuple containing the open and close prices for that day
    """
    if date == None:
        date = date.today()

    logger.info(f"Fetching open/close for symbol: {symbol}, date: {date}")
    params = {
        "apiKey": os.getenv("MASSIVE_API_KEY")
    }
    url = f"https://api.massive.com/v1/open-close/{symbol}/{date}"
    for call_attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            data = response.json()
            open_price = float(data["open"])
            close_price = float(data["close"])
            logger.info(f"Successful open/close retrieval for symbol: {symbol} date: {date}")
            return (open_price, close_price)
        
        except Exception as e:
            if call_attempt == max_attempts:
                logger.error(f"Could not fetch data for symbol: {symbol}, in {max_attempts} attempts")
                return None
            else:
                logger.warning(f"Problem fetching open, close data from massive api: {e} with symbol: {symbol}, date: {date}, will retry: {max_attempts - call_attempt} more times.")
                jitter = random.uniform(0, 1.0)
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
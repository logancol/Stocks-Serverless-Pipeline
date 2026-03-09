import logging
from datetime import date, timedelta
import requests
import json
import random
from time import sleep
from dotenv import load_dotenv
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger()

# https://www.youtube.com/watch?v=UllPQzVXYtU&t=1s video docs

load_dotenv()

"""
AWS Lambda function that connects to a stock api, iterates through the watchlist, and
calculates which stock had the highest percentage change for the day.
"""

WATCHLIST = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]


def lambda_hander(event, _):
    """
    Lambda handler that wraps mover fetching and logging behavior
    """
    amount = 100
    response = {
        "statusCode": 200,
        "body": json.dumps({'result': amount})
    }
    logger.info('Response succesfully returnd : %s', response)
    return response


def fetch_biggest_mover(watchlist: list[str], max_attempts: int = 5) -> tuple:
    """
    Fetching open, close data and calculating biggest mover with retry

    Note that rate limit for free tier is 5 requests per minute https://massive.com/knowledge-base/article/what-is-the-request-limit-for-massives-restful-apis
    This might have to take about a minute.
    """
    logger.info("Fetching biggest movers ...")
    biggest_mover = None
    biggest_movement = 0
    params = {
        "apiKey": os.getenv("MASSIVE_API_KEY")
    }
    today = date.today()
    query_date = today - timedelta(days=5)
    for symbol in watchlist:
        url = f"https://api.massive.com/v1/open-close/{symbol}/{query_date}"
        for call_attempt in range(1, max_attempts + 1):
            try:
                response = requests.get(url, params=params, timeout=5)
                response.raise_for_status()
                data = response.json()

                open_price = float(data["open"])
                close_price = float(data["close"])
                movement = ((close_price - open_price) / open_price) * 100

                logger.info(f"Successful open/close retrieval for symbol: {symbol}")
                if abs(movement) > abs(biggest_movement):
                    print("symbol set")
                    biggest_movement = movement
                    biggest_mover = symbol
                    logger.info(f"Movement for symbol {symbol} is {movement}")
                sleep(15)
                break

            except Exception as e:
                if call_attempt == max_attempts:
                    logger.error(
                        f"Could not fetch data for symbol: {symbol}, in {max_attempts} attempts"
                        )
                    return None
                
                else:
                    logger.warning(
                        f"Problem fetching open, close data from massive api: {e} with symbol: {symbol}, date: {query_date}, will retry: {max_attempts - call_attempt} more times."
                        )
                    jitter = random.uniform(0, 1.0)
                    sleep(3.0 + jitter)

    logger.info(f"{query_date} biggest mover is {biggest_mover} with movement: {biggest_movement}")                
    if biggest_mover == None:
        return None

    return (biggest_mover, biggest_movement)

def main(): # example usage
    fetch_biggest_mover(WATCHLIST, max_attempts=5)

if __name__ == "__main__":
    main()
import logging
import json
from dotenv import load_dotenv
from movers import fetch_biggest_mover

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()
load_dotenv()

"""
AWS Lambda function that connects to a stock api, iterates through the watchlist, and
calculates which stock had the highest percentage change for the day.
"""

WATCHLIST = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]


def lambda_handler(event, _):
    """
    Lambda handler that wraps mover fetching and logging behavior
    """
    
    try:
        mover = fetch_biggest_mover(WATCHLIST)
        response = {
            "statusCode": 200,
            "body": json.dumps({'biggest_mover': mover})
        }
        logger.info(f"Lamda succeeded: {mover}")
        return response
    
    except Exception as e:
        logger.error(f"Lambda failed: {e}")
        return {
            "statusCode": 500, 
            "body": json.dumps({
                "error": "Problem computing biggest mover"
            })
        }

import logging
import json
import os
from datetime import timedelta, date
from decimal import Decimal
import boto3

from movers import fetch_biggest_mover

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

"""
Lambda function that connects to massive, iterates through the watchlist, and
calculates which stock had the highest percentage change for the day.
"""

WATCHLIST = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]


def lambda_handler(event, _):
    """
    Lambda handler that wraps mover fetching and logging behavior
    """
    try:
        dt = date.today()
        use_date = dt.isoformat()
        winner_symbol, percent_change, close_price = fetch_biggest_mover(WATCHLIST, use_date=dt)

        if not winner_symbol:
            raise RuntimeError("No winner computed (all symbols failed)")

        table_name = os.getenv("DYNAMODB_TABLE_NAME")
        if not table_name:
            raise RuntimeError("Missing env var DYNAMODB_TABLE_NAME")

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        item = {
            "date": use_date,
            "ticker_symbol": winner_symbol,
            "percent_change": Decimal(str(percent_change)),
            "closing_price": Decimal(str(close_price)),
        }
        table.put_item(Item=item)

        response_item = {
            "date": use_date,
            "ticker_symbol": winner_symbol,
            "percent_change": float(percent_change),
            "closing_price": float(close_price),
        }

        return {
            "statusCode": 200,
            "body": json.dumps({"stored": True, "winner": response_item}),
        }
    
    except Exception as e:
        logger.error("Movement lambda failed")
        return {
            "statusCode": 500, 
            "body": json.dumps({
                "error": "Problem computing biggest mover"
            })
        }

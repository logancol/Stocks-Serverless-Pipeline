import logging
import json
import os
from datetime import timedelta, date, datetime, time
from decimal import Decimal
import boto3

from movers import fetch_biggest_mover
from zoneinfo import ZoneInfo

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger()

WATCHLIST = ["AAPL","MSFT","GOOGL","AMZN","TSLA","NVDA"]
CLOSE_BUFFER_MINUTES = 5
MARKET_CLOSE_ET = time(16, 0)
MARKET_TZ = ZoneInfo("America/New_York")

# rollback to previous weekday if call to lambda happens before close time
def effective_market_date(now_et: datetime | None = None) -> date:
    if now_et is None:
        now_et = datetime.now(tz=MARKET_TZ)

    today = now_et.date()
    close_dt = datetime.combine(today, MARKET_CLOSE_ET, tzinfo=MARKET_TZ) + timedelta(minutes=CLOSE_BUFFER_MINUTES)

    use_date = today if now_et >= close_dt else (today - timedelta(days=1))
    # if its before 4 pm on a monday, we go back to friday. 
    while use_date.weekday() >= 5:
        use_date -= timedelta(days=1)

    return use_date


def lambda_handler(event, _):
    """
    Lambda handler that wraps mover fetching and logging behavior
    """
    try:
        use_date = effective_market_date()
        use_date_str = use_date.isoformat()
        winner_symbol, percent_change, close_price = fetch_biggest_mover(WATCHLIST, use_date=use_date)

        if not winner_symbol:
            raise RuntimeError("No winner computed (all symbols failed)")

        table_name = os.getenv("DYNAMODB_TABLE_NAME")
        if not table_name:
            raise RuntimeError("Missing env var DYNAMODB_TABLE_NAME")

        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        item = {
            "date": use_date_str,
            "ticker_symbol": winner_symbol,
            "percent_change": Decimal(str(percent_change)),
            "closing_price": Decimal(str(close_price)),
        }
        table.put_item(Item=item)

        response_item = {
            "date": use_date_str,
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

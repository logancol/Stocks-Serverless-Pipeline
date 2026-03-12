import json
import logging
import os
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

"""
Lambda function that connects to the dynamodb, gets the winners, and returns the 7 most recent ones (if 7 present).

I interpretted "last 7 days of winning stocks" to imply avoiding non-trading days in the time frame
"""

def _cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }


def lambda_handler(event, _context):
    """API Lambda: return last 7 winning stocks from DynamoDB."""

    method = (event.get("httpMethod") or event.get("requestContext", {}).get("http", {}).get("method") or "").upper()
    if method == "OPTIONS":
        return {"statusCode": 204, "headers": _cors_headers(), "body": ""}

    table_name = os.getenv("DYNAMODB_TABLE_NAME")
    dynamodb = boto3.resource("dynamodb")
    table = dynamodb.Table(table_name)

    try:
        resp = table.scan()
        items = resp.get("Items", [])

        items.sort(key=lambda x: x.get("date", ""), reverse=True) # get most recent logged days
        last_7 = items[:7] # "last 7 days of "Winning Stocks"

        # succesfully located the winners
        return {
            "statusCode": 200,
            "headers": {**_cors_headers(), "Content-Type": "application/json"},
            "body": json.dumps({"winners": last_7}, default=str),
        }

    except Exception as exc:
        # problem accessing the db 
        logger.exception("Failed reading DynamoDB: %s", exc)
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": "Problem retrieving movers"}, default=str),
        }

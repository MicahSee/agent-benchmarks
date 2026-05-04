import boto3
import os

_table = None


def get_table():
    global _table
    if _table is None:
        dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))
        _table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "benchmark_runs"))
    return _table

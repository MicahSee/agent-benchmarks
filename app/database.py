import boto3
import os

_table = None
_api_keys_table = None
_users_table = None


def _dynamodb():
    return boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def get_table():
    global _table
    if _table is None:
        _table = _dynamodb().Table(os.environ.get("DYNAMODB_TABLE", "benchmark_runs"))
    return _table


def get_api_keys_table():
    global _api_keys_table
    if _api_keys_table is None:
        _api_keys_table = _dynamodb().Table(os.environ.get("API_KEYS_TABLE", "api_keys"))
    return _api_keys_table


def get_users_table():
    global _users_table
    if _users_table is None:
        _users_table = _dynamodb().Table(os.environ.get("USERS_TABLE", "users"))
    return _users_table

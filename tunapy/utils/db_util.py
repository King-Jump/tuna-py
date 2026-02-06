""" the singleton of redis client
    update:uding ConnectionPool
"""
import json
import redis
from redis import ConnectionPool
from functools import lru_cache

REDIS_CONFIG = {
    "host": "127.0.0.1", "port": 6379, "password": "",
    "max_connections": 5,
    "socket_connect_timeout": 1,
    "health_check_interval": 30,
    "decode_responses": True,
}

pool = ConnectionPool(**REDIS_CONFIG)

@lru_cache(maxsize=1)
def get_conn():
    try:
        conn = redis.Redis(connection_pool=pool)
        if conn.ping():
            return conn
    except redis.RedisError:
        raise ConnectionError("Local node unavailable")


def RDB():
    try:
        conn = get_conn()
        if conn and conn.ping():
            # print("using cache_conn")
            return conn
        get_conn.cache_clear()
    except (redis.RedisError, ConnectionError):
        get_conn.cache_clear()

    raise ConnectionError("Redis server unavailable")


# fundamental API
def get_int(key: str) -> int:
    """ get int value
    """
    res = RDB().get(key)
    if res:
        return int(res)
    return res

def get_float(key: str) -> float:
    """ get float value
    """
    res = RDB().get(key)
    if res:
        return float(res)
    return 0.0

def set_float(key: str, value: float):
    """ set float value
    """
    if key:
        RDB().set(key, float(value))

def get_dict(key: str) -> dict:
    """ get dict object
    """
    res = RDB().get(key)
    if res:
        return json.loads(res)
    return res

def set_dict(key: str, value: dict):
    """ set dict object
    """
    if key and value:
        RDB().set(key, json.dumps(value))

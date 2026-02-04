import json
from functools import lru_cache

import redis
from redis import ConnectionError

REDIS_CONFIG = {
    "host": "127.0.0.1", "port": 6379, "password": "",
    "max_connections": 5,
    "socket_connect_timeout": 1,
    "health_check_interval": 30,
    "decode_responses": True,
}

@lru_cache(maxsize=1)
def _get_conn():
    conn = redis.Redis(**REDIS_CONFIG)
    if conn.ping():
        return conn

def RDB():
    try:
        conn = _get_conn()
        if conn and conn.ping():
            #print("using cache_conn")
            return conn
        _get_conn.cache_clear()
    except (redis.RedisError, ConnectionError):
        _get_conn.cache_clear()

    raise ConnectionError("Redis server unavailable")

def load_config(redis_key: str, prev_version: int) -> list:
    """ Load configuration from Redis by key.
    """
    config = []
    if redis_key:
        conn = RDB()
        if conn:
            version = conn.get(f'{redis_key}_version')
            if version and int(version) > prev_version:
                value = conn.get(f'{redis_key}_data')
                if value:
                    if type(value) is bytes:
                        value = value.decode('utf-8')
                    return int(version), json.loads(value)
    return 0, config

def load_config_str(redis_key: str, prev_version: int):
    """ Load configuration from Redis by key.
    """
    config = []
    if redis_key:
        conn = RDB()
        if conn:
            version = conn.get(f'{redis_key}_version')
            if version and int(version) > prev_version:
                value = conn.get(f'{redis_key}_data')
                if value:
                    if type(value) is bytes:
                        value = value.decode('utf-8')
                    return int(version), value
    return 0, "[]"

def set_config(redis_key: str, configs: dict) -> bool:
    """ Set configuration from Redis by key.
    """
    if redis_key:
        conn = RDB()
        if conn:
            version = conn.get(f'{redis_key}_version')
            conn.set(f'{redis_key}_data', json.dumps(configs))
            conn.set(f'{redis_key}_version', int(version) + 1)
    return True

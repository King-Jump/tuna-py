""" Redis client based on db_util
"""
import os
import sys
import json
import time

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    
from tunapy.utils.db_util import RDB, get_int, get_float, set_float, get_dict

ONE_MIN_HUNDRED_MS = 600
class DATA_REDIS_CLIENT:
    """
    # fundamental API
    """
    @classmethod
    def set_int(cls, key: str, value:int):
        """ set int value
        """
        if key:
            RDB().set(key, int(value))

    @classmethod
    def get_int(cls, key: str) -> int:
        """ get int value
        """
        return get_int(key)

    @classmethod
    def get_float(cls, key: str) -> float:
        """ get float value
        """
        return get_float(key)

    @classmethod
    def set_float(cls, key: str, value: float):
        """ set float value
        """
        return set_float(key, value)
        
    @classmethod
    def get_dict(cls, key: str) -> dict:
        """ get dict object
        """
        return get_dict(key)

    @classmethod
    def set_dict(cls, key: str, value: dict):
        """ set dict object
        """
        if key and value:
            RDB().set(key, json.dumps(value))
            
    @classmethod
    def get_ticker(cls, symbol_key:str):
        ts = int(time.time()*10)
        current_tag = ts % ONE_MIN_HUNDRED_MS
        # backforward to last minute
        for prev_tag in range(current_tag, current_tag - ONE_MIN_HUNDRED_MS, -1):
            tag = (prev_tag + ONE_MIN_HUNDRED_MS) % ONE_MIN_HUNDRED_MS  # prev_tag may less than zero
            _key=f'{symbol_key}{tag}'
            t1 = cls.get_int(_key)
            if t1 and ts-ONE_MIN_HUNDRED_MS < t1 <= ts:
                prev_ticker = cls.get_dict(f'{_key}_value')
                if prev_ticker:
                    return prev_ticker  # nearest ticker
        return None # fail to get previous ticker
    
    @classmethod
    def get_order_book(cls, symbol_key:str):
        """ get order book
        """
        ts = int(time.time()*10)
        current_tag = ts % ONE_MIN_HUNDRED_MS
        # backforward to last minute
        for prev_tag in range(current_tag, current_tag - ONE_MIN_HUNDRED_MS, -1):
            tag = (prev_tag + ONE_MIN_HUNDRED_MS) % ONE_MIN_HUNDRED_MS  # prev_tag may less than zero
            _key=f'{symbol_key}{tag}'
            t1 = cls.get_int(_key)
            if t1 and ts-ONE_MIN_HUNDRED_MS < t1 <= ts:
                prev_order_book = cls.get_dict(f'{_key}_value')
                if prev_order_book:
                    return prev_order_book  # nearest order_book
        return None # fail to get previous order_book

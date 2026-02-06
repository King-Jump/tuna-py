""" Binance Quote on WS
"""
import os
import time
import ujson

from binance.websocket.spot.websocket_stream import SpotWebsocketStreamClient
from management.redis_client import DATA_REDIS_CLIENT
from octopuspy.utils.log_util import create_logger

# one munite = 600 * 100 ms
ONE_MIN_HUNDRED_MS = 600
# binance spot partial depth
EXCHANGE_DEPTH_PREFIX = 'depth'
# binance spot ticker
EXCHANGE_TICKER_PREFIX = 'ticker'

CURR_PATH = os.path.dirname(os.path.abspath(__file__))
LOGGER = create_logger(os.path.join(CURR_PATH, 'log'), "bn_pubws.log", "BN-PUBWS", 10)

def _key(tag, ts):
    """ BiNance Spot
        The update period of Binance WS is 100ms.
        1 minutes have 60 * 10 = 600 (100ms)
    """
    return f'{EXCHANGE_DEPTH_PREFIX}{tag}{ts % ONE_MIN_HUNDRED_MS}'

def _handle_orderbook_depth(rkey: str, req_ts: int, data: dict) -> dict:
    order_book = {
        'asks': sorted([(float(a), float(q)) for a, q in data['asks']], key=lambda x: x[0]),
        'bids': sorted([(float(b), float(q)) for b, q in data['bids']], key=lambda x: x[0],
                       reverse=True),
    }
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', order_book)
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Depth %s, ask size=%d, bid size=%s',
                rkey, len(order_book['asks']), len(order_book['bids']))
    return order_book

def _handle_ticker(data: dict, req_ts: int) -> dict:
    symbol = data['data']['s']
    price = float(data['data']['p'])
    qty = float(data['data']['q'])

    rkey = f'{EXCHANGE_TICKER_PREFIX}{symbol}{req_ts % ONE_MIN_HUNDRED_MS}'
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', {'price': price, 'qty': qty})
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Tick %s, price=%s, qty=%s', symbol, price, qty)

def message_handler(_, message):
    ''' thread and message
    '''
    message = ujson.loads(message)
    if 'stream' in message:
        req_ts = int(10 * time.time())
        if 'depth' in message['stream']:
            pair, _, _ = message['stream'].split('@')
            rkey = _key(pair, req_ts)
            # order book partial depth
            _handle_orderbook_depth(rkey, req_ts, message['data'])

        elif 'aggTrade' in message['stream']:
            _handle_ticker(message, req_ts)


def error_handler(_, message):
    LOGGER.error(message)

def bn_subscribe(depth_symbols: list[str], ticker_symbols: list[str]):
    """ subscribe partial depth or ticker of given symbols
    """
    ws = SpotWebsocketStreamClient(on_message=message_handler, on_error=error_handler,
                                   is_combined=True)
    topics = []
    for symbol in depth_symbols:
        symbol = symbol.lower()
        topics.append(f'{symbol}@depth20@100ms')
    for symbol in ticker_symbols:
        topics.append(f'{symbol}@aggTrade')

    ws.subscribe(stream=topics)

    while 1:
        time.sleep(1)

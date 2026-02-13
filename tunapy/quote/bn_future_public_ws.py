""" Binance Future Quote on WS
"""
import os
import sys
import time
import ujson

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURR_DIR))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
    
from binance.websocket.um_futures.websocket_client import UMFuturesWebsocketClient
from tunapy.quote.redis_client import DATA_REDIS_CLIENT
from octopuspy.utils.log_util import create_logger

# one munite = 600 * 100 ms
ONE_MIN_HUNDRED_MS = 600
# binance future partial depth
EXCHANGE_FUTURE_DEPTH_PREFIX = 'binance_future_depth'
# binance future ticker
EXCHANGE_FUTURE_TICKER_PREFIX = 'binance_future_ticker'

CURR_PATH = os.path.dirname(os.path.abspath(__file__))
LOGGER = create_logger(BASE_DIR, "bn_future_pub_ws.log", "BN-FUTURE-PUBWS", 10)

# Global variables for reconnection
WS_CLIENT = None
DEPTH_SYMBOLS = []
TICKER_SYMBOLS = []

def _key(tag, ts):
    """ BiNance Future
        The update period of Binance WS is 100ms.
        1 minutes have 60 * 10 = 600 (100ms)
    """
    return f'{EXCHANGE_FUTURE_DEPTH_PREFIX}{tag}{ts % ONE_MIN_HUNDRED_MS}'

def _handle_orderbook_depth(rkey: str, req_ts: int, data: dict) -> dict:
    # import pdb; pdb.set_trace()
    order_book = {
        'asks': sorted([(float(a), float(q)) for a, q in data['a']], key=lambda x: x[0]),
        'bids': sorted([(float(b), float(q)) for b, q in data['b']], key=lambda x: x[0],
                       reverse=True),
    }
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', order_book)
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Future Depth %s, ask size=%d, bid size=%s',
                rkey, len(order_book['asks']), len(order_book['bids']))
    return order_book

def _handle_ticker(data: dict, req_ts: int) -> dict:
    symbol = data['data']['s'].lower()  # bn symbol default lowercase
    price = float(data['data']['p'])
    qty = float(data['data']['q'])
    rkey = f'{EXCHANGE_FUTURE_TICKER_PREFIX}{symbol}{req_ts % ONE_MIN_HUNDRED_MS}'
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', {'price': price, 'qty': qty})
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Future Tick %s, price=%s, qty=%s', rkey, price, qty)

def message_handler(_, message):
    ''' thread and message
    '''
    # import pdb; pdb.set_trace()
    message = ujson.loads(message)
    LOGGER.debug("message received: %s", message)
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
    while 1:
        try:
            LOGGER.error(f"WebSocket error: {message}, reconnecting...")
            # Recreate WebSocket client
            global WS_CLIENT, DEPTH_SYMBOLS, TICKER_SYMBOLS
            WS_CLIENT = UMFuturesWebsocketClient(on_message=message_handler, on_error=error_handler,
                                           on_close=close_handler, is_combined=True)
            
            # Resubscribe to topics
            topics = []
            for symbol in DEPTH_SYMBOLS:
                topics.append(f'{symbol.lower()}@depth20@100ms')
            for symbol in TICKER_SYMBOLS:
                topics.append(f'{symbol.lower()}@aggTrade')
            
            LOGGER.debug("Reconnecting to topics: %s", topics)
            WS_CLIENT.subscribe(stream=topics)
            LOGGER.info("WebSocket reconnected successfully after error")
            return
        except Exception as e:
            LOGGER.error("Failed to reconnect: %s", e)
            # Wait before retrying
            time.sleep(5)

def close_handler(_):
    while 1:
        try:
            LOGGER.info("WebSocket connection closed, reconnecting...")
            # Recreate WebSocket client
            global WS_CLIENT, DEPTH_SYMBOLS, TICKER_SYMBOLS
            WS_CLIENT = UMFuturesWebsocketClient(on_message=message_handler, on_error=error_handler,
                                            on_close=close_handler, is_combined=True)
            
            # Resubscribe to topics
            topics = []
            for symbol in DEPTH_SYMBOLS:
                topics.append(f'{symbol.lower()}@depth20@100ms')
            for symbol in TICKER_SYMBOLS:
                topics.append(f'{symbol.lower()}@aggTrade')
            
            LOGGER.debug("Reconnecting to topics: %s", topics)
            WS_CLIENT.subscribe(stream=topics)
            LOGGER.info("WebSocket reconnected successfully")
            return
        except Exception as e:
            LOGGER.error("Failed to reconnect: %s", e)
            # Wait before retrying
            time.sleep(5)

def bn_future_subscribe(depth_symbols: list[str], ticker_symbols: list[str]):
    """ subscribe partial depth or ticker of given symbols for future
    """
    global WS_CLIENT, DEPTH_SYMBOLS, TICKER_SYMBOLS
    
    # Save symbols for reconnection
    DEPTH_SYMBOLS = depth_symbols
    TICKER_SYMBOLS = ticker_symbols
    
    # Create WebSocket client
    WS_CLIENT = UMFuturesWebsocketClient(on_message=message_handler, on_error=error_handler,
                                   on_close=close_handler, is_combined=True)
    
    # Subscribe to topics
    topics = []
    for symbol in depth_symbols:
        topics.append(f'{symbol.lower()}@depth20@100ms')
    for symbol in ticker_symbols:
        topics.append(f'{symbol.lower()}@aggTrade')

    LOGGER.debug("bn future subscribe topics: %s", topics)
    WS_CLIENT.subscribe(stream=topics)

    while 1:
        time.sleep(1)

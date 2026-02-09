import os
import sys
import asyncio
import time
import traceback
import json
import threading
from okx.websocket.WsPublicAsync import WsPublicAsync

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURR_DIR))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from octopuspy.utils.log_util import create_logger
from management.redis_client import DATA_REDIS_CLIENT

CURR_PATH = os.path.dirname(os.path.abspath(__file__))
LOGGER = create_logger(BASE_DIR, "okx_future_pub_ws.log", "OKX-FUTURE-PUBWS", 10)

# Global variables for reconnection
WS_CLIENT = None
DEPTH_SYMBOLS = []
TICKER_SYMBOLS = []

OKX_FUTURE_PUB_WS_STREAM = 'wss://ws.okx.com:8443/ws/v5/public'
ORDER_BOOK = {}
BOOK_MESSAGE_BUFF = {}

# one munite = 600 * 100 ms
ONE_MIN_HUNDRED_MS = 600
# OKX future partial depth
EXCHANGE_FUTURE_DEPTH_PREFIX = 'future_depth'
# OKX future ticker
EXCHANGE_FUTURE_TICKER_PREFIX = 'future_ticker'

def _key(tag, ts):
    """ OKX Future
        The update period of OKX WS is 100ms.
        1 minutes have 60 * 10 = 600 (100ms)
    """
    return f'{tag}{ts % ONE_MIN_HUNDRED_MS}'

def _merge_ask_bid(ob_data, update_data):
    asks: dict = ob_data['asks']
    for price, qty, _, _ in update_data['asks']:
        if float(qty) == 0:
            del asks[price]
        else:
            asks[price] = qty
    sorted_asks = sorted(asks.items(), key=lambda x: float(x[0]), reverse=False)
    ob_data['asks'] = dict(sorted_asks)

    bids: dict = ob_data['bids']
    for price, qty, _, _ in update_data['bids']:
        if qty == 0:
            del bids[price]
        else:
            bids[price] = qty
    sorted_bids = sorted(bids.items(), key=lambda x: float(x[0]), reverse=True)
    ob_data['bids'] = dict(sorted_bids)

def _get_msg_time_info(ob):
    try:
        seqId = ob['seqId']
        prevSeqId = ob['prevSeqId']
        ob_ts = float(ob['ts'])
        return seqId, prevSeqId, ob_ts
    except Exception as e:
        LOGGER.error(e)
        return "-2", "-3", 0
    
def _merge_ob_fun(symbol: str, logger):
    ob = ORDER_BOOK[symbol]
    id1, _, obTs1 = _get_msg_time_info(ob)
    msg_buff = BOOK_MESSAGE_BUFF[symbol]
    t1 = time.time()
    l1 = len(msg_buff)
    while len(msg_buff) > 0:
        did_something = False
        for ob_msg in msg_buff:
            id2, prevId2, obTs2 = _get_msg_time_info(ob_msg['data'][0])
            if obTs2 < int(obTs1):
                logger.debug('skip book update [%s < %s]: %s', obTs2, obTs1, ob_msg)
                msg_buff.remove(ob_msg)
                did_something = True
                break
            elif prevId2 == id1:     # msg next to last orderbook update
                ob['seqId'] = id2
                ob['prevSeqId'] = prevId2
                ob['ts'] = obTs2
                _merge_ask_bid(ob, ob_msg['data'][0])
                msg_buff.remove(ob_msg)
                did_something = True
                break
        if not did_something:
            logger.debug(f"warning: no book message matched in a loop for symbol {symbol}! wait 0.1 second.")
            time.sleep(0.1)
    t2 = time.time()
    LOGGER.debug(f'thread ended for processing book message of {symbol}. before processing: {l1}messages, after processing: {len(msg_buff)}. time consumed: {t2-t1}s')
    # save in redis
    req_ts = int(10 * time.time())
    rkey = f'{EXCHANGE_FUTURE_DEPTH_PREFIX}{symbol}{req_ts % ONE_MIN_HUNDRED_MS}'
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', ob)
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Future Depth %s, ask size=%d, bid size=%s',
                rkey, len(ob['asks']), len(ob['bids']))

def _init_orderbook(j):
    symbol = j['arg']['instId']
    if not ORDER_BOOK.get(symbol):
        ORDER_BOOK[symbol] = {}
    ORDER_BOOK[symbol]['asks'] = {}
    ORDER_BOOK[symbol]['bids'] = {}
    
    for price, qty, _, _ in j['data'][0]['asks']:
        ORDER_BOOK[symbol]['asks'][price] = qty
    for price, qty, _, _ in j['data'][0]['bids']:
        ORDER_BOOK[symbol]['bids'][price] = qty
    ORDER_BOOK[symbol]['seqId'] = j['data'][0]['seqId']
    ORDER_BOOK[symbol]['prevSeqId'] = j['data'][0]['prevSeqId']
    ORDER_BOOK[symbol]['ts'] = int(j['data'][0]['ts'])
    LOGGER.debug('init order book: %s, %s', symbol, ORDER_BOOK[symbol])
    # save in redis
    req_ts = int(10 * time.time())
    rkey = f'{EXCHANGE_FUTURE_DEPTH_PREFIX}{symbol}{req_ts % ONE_MIN_HUNDRED_MS}'
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', ORDER_BOOK[symbol])
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Future Depth %s, ask size=%d, bid size=%s',
                rkey, len(ORDER_BOOK[symbol]['asks']), len(ORDER_BOOK[symbol]['bids']))

def _update_orderbook(j):
    symbol = j['arg']['instId']
    if not BOOK_MESSAGE_BUFF.get(symbol):
        BOOK_MESSAGE_BUFF[symbol] = []
    BOOK_MESSAGE_BUFF[symbol].append(j)   # another thread will process the message buffer
    merge_ob_thread = threading.Thread(target=_merge_ob_fun, args=(symbol, LOGGER))
    merge_ob_thread.start()
    merge_ob_thread.join()

def _process_ticker(j):
    last_price = j['data'][0]['last']
    last_sz = j['data'][0]['lastSz']
    symbol = j['arg']['instId']
    # caculate ts, create key, save to redis
    req_ts = int(10 * time.time())
    rkey = f'{EXCHANGE_FUTURE_TICKER_PREFIX}{symbol}{req_ts % ONE_MIN_HUNDRED_MS}'
    DATA_REDIS_CLIENT.set_dict(f'{rkey}_value', {'price': last_price, 'qty': last_sz})
    DATA_REDIS_CLIENT.set_int(rkey, req_ts)
    LOGGER.info('Update Future Tick %s, price=%s, qty=%s', symbol, last_price, last_sz)
    
def _process_book(j):
    if j['action'] == 'snapshot':
        _init_orderbook(j)
    elif j['action'] == 'update':
        _update_orderbook(j)
    else:
        LOGGER.error("orderbook unhandled message: %s" % j)
                    
def _process_message(j:dict):
    if j.get('event') and j['event'] == "error":
        LOGGER.error("error event: %s " % j)
    elif j.get('event') and j['event'] == "subscribe":
        LOGGER.debug("message subscribe: %s " % j)
    elif j.get('arg') and j['arg'].get('channel'):
        channel = j['arg']['channel']
        if channel == 'tickers':
            _process_ticker(j)
        elif channel == 'books':
            _process_book(j)
        else:
            LOGGER.debug("ignore message: %s", j)
    else:
        LOGGER.debug("ignore message: %s", j)  

def _on_message(message):
    try:
        j = json.loads(message)
        _process_message(j)
    except Exception as e:
        LOGGER.error("error message: %s" % message)
        LOGGER.error(traceback.format_exc())

def _create_args(depth_symbols: list[str], ticker_symbols: list[str]):
    args = [{"channel": "tickers","instId": symbol} for symbol in ticker_symbols]
    args.extend([{"channel": "books","instId": symbol} for symbol in depth_symbols])
    return args
    
async def _forever_run():
    global WS_CLIENT, DEPTH_SYMBOLS, TICKER_SYMBOLS
    while True:
        try:
            # Reset order book for fresh connection
            global ORDER_BOOK, BOOK_MESSAGE_BUFF
            ORDER_BOOK = {}
            BOOK_MESSAGE_BUFF = {}
            
            # Create new WebSocket client
            LOGGER.info("Connecting to OKX Future WebSocket...")
            ws = WsPublicAsync(OKX_FUTURE_PUB_WS_STREAM)
            WS_CLIENT = ws
            
            # Start WebSocket client
            await ws.start()
            
            # Create subscription args
            args = _create_args(DEPTH_SYMBOLS, TICKER_SYMBOLS)
            
            # Subscribe to topics
            LOGGER.debug("Subscribing to future topics: %s", args)
            await ws.subscribe(args, callback=_on_message)
            
            LOGGER.info('OKX future public websocket connected and started!')
            
            # Keep connection alive
            while 1:
                await asyncio.sleep(1)
        except Exception as e:
            LOGGER.error("OKX future public websocket error!")
            LOGGER.error(traceback.format_exc())
            LOGGER.info("Reconnecting in 5 seconds...")
            await asyncio.sleep(5)

def okx_future_subscribe(depth_symbols: list[str], ticker_symbols: list[str]):
    """ subscribe partial depth or ticker of given symbols for future
    """
    global DEPTH_SYMBOLS, TICKER_SYMBOLS
    
    # Save symbols for reconnection
    DEPTH_SYMBOLS = depth_symbols
    TICKER_SYMBOLS = ticker_symbols
    
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(_forever_run())
    finally:
        loop.close()    # clear after loop finished

""" JumpMaker Self-Trader
"""
from datetime import datetime, timedelta, timezone
import os
import sys
import time
import random
import asyncio
from logging import Logger

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from management.self_trade import TokenParameter as SelftradeParameter
from octopuspy.utils.log_util import create_logger
from utils.redis_client import DATA_REDIS_CLIENT
from cexapi.helper import get_private_client

BJ_TZ = timezone(timedelta(hours=8))
SIDES = ['BUY', 'SELL']

async def _trade(ctx: dict, symbol: str, price: str, qty: str):
    # TODO
    res = await ctx['client'].self_trade(symbol, random.choice(SIDES), price, qty)
    return res

async def _cancel_orders(ctx, symbol, order_id, logger: Logger):
    for _retry in range(3):
        try:
            # TODO
            res = ctx['client'].cancel_orders([order_id], symbol)
            if res and res.get('code') == 200 and order_id in res['data']:
                return True
        except Exception as e:
            logger.error("cancel_orders: %s; error: %s", order_id, e)
        time.sleep(0.5)
    return False

async def self_trade(
    param: SelftradeParameter, ctx: dict, logger: Logger
) -> bool:
    """ self trade by mock or real execution
    """
    # get latest trade of following symbol
    trade = DATA_REDIS_CLIENT.get_ticker(param)  # TODO get ticker from redis
    logger.debug('%s ticker %s', param.follow_symbol, trade)
    if not trade or not trade.get('price') or not trade.get('qty'):
        return False

    # get current order book of self-traded symbol
    symbol = param.maker_symbol
    ob = ctx['client'].get_top_askbid(symbol)
    logger.debug('%s order book %s', symbol, ob)

    if not ob or not ob[0]['ap'] or not ob[0]['bp']:
        logger.warning('no order book %s', symbol)
        return False

    top_ask, top_ask_qty = float(ob[0]['ap']), float(ob[0]['aq'])
    top_bid, top_bid_aty = float(ob[0]['bp']), float(ob[0]['bq'])
    qty = trade['qty'] * param.qty_multiplier
    # random coeficient
    _random_coef = 0.9995 + 0.00001 * random.randrange(0, 100)

    price_decimals = param.price_decimals
    qty_decimals = param.qty_decimals
    if trade['price']:
        # copy binance trade price
        price = trade['price']
        # for real ticker, make little change for sequent st price
        if ctx['price'] == price:
            # this turn self-trade price = pre turn price, change a little
            if price == top_ask:
                price -= 1.0 / 10 ** price_decimals
            else:
                price += 1.0 / 10 ** price_decimals
        elif ctx['price'] > 0:
            if abs(price / ctx['price'] - 1) > param.price_divergence:
                logger.error("Abnormal Ticker Volatility %s: pre price=%s, price=%s",
                    symbol, ctx['price'], price)
                if price > ctx['price']:
                    price = ctx['price'] * (1 + param.price_divergence)
                else:
                    price = ctx['price'] * (1 - param.price_divergence)
        qty *= _random_coef
    else:
        # mock trade using previous st price
        price = ctx['price']
        qty = 0.5 * (top_ask_qty + top_bid_aty) * _random_coef
    logger.debug('symbol %s, price %s, qty %s', symbol, price, qty)

    if price <= 0:
        return False

    qty = min(round(max(1.0 / 10 ** qty_decimals, qty), qty_decimals),
              round(float(param.max_amt_per_order) / price, qty_decimals))
    if qty > 0:
        logger.info('put self-trade %s %s %s %s %s', symbol, price, qty, top_bid, top_ask)
        # the close of minute N must equals to the open of minute N+1
        current_minute = int(int(time.time()) / 60) % 60
        if current_minute != ctx['minute']:
            # a new minute is started, so we need to use the previous trade price
            price = ctx['price']

        ctx['minute'] = current_minute
        price = max(min(price, top_ask), top_bid)
        ctx['price'] = price
        if qty == ctx['qty']:
            qty *= 1.0001
        ctx['qty'] = qty
        res = await _trade(ctx, symbol,
                           str(round(price, price_decimals) if price_decimals else int(price)),
                           str(round(qty, qty_decimals) if qty_decimals else int(qty)))
        logger.info(res)

        if res:
            # selftrade by real trade, cancel the maker order
            await _cancel_orders(ctx, symbol, res[0]['orderId'], logger)
        return True
    return False


async def main(params: list[SelftradeParameter]):
    """ main workflow of self-trader
    """
    logger = create_logger(CURR_DIR, "selftrade.log", 'TUNA_SELFTRADE', backup_cnt=10)
    logger.info('start self-trade with config: %s', params)

    # previous operation timestamp
    _last_operating_ts = {}
    # previous self trade context
    _prev_context = {}

    while 1:
        ts = time.time()
        tasks = []
        for param in params:
            symbol = param.maker_symbol
            # check self-trade frequency
            if _last_operating_ts.get(symbol, 0) + param.interval > ts:
                continue
            sid = param.sid
            if sid not in _prev_context:
                client = get_private_client(
                    exchange=param.exchange,
                    api_key=param.api_key,
                    api_secret=param.api_secret,
                    passphrase=param.passphrase,
                    logger=logger)
                
                _prev_context[sid] = {
                    'client': client, 'price':0, 'minute':0, 'qty':0}
                
            tasks.append(asyncio.create_task(self_trade(param, _prev_context[symbol], logger)))
            _last_operating_ts[symbol] = ts

        if tasks:
            await asyncio.gather(*tasks)
        else:
            await asyncio.sleep(0.05)

if __name__ == '__main__':
    """
    Reference: EXCHANGE_CHANNEL in cexapi/helper.py
    """
    selftrade_params = [
        SelftradeParameter({
            'Strategy Id' : '001', # sid必须是唯一的
            'Exchange' : 'BN',      # eg. BN | OKX | BIFU
            'Term Type' : 'SPOT',    # eg. SPOT | FUTURE | UMFUTURE
            'API KEY': '',
            'Secret': '',
            'Passphrase': '',

            'Follow Symbol': 'BTCUSDT',
            'Maker Symbol': 'btc_usdt',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 5,
            
            'Interval': 2,
            'Quote Timeout': 1,
            'Qty Multiplier': 0.8,
            'Max Amt Per Order': 2_000,
            'Min Qty': 0.00001,
            'Min Amt': 10,
            'Price Divergence': 0.02,
        }),
        SelftradeParameter({
            'Strategy Id' : '002', # sid必须是唯一的
            'Exchange' : 'OKX',      # eg. BN | OKX | BIFU
            'Term Type' : 'FUTURE',    # eg. SPOT | FUTURE | UMFUTURE
            'API KEY': '',
            'Secret': '',
            'Passphrase': '',
            
            'follow_symbol': 'ETHUSDT',
            'maker_symbol': 'eth_usdt',
            'price_decimals': 2,
            'qty_decimals': 4,

            'Interval': 2,
            'Quote Timeout': 1,
            'Qty Multiplier': 0.8,
            'Max Amt Per Order': 2_000,
            'Min Qty': 0.0001,
            'Min Amt': 10,
            'Price Divergence': 0.02,
        })
    ]

    asyncio.run(main(selftrade_params))

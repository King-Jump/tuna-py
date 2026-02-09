""" JumpMaker Self-Trader
"""
from datetime import timedelta, timezone
import os
import sys
import time
import random
import asyncio
from logging import Logger

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(os.path.dirname(CURR_DIR))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from octopuspy.utils.log_util import create_logger
from octopuspy.exchange.base_restapi import AskBid, NewOrder
from tunapy.management.self_trade import TokenParameter as SelftradeParameter
from tunapy.management.redis_client import DATA_REDIS_CLIENT
from tunapy.cexapi.helper import get_private_client

# OKX spot partial depth
# EXCHANGE_DEPTH_PREFIX = 'depth'
# # OKX spot ticker
EXCHANGE_TICKER_PREFIX = 'ticker'
BJ_TZ = timezone(timedelta(hours=8))
SIDES = ['BUY', 'SELL']

# hook parameters for unit_test
UNIT_TEST = True
TEST_HOOK = {}

async def _trade(ctx: dict, symbol: str, term_type:str,
                 price: str, qty: str, logger:Logger):
    side = random.choice(SIDES)
    ts = int(time.time()*1000)
    contract_size = 0.1
    leverage = 2
    if term_type == 'SPOT':
        orders = [
            NewOrder(
                symbol=symbol,
                client_id=f'M{symbol}_{ts}',
                side='BUY' if side == 'SELL' else 'SELL',
                type="LIMIT",
                quantity=qty,
                price=price,
                biz_type="SPOT",
                tif='GTX',
                reduce_only=False,
                position_side='',
                bait=False,
                selftrade_enabled=False,
            ),
            NewOrder(
                symbol=symbol,
                client_id=f'T{symbol}_{ts}',
                side=side,
                type="LIMIT",
                quantity=qty,
                price=price,
                biz_type="SPOT",
                tif='IOC',
                reduce_only=False,
                position_side='',
                bait=False,
                selftrade_enabled=False,
            )
        ]
    elif term_type == 'FUTURE':
        orders = [
            NewOrder(
                symbol=symbol,
                client_id=f'M{symbol}_{ts}',
                side='BUY' if side == 'SELL' else 'SELL',
                type="LIMIT",
                quantity=str(int((float(qty) * leverage) / contract_size)),
                price=price,
                biz_type="FUTURE",
                tif='GTX',
                reduce_only=False,
                position_side='LONG' if side == 'SELL' else 'SHORT',
                bait=False,
                selftrade_enabled=False,
            ),
            NewOrder(
                symbol=symbol,
                client_id=f'T{symbol}_{ts}',
                side=side,
                type="LIMIT",
                quantity=str(int((float(qty) * leverage) / contract_size)),
                price=price,
                biz_type="FUTURE",
                tif='IOC',
                reduce_only=False,
                position_side='SHORT' if side == 'SELL' else 'LONG',
                bait=False,
                selftrade_enabled=False,
            )
        ]
    else:
        logger.error("Unknown term_type: %s", term_type)
        return None
    logger.debug("selftrade trade 1: %s", orders[0])
    logger.debug("selftrade trade 2: %s", orders[1])
    # import pdb; pdb.set_trace()
    return ctx['client'].batch_make_orders(orders, symbol)

async def _cancel_orders(ctx, symbol, order_id, logger: Logger):
    for _retry in range(3):
        try:
            res = ctx['client'].cancel_order(order_id, symbol)
            if res.order_id == order_id:
                logger.debug("cancel_orders: %s", order_id)
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
    # import pdb; pdb.set_trace()
    logger.debug("self_trade begin!")
    # symbol_key = f'{EXCHANGE_TICKER_PREFIX}{param.follow_symbol}'
    trade = DATA_REDIS_CLIENT.get_ticker(param.follow_symbol)
    logger.debug('%s ticker %s', param.follow_symbol, trade)
    if not trade or not trade.get('price') or not trade.get('qty'):
        logger.warning('fail to get ticker %s', param.follow_symbol)
        return False

    # get current order book of self-traded symbol
    symbol = param.maker_symbol
    ob:AskBid = ctx['client'].top_askbid(symbol)
    logger.debug('%s order book %s', symbol, ob)
    if not ob:
        logger.warning('no order book %s', symbol)
        return False

    top_ask, top_ask_qty = float(ob[0].ap), float(ob[0].aq)
    top_bid, top_bid_aty = float(ob[0].bp), float(ob[0].bq)
    
    qty = float(trade['qty']) * param.qty_multiplier
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

        # unit test
        # if UNIT_TEST:
        #     fun_name = sys._getframe(0).f_code.co_name
        #     if TEST_HOOK.get(fun_name) and TEST_HOOK[fun_name]["do_unit_test"]:
        #         for var_name in TEST_HOOK[fun_name]["hooks"].keys():
        #             TEST_HOOK[fun_name]["hooks"][var_name] = locals().get(var_name)
        #     if TEST_HOOK[fun_name]["break"]:
        #         return False

        # res : List[OrderID]
        res = await _trade(ctx, symbol, param.term_type,
                           str(round(price, price_decimals) if price_decimals else int(price)),
                           str(round(qty, qty_decimals) if qty_decimals else int(qty)),
                           logger)
        logger.info(res)
        if res:
            # selftrade by real trade, cancel the maker order
            await _cancel_orders(ctx, symbol, res[0].order_id, logger)
        return True
    return False

async def main(params: list[SelftradeParameter]):
    """ main workflow of self-trader
    """
    logger = create_logger(BASE_DIR, "selftrade.log", 'TUNA_SELFTRADE', backup_cnt=10)
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
            if symbol not in _prev_context:
                client = get_private_client(
                    exchange=param.follow_exchange,
                    api_key=param.api_key,
                    api_secret=param.api_secret,
                    passphrase=param.passphrase,
                    logger=logger,
                )
                ### Set client.mock = True, use mock interfaces for unittest
                client.mock = True
                _prev_context[symbol] = {'client': client, 'price':0, 'minute':0, 'qty':0}
            tasks.append(asyncio.create_task(self_trade(param, _prev_context[symbol], logger)))
            logger.debug("append task: self_trade with param=[%s], _prev_context=[%s], symbol=[%s]",
                         param, _prev_context[symbol], symbol)
            _last_operating_ts[symbol] = ts

        # hook for unittest
        # if UNIT_TEST:
        #     fun_name = sys._getframe(0).f_code.co_name
        #     _pctx = _prev_context[symbol]
        #     if TEST_HOOK.get(fun_name) and TEST_HOOK[fun_name]["do_unit_test"]:
        #         for var_name in TEST_HOOK[fun_name]["hooks"].keys():
        #             TEST_HOOK[fun_name]["hooks"][var_name] = locals().get(var_name)
        #     if TEST_HOOK[fun_name]["break"]:
        #         break
        if tasks:
            await asyncio.gather(*tasks)
        else:
            await asyncio.sleep(0.05)
            
from test_env import API_KEY, SECRET, PASSPHRASE
if __name__ == '__main__':
    """
    Reference: EXCHANGE_CHANNEL in cexapi/helper.py
    """
    selftrade_params = [
        SelftradeParameter({
            'API KEY': API_KEY,
            'Secret': SECRET,
            'Passphrase': PASSPHRASE,

            'Follow Exchange': 'binance_spot',
            'Follow Symbol': 'btcusdt',
            'Maker Symbol': 'BTCUSDT',
            'Term type': 'SPOT',
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
            'API KEY': API_KEY,
            'Secret': SECRET,
            'Passphrase': PASSPHRASE,
            
            'Follow Exchange': 'binance_spot',
            'Follow Symbol': 'ethusdt',
            'Maker Symbol': 'ETHUSDT',
            'Term type': 'SPOT',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 4,

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

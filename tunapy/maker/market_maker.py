""" Market Maker Main
"""
import os
from re import A
import sys
import time
import traceback
import asyncio
from logging import Logger
import json
from collections import namedtuple

CURR_PATH = os.path.dirname(os.path.abspath(__file__))
if CURR_PATH not in sys.path:
    sys.path.insert(0, CURR_PATH)
BASE_PATH = os.path.dirname(os.path.dirname(CURR_PATH))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

from octopuspy.exchange.base_restapi import NewOrder
from octopuspy.utils.log_util import create_logger

from tunapy.management.market_making import TokenParameter
from tunapy.management.redis_client import DATA_REDIS_CLIENT
from tunapy.cexapi.helper import get_private_client
from tunapy.maker.maker_libs import (
    gen_ask_orders,
    gen_bid_orders,
    gen_client_order_id,
    gen_far_liquidity,
    mix_ask_bid_orders,
    diff_prev_new_orders,
)

EXCHANGE_DEPTH_PREFIX = 'depth'
BATCH_SIZE = 10

# CachedOrder class for storing order information with price and id
CachedOrder = namedtuple('CachedOrder', ['price', 'id'])

async def _clear_all_open_orders(symbol: str, ctx: dict, logger: Logger):
    logger.info('Cancel all open orders of %s', symbol)
    res=[]
    if ctx['client']:
        ids = ctx['client'].open_orders(symbol)
        res = ctx['client'].batch_cancel(ids)
    if not res:
        logger.error('Can not cancel all open orders of %s', symbol)


async def _clear_all_ner_open_orders(symbol: str, ctx: dict, logger: Logger):
    logger.info("Cancel all ner open orders of %s", symbol)
    orders = await _open_orders(ctx, symbol)
    cancell_ids = [order.order_id
                   for order in orders if (hasattr(order, 'client_id') and not order.client_id.startswith('F0'))]
    res = []
    if cancell_ids:
        if ctx['client']:
            res = ctx['client'].batch_cancel(cancell_ids, symbol)
        logger.info('Cancel all near orders %s', res)


async def _make_orders(ctx: dict, symbol: str, orders: list, logger: Logger) -> list:
    res = []
    # get batch size from config
    for start in range(0, len(orders), BATCH_SIZE):
        sub_res = []
        if ctx['client']:
            sub_res = ctx['client'].batch_make_orders(orders[start:start + BATCH_SIZE], symbol)
        logger.debug('Make Orders Response %s: %s', symbol, sub_res)
        res.extend(sub_res)
    return res

async def _cancel_orders(ctx: dict, symbol: str, cancel_ids: list, logger: Logger) -> int:
    cancel_num = 0
    for start in range(0, len(cancel_ids), BATCH_SIZE):
        sub_res = []
        if ctx['client']:
            sub_res = ctx['client'].batch_cancel(cancel_ids[start:start + BATCH_SIZE], symbol)
        logger.debug("cancel_orders %s: %s", symbol, sub_res)
        cancel_num += len(sub_res)
    return cancel_num

async def _open_orders(ctx: dict, symbol: str) -> list:
    if ctx['client']:
        return ctx['client'].open_orders(symbol)
    return []

async def handle_orders(
    param: TokenParameter,
    maker_symbol: str,
    ask_orders: list,
    bid_orders: list,
    ctx: dict,
    logger: Logger,
    is_far: bool = False
):
    """ handle orders, including make and cancel orders
    """
    # scan top ask/bid of new orders
    top_bid = bid_orders[0].price if bid_orders else 0
    top_ask = ask_orders[0].price if ask_orders else sys.maxsize

    prev_asks = ctx.get('prev_farasks', []) if is_far else ctx.get('prev_asks', [])
    prev_bids = ctx.get('prev_farbids', []) if is_far else ctx.get('prev_bids', [])
    # the number of rounds without forcely refresh
    no_force_refresh_num = ctx.get('no_force_refresh_num', 0)

    # max difference between prices of sequent rounds
    diff_rate_per_round = float(param.near_diff_rate_per_round)
    # diff_rate_per_round in BPS
    diff_rate_per_round *= 0.0001
    force_refresh_num = int(param.force_refresh_num)

    # order ids to be canceled
    cancel_ids = []
    # reserved previous orders
    reserve_asks, reserve_bids = [], []
    if diff_rate_per_round <= 0 or no_force_refresh_num >= force_refresh_num:
        # forcely refresh: cancel all previous orders
        cancel_ids = [co.id for co in prev_asks + prev_bids]
        # reserve all new ask/bid orders
        merged_asks = ask_orders
        merged_bids = bid_orders
        # update context
        ctx['no_force_refresh_num'] = 0
    else:
        # replace ask/bid order with large price difference
        merged_asks = diff_prev_new_orders(diff_rate_per_round, 'SELL', prev_asks, ask_orders,
                                           cancel_ids, reserve_asks)
        merged_bids = diff_prev_new_orders(diff_rate_per_round, 'BUY', prev_bids, bid_orders,
                                           cancel_ids, reserve_bids)
        # update context
        ctx['no_force_refresh_num'] += 1

    mix_new_orders = mix_ask_bid_orders(merged_asks, merged_bids)
    logger.debug('New Ordres: %s', mix_new_orders)
    cancel_num = 0 # number of canceled orders
    made_orders = [] # response of make orders
    if mix_new_orders:
        # First put new orders, then cancel previous orders
        made_orders = await _make_orders(ctx, maker_symbol, mix_new_orders, logger)
        for order, item in zip(mix_new_orders, made_orders):
            order_id = item.order_id
            if order_id:
                if order.side == 'BUY':
                    # define cancel order data structure
                    reserve_bids.append(
                        CachedOrder(price=order.price, id=order_id)
                    )
                else:
                    reserve_asks.append(
                        CachedOrder(price=order.price, id=order_id)
                    )
        if is_far:
            ctx['prev_farasks'] = reserve_asks
            ctx['prev_farbids'] = reserve_bids
        else:
            ctx['prev_asks'] = reserve_asks
            ctx['prev_bids'] = reserve_bids

        if cancel_ids:
            cancel_num = await _cancel_orders(ctx, maker_symbol, cancel_ids, logger)
            if not cancel_num:
                # failed to cancel previous orders
                ctx['top_ask'] = min(ctx.get('top_ask', top_ask), top_ask)
                ctx['top_bid'] = max(ctx.get('top_bid', top_bid), top_bid)
            elif not is_far:
                # sucessful canceled, and near orders only
                ctx['top_ask'] = top_ask
                ctx['top_bid'] = top_bid
        if is_far: # far end orders
            # handle exception in batch make orders, roll-back
            listed_orders = await _open_orders(ctx, maker_symbol)
            # made_orders are orders of far-end
            expect_ids = set([item.id for item in reserve_asks + reserve_bids])
            # add previous near-end orders
            for co in ctx.get('prev_asks', []):
                expect_ids.add(co.id)
            for co in ctx.get('prev_bids', []):
                expect_ids.add(co.id)
            unexpected_orders = [o['orderId'] for o in listed_orders if o['orderId'] \
                                and o['orderId'] not in expect_ids]
            if unexpected_orders:
                await _cancel_orders(ctx, maker_symbol, unexpected_orders, logger)
                logger.warning("Unexpected Orders %s", unexpected_orders)
                logger.debug('listed orders: %s', listed_orders)
    else:
        # no new orders, only delete reduced orders.
        if cancel_ids:
            cancel_num = await _cancel_orders(ctx, maker_symbol, cancel_ids, logger)
        ctx['no_force_refresh_num'] += 1

    logger.debug("HANDLE ORDERS: symbol: %s, diff rate per round: %s, no force refresh rounds: %s, "
                 "force refresh rounds: %s, prev ask size: %s, prev bid size: %s, "
                 "news ask order size: %s, new bid order size: %s, update order size: %s",
        maker_symbol, diff_rate_per_round, no_force_refresh_num, force_refresh_num, len(prev_asks),
        len(prev_bids), len(ask_orders), len(bid_orders), len(mix_new_orders), )
    logger.debug("put orders: %s, cancel orders num: %s", made_orders, cancel_num)


async def market_making(
    param: TokenParameter,        # market making parameters
    ctx: dict,          # context, include previous orders
    logger: Logger,
    is_far: bool
):
    """ Run market making strategy
        Parameters:
            param: near end parameters of market making
            far_param: far end parameters of market making
            ctx: the context of the current symbol
            logger: the logger
            is_far: whether put far-end orders 
    """
    maker_symbol = param.maker_symbol
    try:
        job_start_ts = time.time()

        # get order book of following symbol, cached in redis
        # binance have 2 types of future: UMFuture and portfolio_margin
        exchange_mapping = {
            "binance_UMFuture": "binance_future",
            "binance_portfolio_margin": "binance_future"
        }
        _exchange_prefix = exchange_mapping.get(ctx['follow_exchange'], ctx['follow_exchange'])
        symbol_key = f'{_exchange_prefix}_{EXCHANGE_DEPTH_PREFIX}{param.follow_symbol.lower()}'
        ask_bid = DATA_REDIS_CLIENT.get_order_book(symbol_key)
        logger.debug("get orderbook of key [%s]: %s", symbol_key, ask_bid)
        if not ask_bid or not ask_bid.get('asks') or not ask_bid.get('bids'):
            logger.warning('Cannot get quotes of %s', maker_symbol)
            return

        # first generate new near-end ask/bid orders
        side = param.near_side # put ASK or BID or Both
        new_asks = gen_ask_orders(ask_bid['asks'], param) if side in ('BOTH', 'ASK') else []
        new_bids = gen_bid_orders(ask_bid['bids'], param) if side in ('BOTH', 'BID') else []

        # for client order id
        clorder_start = int(time.time() / 86400)
        clorder_offset = int(time.time()*1000) % 86400000

        # the top ask and bid of prevous round's near orders
        top_bid = max(new_bids[0][0] if new_bids else float(ask_bid['bids'][0][0]), ctx.get('top_bid', 0))
        valid_asks = []
        for price, qty in new_asks:
            if price > top_bid:  # avoid self-trade
                valid_asks.append(
                    # batch order data structure
                    NewOrder(
                        symbol=maker_symbol,
                        client_id=gen_client_order_id(
                            maker_symbol, clorder_start, clorder_offset),
                        side="SELL",
                        type='LIMIT',
                        quantity=qty,
                        price=price,
                        biz_type=param.term_type,
                        tif=param.near_tif,
                        position_side=param.position_side,
                    )
                )
                clorder_offset += 1
        valid_bids = []
        top_ask = min(new_asks[0][0] if new_asks else float(ask_bid['asks'][0][0]), ctx.get('top_ask', top_bid))
        for price, qty in new_bids:
            if price < top_ask:
                valid_bids.append(
                    # batch order data structure
                    NewOrder(
                        symbol=maker_symbol,
                        client_id=gen_client_order_id(
                            maker_symbol, clorder_start, clorder_offset),
                        side="BUY",
                        type='LIMIT',
                        quantity=qty,
                        price=price,
                        biz_type=param.term_type,
                        tif=param.near_tif,
                        position_side=param.position_side,
                    )
                )
                clorder_offset += 1
        # put orders via exchange restful API
        await handle_orders(param, maker_symbol, valid_asks, valid_bids, ctx, logger, False)
        logger.info("[delay:maker-ner]%s:%s", maker_symbol, int(
            (time.time() - job_start_ts) * 1000))

        if not is_far:
            return

        # if updating the far put order,canecl all put order(far and ner)
        far_ask_orders, far_bid_orders = [], []
        job_start_ts = time.time()
        if param.far_side in ('BOTH', 'ASK'):
            far_ask_orders = gen_far_liquidity(maker_symbol, param, ask_bid, side='SELL',
                                               guard_price=top_bid, cl_order_start=clorder_start)
        if param.far_side in ('BOTH', 'BID'):
            far_bid_orders = gen_far_liquidity(maker_symbol, param, ask_bid, side='BUY',
                                               guard_price=top_ask, cl_order_start=clorder_start)
        await handle_orders(
            param, maker_symbol, far_ask_orders, far_bid_orders, ctx, logger, True)
        logger.info("[delay:maker-far]%s:%s", maker_symbol, int(
            (time.time() - job_start_ts) * 1000))
    except Exception:
        logger.error(traceback.format_exc())
        await _clear_all_ner_open_orders(maker_symbol, ctx, logger)


async def main(params: list[TokenParameter]):
    """ The main function
    """
    logger = create_logger(BASE_PATH, f"market_making.log", 'MM')
    logger.info('start market maker with config: %s', params)

    _last_operating_ts = {}  # the timestamp of last making orders for each pair
    _prev_context = {}  # previous context of MM data
    while 1:
        try:
            tasks = []
            for param in params:
                symbol = param.maker_symbol
                ts = time.time()

                # check update frequency
                if symbol not in _last_operating_ts:
                    _last_operating_ts[symbol] = {'near_opts': 0.0, 'far_opts': 0.0}
                op_ts = _last_operating_ts[symbol]
                if op_ts['near_opts'] + param.near_interval > ts:
                    continue
                _last_operating_ts[symbol]['near_opts'] = ts

                is_far = False
                if param.far_interval and op_ts['far_opts'] + param.far_interval <= ts:
                    _last_operating_ts[symbol]['far_opts'] = ts
                    is_far = True

                if symbol not in _prev_context:
                    client = get_private_client(exchange=param.maker_exchange,
                                                api_key=param.api_key,
                                                api_secret=param.api_secret,
                                                passphrase=param.passphrase,
                                                logger=logger,
                                                )
                    # use mock interface for fast testing
                    # client.mock = True
                    _prev_context[symbol] = {
                        'client': client,
                        'follow_exchange': param.follow_exchange,   # used to create get_ticker key
                        'prev_asks': [],    # previous made ask orders, near-end
                        'prev_bids': [],    # previous made bid orders, near-end
                        'prev_farasks': [],    # previous made ask orders, far-end
                        'prev_farbids': [],    # previous made bid orders, far-end
                        'no_force_refresh_num': 0,
                    }
                tasks.append(asyncio.create_task(market_making(
                    param, _prev_context[symbol], logger, is_far)))

            if tasks:
                await asyncio.gather(*tasks)
            else:
                await asyncio.sleep(0.05)
        except Exception:
            logger.error(traceback.format_exc())

    # before exit
    for symbol, ctx in _prev_context.items():
        await _clear_all_ner_open_orders(symbol, ctx, logger)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python market_maker.py <config_file>")
        sys.exit(1)
    _config_file = sys.argv[1]
    try:
        with open(_config_file, 'r') as f:
            args = json.load(f)
    except Exception:
        print(f"Error: failed to load config file {_config_file}")
        sys.exit(1)
    params = [TokenParameter(item) for item in args]
    asyncio.run(main(params))

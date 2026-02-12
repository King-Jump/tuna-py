""" Strategies and Tools for market making
"""
import time
import logging
import random

from tunapy.management.market_making import TokenParameter
from octopuspy.exchange.base_restapi import NewOrder

LOGGER = logging.getLogger('MM')

def gen_ask_orders(
    order_book: list,
    param: TokenParameter,
) -> list:
    """ Generate ask orders
    """
    return _mirror_ask_orders(order_book, param)

def gen_bid_orders(
    order_book: list,
    param: TokenParameter,
) -> list:
    """ Generate bid orders
    """
    return _mirror_bid_orders(order_book, param)

def _mirror_ask_orders(
    order_book: list,
    param: TokenParameter,
) -> list:
    # the quantity discount in BPS
    qty_coef = param.near_qty_multiplier
    price_decimals = param.price_decimals
    price_coef = 1. + 0.0001 * param.near_sell_price_margin

    new_orders, count = [], 0
    for ask, qty in order_book:
        if count >= param.near_ask_size:
            break
        order_price = ask * price_coef
        order_price = round(order_price, price_decimals) if price_decimals else int(order_price)
        order_qty = _calc_maker_qty(order_price, qty * qty_coef, param, False)
        if order_qty > 0:
            new_orders.append((order_price, order_qty))
            count += 1

    return new_orders

def _mirror_bid_orders(
    order_book: list,
    param: TokenParameter,
) -> list:
    # the quantity discount in BPS
    qty_coef = param.near_qty_multiplier
    price_decimals = param.price_decimals
    price_coef = 1. + 0.0001 * param.near_buy_price_margin

    new_orders, count = [], 0
    for bid, qty in order_book:
        if count >= param.near_bid_size:
            break
        order_price = bid * price_coef
        order_price = round(order_price, price_decimals) if price_decimals else int(order_price)
        order_qty = _calc_maker_qty(order_price, qty * qty_coef, param, False)
        if order_qty > 0:
            new_orders.append((order_price, order_qty))
            count += 1

    return new_orders

def _calc_maker_qty(order_price: float, order_qty: float, param: TokenParameter, is_far: bool = False):
    max_amt_per_order = float(param.far_max_amt_per_order) if is_far else float(param.near_max_amt_per_order)
    if order_qty * order_price > max_amt_per_order:
        order_qty = max_amt_per_order / order_price
    qty_decimals = param.qty_decimals
    if qty_decimals == 0:
        return int(order_qty)
    return round(order_qty, qty_decimals)

def gen_far_liquidity(symbol: str,
                      param: TokenParameter,
                      askbids: dict,
                      side: str,
                      guard_price: float,
                      cl_order_start: int,
) -> list:
    """ generate far orders
    """
    offset = int(time.time() * 100) % 8640000
    tif = param.far_tif
    orders = []
    if side == 'BUY':
        # make more price margin if previous hedge loses
        new_orders = _gen_bid_orders_far(askbids['bids'], param)
        for price, qty in new_orders:
            # avoid self-trade
            if price < guard_price:
                orders.append(
                    NewOrder(
                        symbol=symbol,
                        client_id=gen_client_order_id(f'B{symbol}', cl_order_start, offset, True),
                        side="BUY",
                        type='LIMIT',
                        quantity=qty,
                        price=price,
                        biz_type=param.term_type,
                        tif=tif,
                        position_side=param.position_side,
                    )
                )
                offset += 1
    else:
        new_orders = _gen_ask_orders_far(askbids['asks'], param)
        for price, qty in new_orders:
            # avoid self-trade
            if price > guard_price:
                orders.append(
                    NewOrder(
                        symbol=symbol,
                        client_id=gen_client_order_id(f'S{symbol}', cl_order_start, offset, True),
                        side="SELL",
                        type='LIMIT',
                        quantity=qty,
                        price=price,
                        biz_type=param.term_type,
                        tif=tif,
                        position_side=param.position_side,
                    )
                )
                offset += 1
    return orders

def _spread_far(
    order_book: list, param: TokenParameter, side: str
) -> list:
    new_orders = []

    base_price = order_book[0][0]
    if side == 'SELL':
        price_coef = 1 + 0.0001 * float(param.far_sell_price_margin)
        max_size = param.far_ask_size
    else:
        price_coef = 1 - 0.0001 * float(param.far_buy_price_margin)
        max_size = param.far_bid_size
    price_decimals = param.price_decimals
    qty_coef = param.far_qty_multiplier
    qtys = [float(item[1]) for item in order_book]
    qty_size = len(qtys)

    for _ in range(max_size):
        base_price *= price_coef
        rand_idx = random.randrange(0, qty_size)
        qty = qtys[rand_idx] * (0.95 + rand_idx * 0.05 / qty_size)

        order_price = round(base_price, price_decimals) if price_decimals else int(base_price)
        order_qty = _calc_maker_qty(order_price, qty * qty_coef, param, True)
        if order_qty > 0:
            new_orders.append((order_price, order_qty))
    return new_orders

def _gen_ask_orders_far(
    order_book: list, # near order book, 20 top asks
    param: TokenParameter,
) -> list:
    if param.far_strategy == 'spread':
        return _spread_far(order_book, param, 'SELL')
    return []

def _gen_bid_orders_far(
    order_book: list, # near order book, 20 top bids
    param: TokenParameter,
) -> list:
    if param.far_strategy == 'spread':
        return _spread_far(order_book, param, 'BUY')
    return []


def gen_client_order_id(
    symbol: str, cl_order_start: int, cl_order_offset: int, far_end: bool = False
) -> str:
    """ Generate ClOrdID
    """
    if far_end:
        # far-end liquidity
        return f'F0{symbol}_{cl_order_start}_{cl_order_offset}'
    return f'{symbol}_{cl_order_start}_{cl_order_offset}'

def mix_ask_bid_orders(ask_orders: list, bid_orders: list) -> list:
    """Mix ask and bid orders
    """
    ask_orders_len = len(ask_orders)
    bid_orders_len = len(bid_orders)
    mixed_orders = []

    for ask_, bid_ in zip(ask_orders, bid_orders):
        mixed_orders.append(ask_)
        mixed_orders.append(bid_)
    if bid_orders_len > ask_orders_len:
        mixed_orders.extend(bid_orders[ask_orders_len:])
    elif bid_orders_len < ask_orders_len:
        mixed_orders.extend(ask_orders[bid_orders_len:])
    return mixed_orders

def _merge_orders(
    prev_orders: list, new_orders: list, flags: list, cancel_ids: list, reserve_orders: list
) -> list:
    merged_orders = []
    for idx, flag in enumerate(flags):
        prev_order = prev_orders[idx]
        if not flag:
            # if False, replace previous order with new order
            cancel_ids.append(prev_order.id)
            merged_orders.append(new_orders[idx])
        else:
            reserve_orders.append(prev_order)
    if len(prev_orders) > len(flags):
        # remove additional previous orders
        cancel_ids.extend([order.id for order in prev_orders[len(flags):]])
    if len(new_orders) > len(flags):
        # reverse additional new orders
        merged_orders.extend(new_orders[len(flags):])
    return merged_orders

def diff_prev_new_orders(
    diff_rate_per_round: float,
    side: str,
    prev_orders: list,
    new_orders: list,
    cancel_ids: list,
    reserve_orders: list
) -> list:
    """ compare previous and new orders by price, if the difference < diff_rate_per_round,
        reserve the previous order, otherwise cancel the previous order and reserve the new one.
    """
    # replace ask/bid order with large price difference
    prev_orders.sort(key=lambda x: x.price, reverse=side=='BUY')  # sort by price
    new_orders.sort(key=lambda x: x.price, reverse=side=='BUY')  # sort by price
    # True if no price difference
    flags = [abs(prev_order.price / order.price - 1) < diff_rate_per_round
        for prev_order, order in zip(prev_orders, new_orders)]
    return _merge_orders(prev_orders, new_orders, flags, cancel_ids, reserve_orders)

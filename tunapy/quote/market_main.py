""" Market Main
"""
import os
import sys

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

#from management.market_making import TokenParameter as MakerParameter
# from management.self_trade import TokenParameter as SelftradeParameter
from management.quote import TokenParameter as QuoteParameter
from quote.bn_public_ws import bn_subscribe
from quote.bn_future_public_ws import bn_future_subscribe
from quote.okx_public_ws import okx_subscribe
from quote.okx_future_public_ws import okx_future_subscribe

EXCHANGE_BN = "binance_spot"
EXCHANGE_BN_FUTURE = "binance_future"
EXCHANGE_OKX = "okx_spot"
EXCHANGE_OKX_FUTURE = "okx_future"

def main(exchange, maker_params: list[QuoteParameter], selftrade_params: list[QuoteParameter]):
    """ main workflow of market data
    """
    maker_symbols = [param.follow_symbol for param in maker_params]
    selftrade_symbols = [param.follow_symbol for param in selftrade_params]
    
    if exchange == EXCHANGE_BN:
        bn_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_BN_FUTURE:
        bn_future_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_OKX:
        okx_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_OKX_FUTURE:
        okx_future_subscribe(maker_symbols, selftrade_symbols)
    else:
        return

if __name__ == '__main__':
    exchange = EXCHANGE_BN
    maker_params = [
        QuoteParameter({
            'Follow Symbol': 'btcusdt',
            'Maker Symbol': 'btcusdt',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 5,
        }),
        QuoteParameter({
            'Follow Symbol': 'ethusdt',
            'Maker Symbol': 'ethusdt',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 4,
        })
    ]

    selftrade_params = [
        QuoteParameter({
            'Follow Symbol': 'btcusdt',
            'Maker Symbol': 'btcusdt',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 5,
        }),
        QuoteParameter({
            'Follow Symbol': 'ethusdt',
            'Maker Symbol': 'ethusdt',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 4,
        })
    ]
    
    main(EXCHANGE_BN_FUTURE, maker_params, selftrade_params)

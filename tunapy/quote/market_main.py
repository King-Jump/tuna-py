""" Market Main
"""
import os
import sys

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from management.market_making import TokenParameter as MakerParameter
from management.self_trade import TokenParameter as SelftradeParameter
from quote.bn_public_ws import bn_subscribe
from quote.okx_public_ws import okx_subscribe

EXCHANGE_BN = 'Binance'
EXCHANGE_OKX = 'OKX'

def main(exchange, maker_params: list[MakerParameter], selftrade_params: list[SelftradeParameter]):
    """ main workflow of market data
    """
    
    maker_symbols = [param.follow_symbol for param in maker_params]
    selftrade_symbols = [param.follow_symbol for param in selftrade_params]
    
    if exchange == EXCHANGE_BN:
        bn_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_OKX:
        okx_subscribe(maker_symbols, selftrade_symbols)
    else:
        return

if __name__ == '__main__':
    maker_params = [
        MakerParameter({
            'follow_symbol': 'BTCUSDT',
            'maker_symbol': 'btc_usdt',
            'price_decimals': 2,
            'qty_decimals': 5,
        }),
        MakerParameter({
            'follow_symbol': 'ETHUSDT',
            'maker_symbol': 'eth_usdt',
            'price_decimals': 2,
            'qty_decimals': 4,
        }),
    ]

    selftrade_params = [
        SelftradeParameter({
            'follow_symbol': 'BTCUSDT',
            'maker_symbol': 'btc_usdt',
            'price_decimals': 2,
            'qty_decimals': 5,
        }),
        SelftradeParameter({
            'follow_symbol': 'ETHUSDT',
            'maker_symbol': 'eth_usdt',
            'price_decimals': 2,
            'qty_decimals': 4,
        })
    ]
    
    main(EXCHANGE_BN, maker_params, selftrade_params)

""" Market Main
"""
import os
import sys
import json

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from management.market_making import TokenParameter as MakerParameter
from management.self_trade import TokenParameter as SelftradeParameter
# from management.quote import TokenParameter as QuoteParameter
from quote.bn_public_ws import bn_subscribe
from quote.bn_future_public_ws import bn_future_subscribe
from quote.okx_public_ws import okx_subscribe
from quote.okx_future_public_ws import okx_future_subscribe

EXCHANGE_BN = "binance_spot"
EXCHANGE_BN_FUTURE = "binance_future"
EXCHANGE_OKX = "okx_spot"
EXCHANGE_OKX_FUTURE = "okx_future"

def main(exchange, maker_params: list[MakerParameter], selftrade_params: list[SelftradeParameter]):
    """ main workflow of market data
    """
    # Extract symbols and remove duplicates
    maker_symbols = list(set([param.follow_symbol for param in maker_params]))
    selftrade_symbols = list(set([param.follow_symbol for param in selftrade_params]))
    
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
    import argparse
    parser = argparse.ArgumentParser(description='Market data subscription')
    parser.add_argument('exchange', help='Exchange to subscribe (e.g., binance_spot, binance_future, okx_spot, okx_future)')
    parser.add_argument('--maker_json', required=False, help='Path to maker parameters JSON file')
    parser.add_argument('--st_json', required=False, help='Path to self-trade parameters JSON file')
    
    args = parser.parse_args()
    exchange = args.exchange
    maker_params_json_file = args.maker_json
    selftrade_params_json_file = args.st_json
    
    # Load maker parameters
    maker_params = []
    if maker_params_json_file:
        try:
            with open(maker_params_json_file, 'r') as f:
                _params = json.load(f)
                maker_params = [MakerParameter(param) for param in _params]   
        except Exception as e:
            print(f"Error loading maker parameters from {maker_params_json_file}: {e}")
    
    # Load self-trade parameters
    selftrade_params = []
    if selftrade_params_json_file:
        try:
            with open(selftrade_params_json_file, 'r') as f:
                _params = json.load(f)
                selftrade_params = [SelftradeParameter(param) for param in _params]
        except Exception as e:
            print(f"Error loading self-trade parameters from {selftrade_params_json_file}: {e}")

    main(exchange, maker_params, selftrade_params)

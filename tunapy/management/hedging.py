""" Parameters for hedging
"""

from collections import namedtuple
from logging import Logger


class TokenParameter:
    def __init__(self, conf: dict) -> None:
        self.api_key = conf['API KEY']     # the API key for Maker Account
        self.api_secret = conf['Secret']   # the API secret for Maker Account
        self.passphrase = conf['Passphrase'] # the passphrase for Maker Account
        self.maker_symbol = conf['Maker Symbol']     # the maker symbol
        self.hedge_symbol = conf['Hedge Symbol']     # the hedge symbol
        self.hedge_exchange = conf['Hedge Exchange']  # the hedge exchange
        self.price_decimals = int(conf['Hedger Price Decimals'])      # price decimals of hedger symbol
        self.qty_decimals = int(conf['Hedger Qty Decimals'])          # quantity decimals of hedger symbol

        self.min_qty_per_order = float(conf['Min Qty'])             # minimum quantity of each order
        self.min_amt_per_order = float(conf['Min Amt'])             # minimum amount of each order
        self.slippage = max(float(conf['Slippage']), 1.0)           # slippage for hedging

class PrivateWSClient:
    def __init__(self, config: dict, logger:Logger) -> None:
        self.api_key = config.get('API KEY', '')
        self.api_secret = config.get('Secret', '')
        self.passphrase = config.get('Passphrase', '')
        self.stream_url = config.get('Stream URL', '')
        self.logger = logger  # Logger

        # callbacks
        self.on_open = None
        self.on_close = None
        self.handle_trade_filled = None
        self.on_error = None

    def start(self, symbol, on_open, on_close, handle_trade_filled, on_error):
        self.on_open = on_open
        self.on_close = on_close
        self.on_error = on_error
        self.handle_trade_filled = handle_trade_filled
        self.subscribe_execution_report(symbol)

    def subscribe_execution_report(self, symbol: str):
        raise NotImplementedError("subscribe_execution_report not implemented")

FilledOrder = namedtuple("FilledOrder", ["trade_id", "qty", "amount", "symbol", "side", "order_id", "match_time"])

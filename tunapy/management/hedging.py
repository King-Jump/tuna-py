""" Parameters for hedging
"""

class TokenParameter:
    def __init__(self, conf: dict) -> None:
        self.api_key = conf['API KEY']     # the API key for Maker Account
        self.api_secret = conf['Secret']   # the API secret for Maker Account
        self.passphrase = conf['Passphrase'] # the passphrase for Maker Account

        self.stream_url = conf['Stream URL']     # the stream url for private websocket
        self.maker_symbol = conf['Maker Symbol']     # the mirroring symbol
        self.hedge_symbol = conf['Hedge Symbol']     # the hedge symbol
        self.price_decimals = int(conf['Hedger Price Decimals'])      # price decimals of hedger symbol
        self.qty_decimals = int(conf['Hedger Qty Decimals'])          # quantity decimals of hedger symbol

        self.min_qty_per_order = float(conf['Min Qty'])             # minimum quantity of each order
        self.min_amt_per_order = float(conf['Min Amt'])             # minimum amount of each order
        self.slippage = max(float(conf['Slippage']), 1.0)           # slippage for hedging

class PrivateWSClient:
    def __init__(self, api_key: str, api_secret: str, passphrase: str, stream_url: str) -> None:
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = passphrase
        self.stream_url = stream_url

        # callbacks
        self.on_open = None
        self.on_close = None
        self.handle_trade_filled = None
        self.on_error = None

    def start(self, symbol, on_open, on_close, on_error, handle_trade_filled):
        self.on_open = on_open
        self.on_close = on_close
        self.on_error = on_error
        self.handle_trade_filled = handle_trade_filled

        self.subscribe_execution_report(symbol)

    def subscribe_execution_report(self, symbol: str):
        raise NotImplementedError("subscribe_execution_report not implemented")

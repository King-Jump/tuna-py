""" Parameters for self trading
"""

class TokenParameter:
    def __init__(self, conf: dict) -> None:
        self.maker_exchange = conf['Maker Exchange']     # the mirroring exchange, SPOT and FUTURE are different
        self.maker_symbol = conf['Maker Symbol']     # the mirroring symbol
        self.api_key = conf['API KEY']     # the API key for Maker Account
        self.api_secret = conf['Secret']   # the API secret for Maker Account
        self.passphrase = conf['Passphrase'] # the passphrase for Maker Account

        self.follow_exchange = conf['Follow Exchange']   # the mirrored exchange, SPOT and FUTURE are different
        self.follow_symbol = conf['Follow Symbol']   # the mirrored symbol
        self.price_decimals = int(conf['Maker Price Decimals'])      # price decimals of maker symbol
        self.qty_decimals = int(conf['Maker Qty Decimals'])          # quantity decimals of maker symbol
        self.term_type = conf["Term type"]    # SPOT | FUTURE

        self.interval = max(0.1, float(conf['Interval']))   # interval of trading
        self.quote_timeout = float(conf['Quote Timeout'])   # timeout of quote update of follow symbol
        self.qty_multiplier = float(conf['Qty Multiplier'])         # quantity multiplier
        self.max_amt_per_order = float(conf['Max Amt Per Order'])   # maximum amount of each order
        self.min_qty_per_order = float(conf['Min Qty'])             # minimum quantity of each order
        self.min_amt_per_order = float(conf['Min Amt'])             # minimum amount of each order
        self.price_divergence = float(conf['Price Divergence'])       # maximum divergence of consequent self-trades

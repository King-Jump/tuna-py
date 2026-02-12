""" Parameters for market making
"""

class TokenParameter:
    def __init__(self, conf: dict) -> None:
        self.maker_exchange = conf['Maker Exchange']     # the exchange for Maker Account
        self.api_key = conf['API KEY']     # the API key for Maker Account
        self.api_secret = conf['Secret']   # the API secret for Maker Account
        self.passphrase = conf['Passphrase'] # the passphrase for Maker Account

        self.follow_exchange = conf['Follow Exchange']     # the exchange for Follow Account
        self.follow_symbol = conf['Follow Symbol']   # the mirrored symbol
        
        self.maker_symbol = conf['Maker Symbol']     # the mirroring symbol
        self.term_type = conf['Term type']          # term type of maker symbol, such as "SPOT"
        self.price_decimals = int(conf['Maker Price Decimals'])      # price decimals of maker symbol
        self.qty_decimals = int(conf['Maker Qty Decimals'])          # quantity decimals of maker symbol
        self.position_side = conf.get('Position Side', '')       # position side of maker symbol, such as "LONG"

        ### far-end market making parameters
        self.far_interval = float(conf['Far Interval'])          # interval of putting new far-end orders
        self.far_quote_timeout = float(conf['Far Quote Timeout'])# timeout of quote update of follow symbol
        self.far_side = conf['Far Side']                         # BUY: only bids, SELL: only asks, BOTH: both asks and bids
        self.far_tif = conf['Far TIF']                           # time in force, GTX: post only, GTC: good till cancel
        self.far_strategy = conf['Far Strategy']                 # strategy of market making, such as "SPREAD"
        self.far_buy_price_margin = int(conf['Far Buy Price Margin'])     # spread of bid levels
        self.far_sell_price_margin = int(conf['Far Sell Price Margin'])   # spread of ask levels
        self.far_qty_multiplier = float(conf['Far Qty Multiplier'])  # quantity multiplier
        self.far_ask_size = int(conf['Far Ask Size'])            # number of ask levels
        self.far_bid_size = int(conf['Far Bid Size'])            # number of bid levels
        self.far_max_amt_per_order = float(conf['Far Max Amt Per Order'])   # maximum amount of each order
        self.far_min_qty_per_order = float(conf['Far Min Qty'])             # minimum quantity of each order
        self.far_min_amt_per_order = float(conf['Far Min Amt'])             # minimum amount of each order
        self.far_diff_rate_per_round = int(conf['Far Diff Per Round'])    # maximum price difference of the same level
    
        ### near-end market making parameters
        self.near_interval = float(conf['Near Interval'])                  # interval of putting new near-end orders
        self.near_quote_timeout = float(conf['Near Quote Timeout']) # timeout of quote update of follow symbol
        self.near_side = conf['Near Side']                          # BUY: only bids, SELL: only asks, BOTH: both asks and bids
        self.near_tif = conf['Near TIF']                            # time in force, GTX: post only, GTC: good till cancel
        self.near_strategy = conf['Near Strategy']                  # strategy of market making, such as "SPREAD", "MIRROR"
        self.near_buy_price_margin = int(conf['Near Buy Price Margin'])   # price spread of the same bid level between mirrored quote and mirroring quote
        self.near_sell_price_margin = int(conf['Near Sell Price Margin']) # price spread of the same ask level between mirrored quote and mirroring quote
        self.near_qty_multiplier = float(conf['Near Qty Multiplier']) # quantity multiplier
        self.near_ask_size = int(conf['Near Ask Size'])             # number of ask levels
        self.near_bid_size = int(conf['Near Bid Size'])             # number of bid levels
        self.near_max_amt_per_order = float(conf['Near Max Amt Per Order']) # maximum amount of each order
        self.near_min_qty_per_order = float(conf['Near Min Qty'])           # minimum quantity of each order
        self.near_min_amt_per_order = float(conf['Near Min Amt'])           # minimum amount of each order
        self.near_diff_rate_per_round = int(conf['Near Diff Per Round'])  # maximum price difference of the same level
        
        self.force_refresh_num = int(conf['Force Refresh Num'])             # number of rounds without forcely refresh

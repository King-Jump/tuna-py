""" Parameters for market info
"""
class TokenParameter:
    def __init__(self, conf: dict) -> None:
        self.follow_symbol = conf['Follow Symbol']   # the mirrored symbol
        self.maker_symbol = conf['Maker Symbol']     # the mirroring symbol
        self.price_decimals = int(conf['Maker Price Decimals'])      # price decimals of maker symbol
        self.qty_decimals = int(conf['Maker Qty Decimals'])          # quantity decimals of maker symbol

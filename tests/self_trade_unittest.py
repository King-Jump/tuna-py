import unittest
import os
import sys
import json
PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PKG_DIR not in sys.path:
    sys.path.insert(0, PKG_DIR)

from octopuspy.utils.log_util import create_logger
LOGGER = create_logger(".", "self_trader_unittest.log", "SELF_TRADE", 1)

from trader_unittest import TraderUnitTest
from test_env import API_KEY, SECRET, PASSPHRASE
class SelfTraderUnitTest(TraderUnitTest):
    
    def test_00_init_parameter(self):
        print("=============== test_00_init_parameter ===============")
        self.result["init_params"] = {
            'API KEY': API_KEY,
            'Secret': SECRET,
            'Passphrase': PASSPHRASE,
            
            'Follow Exchange': 'binance_spot',
            'Follow Symbol': 'BTCUSDT',
            'Maker Symbol': 'btc_usdt',
            'Maker Price Decimals': 2,
            'Maker Qty Decimals': 5,
            'term_type': 'SPOT',
            
            'Interval': 2,
            'Quote Timeout': 1,
            'Qty Multiplier': 0.8,
            'Max Amt Per Order': 2_000,
            'Min Qty': 0.00001,
            'Min Amt': 10,
            'Price Divergence': 0.02,
        }

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(SelfTraderUnitTest)
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)
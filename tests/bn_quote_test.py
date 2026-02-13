"""
Test market info functionality, on binance with symbol ethusdt.
Validate return data scheme, integrity, calculate time delay.
Before starting this program, start market_main with prarmeter "exchange = EXCHANGE_BN"
"""
import time
import os
import sys
import unittest

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from colorful_test import (
    ColorfulTestCase, 
)
from tunapy.self_trader.self_trader import EXCHANGE_TICKER_PREFIX
from tunapy.quote.redis_client import DATA_REDIS_CLIENT

SYMBOL = 'BNBUSDT'
TEST_LOOPS = 100
INTERMEDIATE_RESULT = {}
ONE_MIN_HUNDRED_MS = 600

class BinanceSpotTest(ColorfulTestCase):
    def setUp(self):
        # This function runs before each test method
        print("=============== test start ===============")
        self.result = INTERMEDIATE_RESULT
        
    def tearDown(self):
        # This runs after each test method
        print("sleep 2 seconds")
        time.sleep(2)
        INTERMEDIATE_RESULT = self.result
        print("RESULT teardown: ", self.result)
        
    def test_bn_quote_test(self):
        print("************* Binance spot quote test *************")
        # get latest trade of following symbol
        success_num = 0
        prev_ticker = {}
        prev_t = 0
        total_100_ms = 0
        for i in range(TEST_LOOPS):
            time.sleep(0.5)
            print(f"** repeat: {i}/{TEST_LOOPS} **")
            ts = int(time.time()*10)
            # print("ts: ", ts)
            current_tag = ts % ONE_MIN_HUNDRED_MS
            # backforward to last minute
            try:
                for prev_tag in range(current_tag, current_tag - ONE_MIN_HUNDRED_MS, -1):
                    tag = (prev_tag + ONE_MIN_HUNDRED_MS) % ONE_MIN_HUNDRED_MS  # prev_tag may less than zero
                    _key=f'{EXCHANGE_TICKER_PREFIX}{SYMBOL}{tag}'
                    # print("_key: ", _key)
                    prev_t = DATA_REDIS_CLIENT.get_int(_key)
                    # print("prev_t: ", prev_t)
                    if prev_t and ts-ONE_MIN_HUNDRED_MS <= prev_t <= ts:
                        prev_ticker = DATA_REDIS_CLIENT.get_dict(f'{_key}_value')
                        if prev_ticker:
                            if prev_ticker["price"] and prev_ticker["qty"]:
                                success_num += 1
                                total_100_ms += (ts-prev_t)
                            break  # nearest order_book
                print("prev_ticker: %s" % prev_ticker)
            except Exception as e:
                print('Ticker failled once.', e)
        self.assertEqualWithColor(success_num, TEST_LOOPS, "All ticker calls succeeded")
        self.assertTrueWithColor(prev_ticker, "Ticker result available")
        self.assertTrueWithColor(prev_ticker["price"], "Ticker price available")
        self.assertTrueWithColor(prev_ticker["qty"], "Ticker quantity available")
        print(f"Ticker succeeded: {success_num}/{TEST_LOOPS}")
        print(f"Success rate: {float(success_num/TEST_LOOPS)}")
        print(f"Average delay when success: {float(total_100_ms / success_num * 100)} ms")

if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(BinanceSpotTest)
    runner = unittest.TextTestRunner(verbosity=1)
    runner.run(suite)
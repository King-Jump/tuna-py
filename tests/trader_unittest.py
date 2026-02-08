import time
import asyncio
import os
import sys

CURR_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(CURR_DIR)
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from colorful_test import *
from tunapy.management.self_trade import (
    TokenParameter as StTokenParameter
)

INTERMEDIATE_RESULT = {}

from tunapy.self_trader.self_trader import TEST_HOOK, UNIT_TEST, main

class TraderUnitTest(ColorfulTestCase):
    """Class for trader unit test
    self.result: {
        "init_params": [{}]    # trader init parameter
        "self_trade_params": StTokenParameter    # trader init parameter
    }
    """
    def setUp(self):
        # This function runs before each test method
        print("=============== test start ===============")
        self.result = INTERMEDIATE_RESULT
        
    def tearDown(self):
        # This runs after each test method
        print("sleep 2 seconds")
        time.sleep(3)
        INTERMEDIATE_RESULT = self.result
        print("RESULT teardown: ", self.result)
        print(UNIT_TEST)
        
    def test_01_create_trader(self):
        print("=============== test_01_create_trader ===============")
        try:
            params = StTokenParameter(self.result["init_params"])
            self.assertIsInstanceWithColor(params, StTokenParameter, "Create param succeed")
            self.assertTrueWithColor(params.api_key, "api_key available")
            self.assertTrueWithColor(params.api_secret, "api_secret available")
            self.assertTrueWithColor(params.follow_exchange, "follow_exchange available")
            self.assertTrueWithColor(params.follow_symbol, "follow_symbol available")
            self.assertTrueWithColor(params.maker_symbol, "maker_symbol available")
            self.assertGreaterWithColor(params.price_decimals, 0, "price_decimals available")
            self.assertGreaterWithColor(params.qty_decimals, 0, "qty_decimals available")
            self.assertInWithColor(params.term_type, ["SPOT", "FUTURE"], "term_type available")
            self.assertGreaterEqualWithColor(params.interval, 0.1, "interval available")
            self.assertGreaterWithColor(params.qty_multiplier, 0, "qty_multiplier available")
            self.assertGreaterWithColor(params.max_amt_per_order, 0, "max_amt_per_order available")
            self.assertGreaterWithColor(params.min_qty_per_order, 0, "min_qty_per_order available")
            self.assertGreaterWithColor(params.min_amt_per_order, 0, "min_amt_per_order available")
            self.assertGreaterWithColor(params.price_divergence, 0, "price_divergence available")
            from tunapy.cexapi.helper import EXCHANGE_CHANNEL
            self.assertInWithColor(params.follow_exchange, EXCHANGE_CHANNEL.keys(), "known follow_exchange")
            self.result["self_trade_params"] = [params]
        except:
            self.assertTrueWithColor(False, "Create params succeed")

    def test_02_test_main(self):
        print("=============== test_02_test_main ===============")
        UNIT_TEST = True
        TEST_HOOK["main"] = {}
        TEST_HOOK["main"]["do_unit_test"] = True
        TEST_HOOK["main"]["break"] = True
        TEST_HOOK["main"]["hooks"] = {}
        TEST_HOOK["main"]["hooks"]["_pctx"] = {}
        TEST_HOOK["main"]["hooks"]["tasks"] = {}
        main_prarms = self.result["self_trade_params"]
        asyncio.run(main(main_prarms))
        self.assertTrueWithColor(TEST_HOOK["main"]["hooks"]["_pctx"], "pre_context initialized")
        self.assertTrueWithColor(TEST_HOOK["main"]["hooks"]["_pctx"]["client"], "client initialized")
        task_num = len(TEST_HOOK["main"]["hooks"]["tasks"])
        param_num = len(self.result["self_trade_params"])
        self.assertEqualWithColor(task_num, param_num, "Params and tasks have same length")
        
    def test_03_task_run(self):
        print("=============== test_03_task_run ===============")
        TEST_HOOK["main"]["break"] = False
        TEST_HOOK["self_trade"] = {}
        TEST_HOOK["self_trade"]["break"] = True
        TEST_HOOK["self_trade"]["do_unit_test"] = True
        TEST_HOOK["self_trade"]["hooks"] = {}
        TEST_HOOK["self_trade"]["symbol"] = None
        TEST_HOOK["self_trade"]["price"] = None
        TEST_HOOK["self_trade"]["qty"] = None
        main_prarms = self.result["self_trade_params"]
        asyncio.run(main(main_prarms))

        
        

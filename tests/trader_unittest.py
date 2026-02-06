import unittest
import os
import sys
import time

# PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# if PKG_DIR not in sys.path:
#     sys.path.insert(0, PKG_DIR)

SYMBOL = "BTC_USDT"
INTERMEDIATE_RESULT = {}

from octopuspy import (
    BaseClient, NewOrder, OrderID, OrderStatus, Ticker, 
    AskBid, ORDER_STATE_CONSTANTS as order_state
)

class Color:
    """ANSI color code"""
    # base color
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'
    
    # bright color
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    
    # backgroud color
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'
    
    # style
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    BLINK = '\033[5m'
    REVERSE = '\033[7m'
    HIDDEN = '\033[8m'
    STRIKETHROUGH = '\033[9m'
    
    # reset
    RESET = '\033[0m'
    
    @classmethod
    def colorize(cls, text, *styles):
        """add style and color"""
        style_codes = ''.join(getattr(cls, style.upper()) for style in styles)
        return f"{style_codes}{text}{cls.RESET}"

class ColorfulTestCase(unittest.TestCase):
    """Base class for colorful test output"""
    
    def print_color(self, message, *styles):
        """Print colorful message"""
        print(Color.colorize(message, *styles))
    
    def log_info(self, message):
        """Info level log (blue)"""
        self.print_color(f"[INFO] {message}", "BLUE")
    
    def log_success(self, message):
        """Success level log (green)"""
        self.print_color(f"[SUCCESS] {message}", "GREEN", "BOLD")
    
    def log_warning(self, message):
        """Warning level log (yellow)"""
        self.print_color(f"[WARNING] {message}", "YELLOW")
    
    def log_error(self, message):
        """Error level log (red)"""
        self.print_color(f"[ERROR] {message}", "RED", "BOLD")
    
    def log_debug(self, message):
        """Debug level log (cyan)"""
        self.print_color(f"[DEBUG] {message}", "CYAN")
    
    def log_custom(self, message, color="white", style="normal"):
        """Custom color log"""
        color_map = {
            "black": "BLACK",
            "red": "RED",
            "green": "GREEN",
            "yellow": "YELLOW",
            "blue": "BLUE",
            "magenta": "MAGENTA",
            "cyan": "CYAN",
            "white": "WHITE",
        }
        style_map = {
            "normal": "",
            "bold": "BOLD",
            "underline": "UNDERLINE",
            "italic": "ITALIC",
            "bright": "BRIGHT",
        }
        styles = []
        if color in color_map:
            styles.append(color_map[color])
        if style in style_map and style_map[style]:
            styles.append(style_map[style])
        self.print_color(message, *styles)
    
    def assertEqualWithColor(self, first, second, msg="", color="green"):
        """Colored assertEqual"""
        try:
            self.assertEqual(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {first} == {second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {first} != {second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise
    
    def assertTrueWithColor(self, expr, msg="", color="green"):
        """Colored assertTrue"""
        try:
            self.assertTrue(expr, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {expr} is True", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {expr} is not True", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

    def assertIsInstanceWithColor(self, first, second, msg="", color="green"):
        """Colored assertIsInstance"""
        try:
            self.assertIsInstance(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: type({first})=={second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: type({first})!={second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

    def assertInWithColor(self, first, second, msg="", color="green"):
        """Colored assertIsInstance"""
        try:
            self.assertIn(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {first} in {second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {first} in {second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

    def assertGreaterWithColor(self, first, second, msg="", color="green"):
        """Colored assertGreater"""
        try:
            self.assertGreater(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {first}>{second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {first}>{second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

    def assertGreaterEqualWithColor(self, first, second, msg="", color="green"):
        """Colored assertGreater"""
        try:
            self.assertGreaterEqual(first, second, msg)
            color_msg = Color.colorize(f"✓ [{msg}] [passed]: {first}>={second}", color.upper())
            print(f"  {color_msg}")
        except AssertionError as e:
            color_msg = Color.colorize(f"✗ [{msg}] [failed]: {first}>={second}", "RED", "BOLD")
            print(f"  {color_msg}")
            if msg:
                print(f"  Message: {msg}")
            raise

from tunapy.management.self_trade import (
    TokenParameter as StTokenParameter, 
)
        
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
            self.result["self_trade_params"] = params
        except:
            self.assertTrueWithColor(False, "Create params succeed")
        
        
        

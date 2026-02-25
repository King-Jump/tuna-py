""" Hedger Main
"""
import os
import sys
import json
import time
import traceback
from logging import Logger
from concurrent.futures import ThreadPoolExecutor

CURR_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.dirname(os.path.dirname(CURR_PATH))
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

from tunapy.utils.config_util import load_config
# from env import HEDGE_API_KEY, HEDGE_API_SECRET
from octopuspy.utils.log_util import create_logger
from octopuspy.exchange.base_restapi import NewOrder, OrderStatus
from tunapy.management.hedging import PrivateWSClient, TokenParameter, FilledOrder
from tunapy.hedger.bifu_private_ws import BiFuPrivateWSClient
from tunapy.cexapi.helper import get_private_client

# Exchange constants
EXCHANGE_BN = "binance"
EXCHANGE_OKX = "okx"

# Hedge execution function
def instant_hedge(
    hedge_client,
    hedge_strategy: dict,
    cl_order_id: int,
    hedge_side: str,
    hedge_qty: float,
    hedge_price: float,
    logger
) -> str:
    """ Execute hedge operation
    Args:
        hedge_client: Hedge client instance
        hedge_strategy: Hedge strategy configuration
        cl_order_id: Client order ID
        hedge_side: Hedge direction (BUY/SELL)
        hedge_qty: Hedge quantity
        hedge_price: Hedge price
        logger: Logger
    
    Returns:
        str: Hedge order ID
    """
    hedge_symbol = hedge_strategy['symbol']
    
    logger.info('Hedge %s, %s %s %s @ %s',
                cl_order_id, hedge_side, hedge_qty, hedge_symbol, hedge_price)

    if not hedge_symbol:
        logger.error('Hedge symbol is empty')
        return ''

    try:
        if not hedge_client:
            logger.error('Hedge client is None')
            return ''
        
        logger.info('Executing hedge for %s', hedge_symbol)
        
        # 创建 NewOrder 对象
        new_order = NewOrder(
            symbol=hedge_symbol,
            client_id=cl_order_id,
            side=hedge_side,
            type='LIMIT',
            quantity=hedge_qty,
            price=hedge_price,
            biz_type='SPOT',
            tif='GTC',
            position_side=''
        )
        
        logger.info('Creating hedge order: %s', new_order)
        
        # 使用 batch_make_orders 方法执行对冲
        try:
            order_ids = hedge_client.batch_make_orders(
                orders=[new_order],
                symbol=hedge_symbol
            )
            
            logger.info('Hedge order created successfully: %s', order_ids)
            
            # 从响应中获取订单ID
            if order_ids and len(order_ids) > 0:
                return order_ids[0].order_id
            else:
                logger.error('Empty response from batch_make_orders')
                return ''
        except Exception as e:
            logger.error('Hedge execution failed: %s', traceback.format_exc())
            return ''
    except Exception as e:
        logger.error('Hedge execution failed: %s', traceback.format_exc())
        return ''

class HedgerAgent():
    """The agent for BiFu hedging of risk positions
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        logger: Logger,
        monitor: Logger,
        config: TokenParameter,
        ws_client: PrivateWSClient,
    ):
        # api key and serect for hedge
        self.hedge_api_key = api_key
        self.hedge_api_secret = api_secret

        # logger for application workflow
        self.logger = logger
        # logger for hedge monitor, including ws message, bn hedge order, hedged result
        self.monitor = monitor

        # hedge strategy config
        self.config = config
        
        # 初始化对冲客户端
        self._init_hedge_client()

        # hedge strategy related data structure
        self._risk_positions = {}
        # multi-threads for hedging
        self._hedge_pool = ThreadPoolExecutor(10)
        self._hedge_tasks = {}

        # stop flag
        self._stop = False

        # performance tracking
        # self._hedge_prformance = {}

        # application name
        self.app_name = "hedger"

        # reporter
        self.reporter = logger

        self._ws_clients = ws_client # WS client for listening trade events
        self._ws_clients.start(    # start ws client
            self.config.maker_symbol,
            self.on_open,
            self.on_close,
            self.handle_trade_filled,
            self.on_error)

        # deduplicate of trade id
        self._trade_ids = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_type:
            self.logger.error(traceback.tb_frame)
            self.logger.error(exc_value)
        return True

    def on_close(self):
        """ do something when the execution report stream closed
        """
        self.logger.warning("Stream closed")

    def close(self):
        """ close the websocket client
        """
        self._stop = True
        # wait for all hedge tasks to finish
        self.wait_for_hedge_multithread(wait=True)

    def on_open(self):
        """ do something when the execution report stream opened
        """
        self.logger.debug('Open new websocket')

    def on_error(self, error):
        """ error handler
        """
        self.logger.error('WS on_error, error: %s', error)

    def _init_hedge_client(self):
        """ Initialize hedge client
        """
        try:
            # Get hedge exchange type from configuration
            hedge_exchange = self.config.hedge_exchange
            self.logger.info('Initializing hedge client for exchange: %s', hedge_exchange)
            
            # Create hedge client using get_private_client
            self._hedge_client = get_private_client(
                exchange=hedge_exchange,
                api_key=self.hedge_api_key,
                api_secret=self.hedge_api_secret,
                passphrase=self.config.passphrase,  # Read passphrase from config
                logger=self.logger
            )
            
            if self._hedge_client:
                self.logger.info('Hedge client initialized successfully')
            else:
                self.logger.error('Failed to initialize hedge client')
        except Exception as e:
            self.logger.error('Error initializing hedge client: %s', traceback.format_exc())

    def handle_trade_filled(self, data: FilledOrder):
        """ handle trade filled event
        """
        report_time = time.time()
        trade_id = data.trade_id

        if not trade_id:
            self.logger.error("Cannot get trade id from message: %s", data)
            return

        if trade_id in self._trade_ids:
            return
        self._trade_ids[trade_id] = report_time

        qty = float(data.qty)
        amount = float(data.amount)
        if qty <= 0 or amount <= 0:
            self.logger.error("Invalid trade data: %s", data)
            return

        symbol = data.symbol
        side = data.side
        avg_price = round(amount / qty, 8)
        order_id = data.order_id
        trade_time = float(data.match_time)

        self.logger.info("[p:hedger-report]%s:%s", symbol, int(report_time * 1000) - trade_time)

        self.monitor.info(
            "User-WS %s: order_id:%s, trade_id:%s, side: %s, price: %s, qty: %s, total_amt: %s",
            symbol, order_id, trade_id, side, avg_price, qty, amount)
        if order_id not in self._risk_positions:
            self._risk_positions[order_id] = {
                'symbol': symbol,
                'qty': qty,
                'price': avg_price,
                'total_amt': amount,
                'hedged_qty': 0,
                'hedged_amt': 0,
                'created_ts': report_time,
                'order': {},    # stores multiple trades if partially filled
                'side': side,
            }
        else:
            position = self._risk_positions[order_id]
            position['qty'] += qty
            position['total_amt'] += amount
            # update average price
            position['price'] = position['total_amt'] / position['qty']
        self.reporter.info("Maker,%s,%s,%s,,%s,%s,%s,",
                           order_id, symbol, side, avg_price, qty, amount)

    def _handle_risk_positions(self):
        """ handle risk positions
        """
        acc_risk_positions = {}  # risk position group by symbol
        if self._risk_positions:
            self.logger.debug("_risk_positions:%s", self._risk_positions)
        for order_id in list(self._risk_positions.keys()):
            # use try-except for performance tuning
            try:
                position = self._risk_positions[order_id]
                if position['hedged_qty'] >= position['qty']:
                    # already full hedged
                    del self._risk_positions[order_id]
                    self.monitor.info("Finished Hedge Order %s: %s", order_id, position)
                    continue

                symbol = position['symbol']
                # check hedger config
                side = position['side']
                # TODO write redis to inform maker ??

                # hedge filled or partially filled orders
                hedge_qty = position['qty'] - position['hedged_qty']
                hedge_amt = position['total_amt'] - position['hedged_amt']

                # combine hedge_amt and hedge_qty anmong multi-orders
                if symbol not in acc_risk_positions:
                    acc_risk_positions[symbol] = {
                        'qty': 0,
                        'amt': 0,
                        'order_ids': [],  # maker order ids of the same symbol
                    }

                acc_risk_positions[symbol]['order_ids'].append(order_id)
                if side == 'BUY':
                    acc_risk_positions[symbol]['qty'] += hedge_qty
                    acc_risk_positions[symbol]['amt'] += hedge_amt
                else:
                    acc_risk_positions[symbol]['qty'] -= hedge_qty
                    acc_risk_positions[symbol]['amt'] -= hedge_amt
            except Exception:
                send_maker_message(f'{symbol}_HedgeConf', f"Lost {symbol}'s hedger config")

        res = False
        if acc_risk_positions:
            self.logger.debug("acc_risk_positions: %s", acc_risk_positions)
        for symbol, position in acc_risk_positions.items():
            try:
                # use try-except for performance tuning
                # Temporarily use config object properties as hedge strategy
                hedge_strategy = {
                    'symbol': self.config.hedge_symbol,
                    'min_amt': self.config.min_amt_per_order,
                    'min_qty': self.config.min_qty_per_order
                }
                hedge_symbol = hedge_strategy['symbol']
                hedge_amt = position['amt']
                hedge_qty = position['qty']
                if abs(hedge_amt) < hedge_strategy['min_amt'] or \
                    abs(hedge_qty) < hedge_strategy['min_qty']:
                    continue

                # update risk positions
                for order_id in position['order_ids']:
                    risk_position = self._risk_positions[order_id]
                    risk_position['hedged_qty'] = risk_position['qty']
                    risk_position['hedged_amt'] = risk_position['total_amt']

                # do hedge
                if hedge_qty == 0:
                    self.monitor.info('self-hedged %s: %s', symbol, position)
                    continue
                hedge_side = 'SELL' if hedge_qty > 0 else 'BUY'

                cl_order_id = int(1000 * time.time())
                hedge_price = abs(hedge_amt) / abs(hedge_qty)
                self.monitor.info("Pre-Hedge %s: client_orderid=%s, position=%s",
                                  symbol, cl_order_id, position)
                
                future = self._hedge_pool.submit(instant_hedge, self._hedge_client, hedge_strategy, cl_order_id,
                                                 abs(hedge_amt), hedge_side, abs(hedge_qty),
                                                 hedge_price, self.logger)
                # hedge_time = int(time.time() * 1000)
                # self.logger.info("[p:hedger-process]%s:%s",
                #                  symbol, hedge_time - self._hedge_prformance.get(symbol, 0))
                
                self._hedge_tasks[cl_order_id] = {
                    "symbol": symbol,
                    "future": future,
                }
                self.monitor.info('client_orderid=%s, %s %s %s @ %s',
                                  cl_order_id, hedge_side, hedge_qty, symbol, hedge_price)
                res = True
            except Exception as e:
                self.logger.error(f"Error handling risk positions for {symbol}: {e}")
        return res

    def _remove_trade_id(self):
        """ remove trade id added 2 hour ago, in order to reduce the size of self._trade_ids
        """
        ts = time.time()
        for trade_id, create_ts in list(self._trade_ids.items()):
            if create_ts + 7200 < ts:
                del self._trade_ids[trade_id]

    def wait_for_hedge_multithread(self, wait=True) -> int:
        """ check hedge order status, record hedge performance,
            and remove hedge status from _order_status
            return number of un-finished tasks
        """
        while 1:
            try:
                for cl_order_id in list(self._hedge_tasks.keys()):
                    if cl_order_id not in self._hedge_tasks:
                        self.logger.warning("cl_order_id: %s is not in _hedge_tasks: %s",
                                            cl_order_id, self._hedge_tasks)
                        continue
                    task = self._hedge_tasks[cl_order_id]["future"]
                    symbol = self._hedge_tasks[cl_order_id]["symbol"]
                    if not task.done():  # done() is not blocked
                        continue

                    # task finished
                    hedge_order_id = task.result()
                    self.monitor.info('Hedge result %s: %s, %s', symbol, cl_order_id, hedge_order_id)
                    if not hedge_order_id:
                        # invalid hedge
                        continue

                    # Get hedge symbol from config object
                    hedge_symbol = self.config.hedge_symbol
                    if hedge_symbol == 'manual':
                        # manually hedge, skip algorithm hedge
                        continue

                    # hedged by strategy
                    res = {}
                    
                    # Use hedge client to query order status
                    if self._hedge_client:
                        try:
                            self.logger.info('Querying order status for order_id: %s, symbol: %s', 
                                         hedge_order_id, hedge_symbol)
                            
                            # Call hedge client's order_status method
                            res:OrderStatus = self._hedge_client.order_status(
                                order_id=hedge_order_id,
                                symbol=hedge_symbol
                            )
                            
                            self.logger.info('Order status response: %s', res)
                            
                            # 记录订单状态日志
                            self.monitor.info('Hedged %s: client_orderid=%s, status: %s, executedQty: %s',
                                          symbol, cl_order_id, res.get('status', ''), 
                                          res.get('executedQty', ''))
                        except Exception as e:
                            self.logger.error('Error querying order status: %s', traceback.format_exc())
                    else:
                        self.logger.warning('Hedge client not initialized, skipping order status query')

                    if cl_order_id in self._hedge_tasks:
                        del self._hedge_tasks[cl_order_id]

                if wait and self._hedge_tasks:
                    time.sleep(0.5)
                    continue
                break
            except Exception:
                self.logger.error(
                    "wait_for_hedge_multithread error: %s", traceback.format_exc())
        return len(self._hedge_tasks)

    def run_forever(self):
        """ Run forever
        """
        self.logger.debug('start hedge job with config: %s', self.config)
        # on start: check account book
        _last_operating_ts = {
            'config': 0.0,
            'log': 0.0,
            'check_tradeid': 0.0,
        }
        # start listening execution report.
        self._ws_clients.subscribe_execution_report(self.config.maker_symbol)
        while 1:
            try:
                ts = time.time()

                # Check for config updates
                if ts > _last_operating_ts['config'] + 1:
                    try:
                        # Load config from Redis
                        current_version = getattr(self.config, 'version', 0)
                        r_key = f'{self.config.maker_symbol}_{self.config.hedge_symbol}@{self.config.hedge_exchange}'
                        version, new_conf = load_config(r_key, current_version)
                        if version > current_version:
                            self.logger.info('Config updated, new version: %s', version)
                            self.config = TokenParameter(new_conf)
                            self.logger.debug('update config: %s', new_conf)
                            self._init_all_ws_clients()
                    except Exception as e:
                        self.logger.error('Error checking config update: %s', traceback.format_exc())
                    finally:
                        _last_operating_ts['config'] = ts

                # hedge by order
                res = self._handle_risk_positions()

                # check and release hedge tasks
                unhedge_cnt = self.wait_for_hedge_multithread(wait=False)
                if ts > _last_operating_ts['log'] + 60:
                    # log every minute
                    self.logger.info('|STAT| un-finished hedge orders %d, risk position size: %d',
                                      unhedge_cnt, len(self._risk_positions))
                    self.logger.info('|STAT| config: %s', self.config)
                    _last_operating_ts['log'] = ts

                # periodical remove trade id
                if not res and ts > _last_operating_ts['check_tradeid'] + 600:
                    # hedge by account balance
                    self._remove_trade_id()
                    _last_operating_ts['check_tradeid'] = ts

                time.sleep(0.1)
            except Exception:
                self.logger.error(traceback.format_exc())

        self._hedge_pool.shutdown()
        self.wait_for_hedge_multithread(True)

def main(conf: dict):
    """ The main function
    """
    try:
        param = TokenParameter(conf['token_parameter'])
        logger = create_logger(BASE_PATH, "hedger.log", 'JPM_MM')
        logger.info('start hedger with config: %s', param)
        monitor = create_logger(BASE_PATH, "HedgeMonitor.log", 'monitor_hedger', backup_cnt=50)
        # Monitor BiFu trade executions
        import pdb; pdb.set_trace()
        ws_client = BiFuPrivateWSClient(conf['private_ws_client'], logger)
        if not param.api_key or not param.api_secret:
            logger.error("Lost Hedge api key or secret")
            return
        agent = HedgerAgent(api_key=param.api_key, api_secret=param.api_secret,
                        logger=logger, monitor=monitor,
                        config=param, ws_client=ws_client)
        agent.run_forever()
    except Exception as e:
        logger.error("HedgerAgent start error: %s, %s", e, traceback.format_exc())

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python hedger_main.py <config_file>")
        sys.exit(1)
    config_file = sys.argv[1]
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
            main(config)
    except Exception as e:
        print(f"Error: failed to load config file {config_file}: {e}")
        sys.exit(1)

    main(param)

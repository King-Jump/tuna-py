""" Hedger Main
"""
import os
import sys

CURR_PATH = os.path.dirname(os.path.abspath(__file__))
BASE_PATH = os.path.dirname(CURR_PATH)
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)

from env import HEDGE_API_KEY, HEDGE_API_SECRET
from octopuspy.utils.log_util import create_logger
from management.hedging import PrivateWSClient, TokenParameter

class HedgerAgent():
    """The agent for BiFu hedging of risk positions
    """

    def __init__(
        self,
        stream_url: str,
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
        self._hedge_client = None # TODO client for hedge exchange

        # hedge strategy related data structure
        self._risk_positions = {}
        # multi-threads for hedging
        self._hedge_pool = ThreadPoolExecutor(10)
        self._hedge_tasks = {}

        # stop flag
        self._stop = False

        self._ws_clients = ws_client # TODO  WS client for listening trade events
        self._ws_clients.start(    # TODO start ws client
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

    def handle_trade_filled(self, data: dict):
        """ handle trade filled event
        """
        report_time = time.time()
        trade_id = data['tradeId']

        if not trade_id:
            self.logger.error("Cannot get trade id from message: %s", data)
            return

        if trade_id in self._trade_ids:
            return
        self._trade_ids[trade_id] = report_time

        qty = float(data['fillSize'])
        amount = float(data['fillValue'])
        if qty <= 0 or amount <= 0:
            self.logger.error("Invalid trade data: %s", data)
            return

        symbol = data['symbolId']
        side = data['orderSide']
        avg_price = round(amount / qty, 8)
        order_id = data['orderId']
        trade_time = float(data['matchTime'])

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
                _ = self.config['HEDGER'][symbol]
                side = position['side']
                # TODO write redis to inform maker

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
                if symbol not in self.config['HEDGER']:
                    send_maker_message(f'{symbol}_HedgeConf', f"Lost {symbol}'s hedger config")
                    self.logger.error('Cannot Get Hedger Config of %s', symbol)

        res = False
        if acc_risk_positions:
            self.logger.debug("acc_risk_positions: %s", acc_risk_positions)
        for symbol, position in acc_risk_positions.items():
            try:
                # use try-except for performance tuning
                hedge_strategy = self.config['HEDGER'][symbol]
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
                hedge_price = hedge_amt / hedge_qty
                self.monitor.info("Pre-Hedge %s: client_orderid=%s, position=%s",
                                  symbol, cl_order_id, position)
                future = self._hedge_pool.submit(instant_hedge, hedge_strategy, cl_order_id,
                                                 abs(hedge_amt), hedge_side, abs(hedge_qty),
                                                 hedge_price, self.logger)
                hedge_time = int(time.time() * 1000)
                self.logger.info("[p:hedger-process]%s:%s",
                                 symbol, hedge_time - self._hedge_prformance.get(symbol, 0))

                self._hedge_tasks[cl_order_id] = {
                    "symbol": symbol,
                    "future": future,
                }
                self.monitor.info('client_orderid=%s, %s %s %s @ %s',
                                  cl_order_id, hedge_side, abs(hedge_qty), symbol, hedge_price)
                res = True
            except Exception:
                if symbol not in self.config['HEDGER']:
                    self.logger.error(f"Can not get {symbol}'s hedger config")
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

                    hedge_symbol = self.config['HEDGER'][symbol]['symbol']
                    if hedge_symbol == 'manual':
                        # manually hedge, skip algorithm hedge
                        continue

                    # hedged by strategy
                    res = {}
                    if self._hedger_exchchage == EXCHANGE_BN:
                        res = self._hedge_client.order_status(order_id=hedge_order_id,
                                                              symbol=hedge_symbol)
                    if 'status' not in res:
                        # hedge order fatal error
                        send_maker_message('', {
                            'app_name': self.app_name, 'symbol': hedge_symbol,
                            'order id': hedge_order_id})
                        del self._hedge_tasks[cl_order_id]
                        continue

                    self.monitor.info('Hedged %s: client_orderid=%s, %s %s',
                                      symbol, cl_order_id, res['side'], res['executedQty'])

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
        while 1:
            try:
                ts = time.time()

                if ts > _last_operating_ts['config'] + 1:
                    if configer.has_update(self.config.get('version', 0)):
                        new_conf = configer.get_config()
                        if new_conf and new_conf['version'] > self.config['version']:
                            self.config = new_conf
                            self.logger.debug('update config: %s', new_conf)
                            self._init_all_ws_clients()
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


def main(param: TokenParameter, ws_client: PrivateWSClient):
    """ The main function
    """
    logger = create_logger(CURR_PATH, f"hedger.log", 'JPM_MM')
    logger.info('start hedger with config: %s', param)

    monitor = create_logger(CURR_PATH, "HedgeMonitor.log", f'monitor_hedger', backup_cnt=50)

    if not HEDGE_API_KEY or not HEDGE_API_SECRET:
        logger.error("Lost Hedge api key or secret")
        return

    with HedgerAgent(api_key=HEDGE_API_KEY, api_secret=HEDGE_API_SECRET,
                    logger=logger, monitor=monitor,
                    config=param, ws_client=ws_client) as agent:
        agent.run_forever()

if __name__ == '__main__':
    param = TokenParameter({
            'API KEY': '',
            'Secret': '',
            'Passphrase': '',
            'Stream URL': '',
            'Maker Symbol': '',
            'Hedge Symbol': '',
            'Hedger Price Decimals': '',
            'Hedger Qty Decimals': '',
            'Min Qty': '',
            'Min Amt': '',
            'Slippage': 0.01,
        })

    ws_client = BiFuPrivateWSClient(
        api_key=param.api_key,
        api_secret=param.api_secret,
        passphrase=param.passphrase,
        stream_url=param.stream_url,
    )

    main(param, ws_client)

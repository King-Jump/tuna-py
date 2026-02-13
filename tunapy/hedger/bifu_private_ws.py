import hmac
import hashlib

from management.hedging import PrivateWSClient

class BiFuPrivateWSClient(PrivateWSClient):
    def __init__(self, api_key: str, api_secret: str, passphrase: str, stream_url: str) -> None:
        super().__init__(api_key, api_secret, passphrase, stream_url)

        self.path = ''  # TODO
        self._ws_client = None

    def on_message(self, message):
        """ handle the message from the execution report stream
        """
        if message.get('type') == 'spot-trade-event':
            try:
                for filled_order in message['msg']['data']['orderFillTransaction']:
                    if filled_order['direction'] == 'MAKER' and filled_order['accountId'] != filled_order['matchAccountId']:
                        self.logger.info("on_message, message: %s", message)
                        # filled with user
                        self._handle_trade_filled(filled_order) # TODO: uniform filled order data structure
            except Exception:
                self.logger.error(traceback.format_exc())
            return
        self.logger.debug("No deal with message: %s ", message)

    def subscribe_execution_report(self, symbol: str):
        pass

    def start(self, symbol, on_open, on_close, on_error, handle_trade_filled):
        self._handle_trade_filled = handle_trade_filled
        self._ws_client = self._ws_connect(on_open, on_close, on_error)

    def _sign(self) -> dict:
        """ sign private websocket
        """
        ts = int(1000 * time.time())
        message = f'{self.path}|{ts}'

        signature = hmac.new(
            self.api_secret.encode("utf-8"), message.encode("utf-8"), hashlib.sha256)
        return {
            'Decode-MM-Auth-Access-Key': self.api_key,
            'Decode-MM-Auth-Timestamp': str(ts),
            'Decode-MM-Auth-Signature': signature.hexdigest(),
        }

    def _ws_connect(self, on_open, on_close, on_error):
        _ws_client = None
        for _ in range(10):
            try:
                headers = self._sign()
                _ws_client = UserWebsocketStreamClient(
                    stream_url=f'{self.stream_url}{self.path}',
                    on_open=on_open,
                    on_close=on_close,
                    on_error=on_error,
                    on_message=self.on_message,
                    client_id=self.api_key,
                    logger=self.logger,
                    headers=headers)
                break
            except Exception as e:
                self.logger.error("Exception in create ws connect %s, try again...", e)
            time.sleep(0.05)
        return _ws_client

# TODO: binance spot client for hedging
client = None

def instant_hedge(
    param: TokenParameter,
    cl_order_id: str,
    hedge_side: str,
    hedge_qty: float,
    ref_price: float,
    logger: Logger,
) -> str:
    """ hedge in a new thread when a maker order is (partially) filled,
        return hedge_order_id
    """
    # hedge in another thread
    hedge_s_time = time.time()
    hedge_symbol = param.hedge_symbol
    slippage = min(10, max(1.0, param.slippage))
    if hedge_side == 'BUY':
        ref_price *= 1.0 + 0.01 * slippage
    if hedge_side == 'SELL':
        ref_price *= 1.0 - 0.01 * slippage
    logger.info('Hedge %s, %s %s %s, slippage=%s',
                cl_order_id, hedge_side, hedge_qty, hedge_symbol, slippage)

    if not hedge_symbol:
        return ''

    try:
        # hedge the token on another Exchange
        res = client.make_order(hedge_symbol, hedge_side.upper(),
                                round(ref_price, param.price_decimals),
                                round(hedge_qty, param.qty_decimals),
                                cl_order_id, 'LIMIT')
      
        logger.info("Hedger %s result %s", cl_order_id, res)
        if not res or 'status' not in res:
            logger.error("Hedger %s result %s", cl_order_id, res)
            return ''

        hedge_e_time = time.time()
        logger.info("[p:hedger-make]%s:%s", hedge_symbol, int((hedge_e_time - hedge_s_time) * 1000))
        logger.info("Hedged %s status %s", cl_order_id, res)

        return res['orderId']

    except Exception:
        logger.error(traceback.format_exc())

    return '', 0, ''

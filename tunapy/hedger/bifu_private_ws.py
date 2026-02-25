import hmac
import hashlib
import time
import traceback
from logging import Logger

from tunapy.management.hedging import PrivateWSClient, TokenParameter, FilledOrder
from tunapy.hedger.websocket_client import UserWebsocketStreamClient

class BiFuPrivateWSClient(PrivateWSClient):
    def __init__(self, config: dict, logger:Logger) -> None:
        super().__init__(config, logger)
        self.path = '/api/v1/private/ws'
        self._ws_client = None  # create web client in start function
        self._handle_trade_filled = None  # function to process filled trades，setup in start function

    """
    WebSocket连接成功之后，Server端会以固定频率向Client端发送Ping消息，消息体如下：
    {"type":"ping","time":"1693208170000"}，
    其中time标示的是Server端Ping时刻的时间戳。此时Client端在收到消息后，请回复服务端Pong消息，
    消息体内容为
    {"type":"pong","time":"1693208170000"}。超过5次不回应，服务端会主动断开当前连接。
    """
    def on_message(self, message):
        """ handle the message from the execution report stream
        """
        if message.get('type') == 'spot-trade-event':
            try:
                for filled_order in message['msg']['data']['orderFillTransaction']:
                    if filled_order['direction'] == 'MAKER' and filled_order['accountId'] != filled_order['matchAccountId']:
                        self.logger.info("on_message, message: %s", message)
                        # filled with user order
                        filled_order = FilledOrder(
                            trade_id=filled_order['tradeId'],
                            qty=filled_order['fillSize'],
                            amount=filled_order['fillValue'],
                            symbol=filled_order['symbolId'],
                            side=filled_order['orderSide'],
                            order_id=filled_order['orderId'],
                            match_time=filled_order['matchTime'],
                        )
                        self._handle_trade_filled(filled_order)
            except Exception:
                self.logger.error(traceback.format_exc())
            return
        if message.get('type') == 'ping':
            self.logger.debug("ping message received: %s", message)
            pong_message = {'type': 'pong', 'time': str(time.time())}
            self._ws_client.send(pong_message)
            return
        self.logger.debug("No deal with message: %s ", message)

    def subscribe_execution_report(self, symbol: str):
        """ Subscribe to execution report stream
        Args:
            symbol: Trading pair symbol

        Bifu private ws client can receive orderFillTransaction message automatically. No need to subscribe.
        message like:
        {
            "type": "spot-trade-event",
            "msg": {
                "data": {
                    ......
                    "orderFillTransaction": [
                        {
                            "orderId": "123456",
                            "symbolId": "BTC-USDT",
                            "orderSide": "BUY",
                            "direction": "MAKER",
                            "fillSize": "0.01",
                            "fillValue": "1000",
                            "tradeId": "123456",
                            "matchTime": "1633046400000"
                            ......
                        }
                    ]
                }
            }
        }
        
        """
        self.logger.info('subscribed to execution report for symbol: %s, please check the log for filled orders', symbol)

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

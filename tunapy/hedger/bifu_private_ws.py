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
                        self.logger.info("on_message, client_id: %s, message: %s", client_id[:8], message)
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

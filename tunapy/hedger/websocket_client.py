import websocket
import json
import time
from logging import Logger

class UserWebsocketStreamClient:
    """ WebSocket client for user stream
    """
    def __init__(
        self,
        stream_url: str,
        on_open=None,
        on_close=None,
        on_error=None,
        on_message=None,
        client_id: str = '',
        logger: Logger = None,
        headers: dict = None
    ):
        """
        Initialize WebSocket client
        
        Args:
            stream_url: WebSocket stream URL
            on_open: Callback function when connection is opened
            on_close: Callback function when connection is closed
            on_error: Callback function when error occurs
            on_message: Callback function when message is received
            client_id: Client ID
            logger: Logger
            headers: HTTP headers
        """
        self.stream_url = stream_url
        self.on_open = on_open
        self.on_close = on_close
        self.on_error = on_error
        self.on_message = on_message
        self.client_id = client_id
        self.logger = logger
        self.headers = headers
        self.ws = None
        
        # Connect to WebSocket
        self._connect()
    
    def _connect(self):
        """
        Connect to WebSocket stream
        """
        try:
            self.ws = websocket.WebSocketApp(
                self.stream_url,
                on_open=self._on_open,
                on_close=self._on_close,
                on_error=self._on_error,
                on_message=self._on_message,
                header=self.headers
            )
            
            # Start WebSocket in a separate thread
            import threading
            self.thread = threading.Thread(target=self.ws.run_forever)
            self.thread.daemon = True
            self.thread.start()
            
            self.logger.info(f"WebSocket client connected to {self.stream_url}")
        except Exception as e:
            self.logger.error(f"Failed to connect to WebSocket: {e}")
    
    def _on_open(self, ws):
        """
        Callback function when connection is opened
        """
        if self.logger:
            self.logger.info("WebSocket connection opened")
        if self.on_open:
            self.on_open()
    
    def _on_close(self, ws, close_status_code, close_msg):
        """
        Callback function when connection is closed
        """
        if self.logger:
            self.logger.info(f"WebSocket connection closed: {close_status_code} - {close_msg}")
        if self.on_close:
            self.on_close()
    
    def _on_error(self, ws, error):
        """
        Callback function when error occurs
        """
        if self.logger:
            self.logger.error(f"WebSocket error: {error}")
        if self.on_error:
            self.on_error(error)
    
    def _on_message(self, ws, message):
        """
        Callback function when message is received
        """
        try:
            # Parse JSON message
            msg = json.loads(message)
            if self.on_message:
                self.on_message(msg)
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"Failed to parse WebSocket message: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Error handling WebSocket message: {e}")
    
    def close(self):
        """
        Close WebSocket connection
        """
        if self.ws:
            self.ws.close()
            if self.logger:
                self.logger.info("WebSocket connection closed")

import asyncio
import websockets
import json
from logging import Logger
from typing import Dict, List, Optional, Callable

class BifuPublicWSClient:
    """ WebSocket Client for Public Data of BiFu
    """
    def __init__(self, url: str = "wss://ws.bifu.co", logger: Optional[Logger] = None):
        """ Initialize WebSocket Client
        
        Args:
            url: WebSocket URL
            logger: Logger instance
        """
        self.url = url
        self.logger = logger
        self.websocket = None
        self.is_connected = False
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.reconnect_interval = 5  # seconds
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_task = None
        self.reconnect_task = None
    
    async def connect(self):
        """ Connect to WebSocket server
        """
        try:
            self.websocket = await websockets.connect(self.url)
            self.is_connected = True
            if self.logger:
                self.logger.info(f"Connected to Bifu WebSocket: {self.url}")
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self._heartbeat())
            
            # Start message handler task
            await self._handle_messages()
        except Exception as e:
            if self.logger:
                self.logger.error(f"WebSocket connection error: {e}")
            self.is_connected = False
            await self._reconnect()
    
    async def _reconnect(self):
        """ Reconnect to WebSocket server
        """
        if self.logger:
            self.logger.info(f"Attempting to reconnect in {self.reconnect_interval} seconds...")
        await asyncio.sleep(self.reconnect_interval)
        await self.connect()
    
    async def _heartbeat(self):
        """ Send heartbeat messages to keep connection alive
        """
        while self.is_connected:
            try:
                if self.websocket:
                    heartbeat_msg = json.dumps({"op": "ping"})
                    await self.websocket.send(heartbeat_msg)
                    if self.logger:
                        self.logger.debug("Sent heartbeat")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Heartbeat error: {e}")
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _handle_messages(self):
        """ Handle incoming WebSocket messages
        """
        while self.is_connected:
            try:
                if self.websocket:
                    message = await self.websocket.recv()
                    await self._process_message(message)
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Message handling error: {e}")
                break
    
    async def _process_message(self, message: str):
        """ Process incoming message
        
        Args:
            message: Raw JSON message
        """
        try:
            data = json.loads(message)
            
            # Handle heartbeat response
            if data.get("op") == "pong":
                if self.logger:
                    self.logger.debug("Received pong")
                return
            
            # Handle subscription messages
            if "channel" in data:
                channel = data["channel"]
                if channel in self.message_handlers:
                    for handler in self.message_handlers[channel]:
                        await handler(data)
        except json.JSONDecodeError as e:
            if self.logger:
                self.logger.error(f"JSON decode error: {e}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Message processing error: {e}")
    
    async def subscribe(self, channel: str, params: Dict, callback: Callable):
        """ Subscribe to a WebSocket channel
        
        Args:
            channel: Channel name
            params: Subscription parameters
            callback: Message callback function
        """
        if not self.is_connected:
            if self.logger:
                self.logger.error("Not connected to WebSocket")
            return
        
        # Add callback to handlers
        if channel not in self.message_handlers:
            self.message_handlers[channel] = []
        self.message_handlers[channel].append(callback)
        
        # Send subscription message
        subscribe_msg = {
            "op": "subscribe",
            "channel": channel,
            "params": params
        }
        
        try:
            if self.websocket:
                await self.websocket.send(json.dumps(subscribe_msg))
                if self.logger:
                    self.logger.info(f"Subscribed to channel: {channel} with params: {params}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Subscription error: {e}")
    
    async def unsubscribe(self, channel: str, params: Dict):
        """ Unsubscribe from a WebSocket channel
        
        Args:
            channel: Channel name
            params: Unsubscription parameters
        """
        if not self.is_connected:
            if self.logger:
                self.logger.error("Not connected to WebSocket")
            return
        
        # Send unsubscription message
        unsubscribe_msg = {
            "op": "unsubscribe",
            "channel": channel,
            "params": params
        }
        
        try:
            if self.websocket:
                await self.websocket.send(json.dumps(unsubscribe_msg))
                if self.logger:
                    self.logger.info(f"Unsubscribed from channel: {channel}")
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unsubscription error: {e}")
    
    async def subscribe_ticker(self, symbol: str, callback: Callable):
        """ Subscribe to ticker channel
        
        Args:
            symbol: Trading symbol (e.g., "90000001" for BTC-USDT)
            callback: Ticker data callback
        """
        params = {
            "instrumentId": symbol
        }
        await self.subscribe("ticker", params, callback)
    
    async def subscribe_orderbook(self, symbol: str, callback: Callable, depth: int = 15):
        """ Subscribe to orderbook channel
        
        Args:
            symbol: Trading symbol (e.g., "90000001" for BTC-USDT)
            callback: Order book data callback
            depth: Order book depth (15 or 200)
        """
        params = {
            "instrumentId": symbol,
            "level": depth
        }
        await self.subscribe("depth", params, callback)
    
    async def subscribe_trades(self, symbol: str, callback: Callable):
        """ Subscribe to trades channel
        
        Args:
            symbol: Trading symbol (e.g., "90000001" for BTC-USDT)
            callback: Trades data callback
        """
        params = {
            "instrumentId": symbol
        }
        await self.subscribe("trade", params, callback)
    
    async def close(self):
        """ Close WebSocket connection
        """
        self.is_connected = False
        
        # Cancel tasks
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        if self.reconnect_task:
            self.reconnect_task.cancel()
        
        # Close websocket
        if self.websocket:
            try:
                await self.websocket.close()
                if self.logger:
                    self.logger.info("WebSocket connection closed")
            except Exception as e:
                if self.logger:
                    self.logger.error(f"Error closing websocket: {e}")
    
    async def start(self):
        """ Start WebSocket client
        """
        await self.connect()


# Example usage
async def example():
    """ Example usage of BifuPublicWSClient
    """
    import logging
    
    # Configure logger
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("bifu_ws")
    
    # Create client
    client = BifuPublicWSClient(logger=logger)
    
    # Define callbacks
    async def ticker_callback(data):
        logger.info(f"Ticker data: {json.dumps(data, indent=2)}")
    
    async def orderbook_callback(data):
        logger.info(f"Orderbook data: {json.dumps(data, indent=2)}")
    
    async def trades_callback(data):
        logger.info(f"Trades data: {json.dumps(data, indent=2)}")
    
    try:
        # Start client
        await client.start()
        
        # Subscribe to channels
        await client.subscribe_ticker("90000001", ticker_callback)  # BTC-USDT
        await client.subscribe_orderbook("90000001", orderbook_callback, depth=15)
        await client.subscribe_trades("90000001", trades_callback)
        
        # Run for 60 seconds
        await asyncio.sleep(60)
    finally:
        # Close client
        await client.close()


if __name__ == "__main__":
    asyncio.run(example())

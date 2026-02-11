

### setup octopus-py package
```
pip install -e ../octopus-py/
```
### Debug
```python
class BinanceWebsocketClient:
    ACTION_SUBSCRIBE = "SUBSCRIBE"
    ACTION_UNSUBSCRIBE = "UNSUBSCRIBE"

    def __init__(
        self,
        stream_url,
        on_message=None,
        on_open=None,
        on_close=None,
        on_error=None,
        on_ping=None,
        on_pong=None,
        logger=None,
        proxies: Optional[dict] = None,
        timeout = None,
        time_unit = None,
    ):
```
### Bifu symbolId
```
https://api.bifu.co/api/v1/public/meta/getMetaData
```
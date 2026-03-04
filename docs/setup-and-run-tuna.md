# SET UP
## Clone King-Jump open source project
```
mkdir king-jump
cd king-jump
git clone https://github.com/King-Jump/octopus-py.git
git clone https://github.com/King-Jump/tuna-py.git
```
## Install required packages
```
cd tuna-py/
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
## Install local package Octopus-py
```
pip install -e <octopus dir>

# example:
pip install -e ../octopus-py/
```
## Edit redis password
vi tunapy/utils/db_util.py
```
REDIS_CONFIG = {
    "host": "127.0.0.1", "port": 6379, "password": "xxxxxx",
    "max_connections": 5,
    "socket_connect_timeout": 1,
    "health_check_interval": 30,
    "decode_responses": True,
}
```
# SPOT MARKET MAKING
## Start the quote module
```
python3 tunapy/quote/market_main.py binance_spot --maker_json=examples/mm_params.json 
```

## Check quote output
```
tail -f log/bn_pub_ws.log | grep "Update Depth"
```
## Edit maker API KEY, Secret, Passphrase:
vi examples/mm_params.json
```
        "API KEY": "xxxx",
        "Secret": "xxxx",
        "Passphrase": "xxx",
```

## Run the market_making module
```
python3 tunapy/maker/market_maker.py examples/mm_params.json
```
## Check market_making response
```
tail -f log/market_making.log | grep "Client batch_make_orders response:"
```
# FUTURE MARKET MAKING
## Start the quote module
```
python3 tunapy/quote/market_main.py binance_future --maker_json=examples/mm_future_params.json 
```
## Check quote output
```
tail -f log/bn_future_pub_ws.log | grep "Update Future Depth"
```
## Edit maker API KEY, Secret, Passphrase:
vi examples/mm_future_params.json
```
        "API KEY": "xxxx",
        "Secret": "xxxx",
        "Passphrase": "xxx",
```
## Run the market_making module
```
python3 tunapy/maker/market_maker.py examples/mm_future_params.json
```
## Check market_making response
```
tail -f log/market_making.log | grep " bifu server response:"
```
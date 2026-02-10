cd ~/bifu_finance/open_source/tuna-py
source venv/bin/activate
python3 tunapy/quote/market_main.py binance_spot --st_json=tests/st_params_bn.json
python3 tunapy/quote/market_main.py binance_future --st_json=tests/st_params_bns.json
python3 tunapy/quote/market_main.py okx_spot --st_json=tests/st_params_okx.json
python3 tunapy/quote/market_main.py okx_future --st_json=tests/st_params_okx.json

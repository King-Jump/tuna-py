cd ~/bifu_finance/open_source/tuna-py
source venv/bin/activate
python3 tunapy/quote/market_main.py binance_spot --st_json=tests/test_st_params_bn.json
python3 tunapy/quote/market_main.py binance_future --st_json=tests/test_st_params_bn.json
python3 tunapy/quote/market_main.py binance_spot --maker_json=tests/test_mm_params_bn.json --st_json=tests/test_st_params_bn.json
python3 tunapy/quote/market_main.py binance_future --maker_json=tests/test_mm_params_bn_1000pepe.json
cd ~/bifu_finance/open_source/tuna-py
source venv/bin/activate
PYTHONPATH=../ python3 tunapy/maker/market_maker.py tests/test_mm_params_bn.json
PYTHONPATH=../ python3 tunapy/maker/market_maker.py tests/test_mm_params_bn_1000pepe.json

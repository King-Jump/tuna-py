cd ~/bifu_finance/open_source/tuna-py
source venv/bin/activate
python3 tunapy/hedger/hedger_main.py tests/test_hedger_params.json
python3 tunapy/hedger/hedger_main.py tests/test_hedger_future_params.json

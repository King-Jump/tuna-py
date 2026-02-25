# tuna-py

## Project Introduction

tuna-py is a professional cryptocurrency trading system that provides comprehensive solutions for market making, self-trading testing, and risk hedging. The system consists of four core modules: market data subscription module, self-trading module, market making module, and hedging module, supporting spot and futures markets of multiple mainstream exchanges.

### Main Features

- **Market Data Subscription**: Real-time subscription of market data from exchanges like Binance and OKX, stored in Redis
- **Self-Trading Test**: Simulate trading behaviors to test market liquidity and trade execution
- **Intelligent Market Making**: Automatically generate buy and sell orders based on real-time market data to provide market liquidity
- **Risk Hedging**: Execute hedging operations to manage risk exposure across different exchanges
- **Multi-Exchange Support**: Support for spot and futures markets on Binance and OKX
- **Parameterized Configuration**: Flexibly adjust strategy parameters through JSON configuration files
- **Normalized Exchange Interface**: Use unified API interface for different exchanges through octopus-py
- **WebSocket Integration**: Real-time execution report streaming for timely hedging decisions

## Directory Structure

```
tuna-py/
├── tunapy/
│   ├── quote/             # Market data subscription module
│   │   ├── __init__.py          # Package initialization
│   │   ├── market_main.py        # Main entry of market data module
│   │   ├── bn_public_ws.py       # Binance spot market data subscription
│   │   ├── bn_future_public_ws.py # Binance futures market data subscription
│   │   ├── okx_public_ws.py      # OKX spot market data subscription
│   │   ├── okx_future_public_ws.py # OKX futures market data subscription
│   │   └── redis_client.py       # Redis client for market data
│   ├── self_trader/       # Self-trading module
│   │   └── self_trader.py        # Main entry of self-trading module
│   ├── maker/             # Market making module
│   │   ├── market_maker.py       # Main entry of market making module
│   │   └── maker_libs.py         # Market making utility functions
│   ├── management/        # Management module
│   │   ├── __init__.py          # Package initialization
│   │   ├── market_making.py      # Market making parameter definition
│   │   ├── self_trade.py         # Self-trading parameter definition
│   │   └── hedging.py            # Hedging parameter definition
│   ├── cexapi/            # Exchange API
│   │   └── helper.py             # API client helper functions
│   ├── hedger/            # Hedging module
│   │   ├── hedger_main.py        # Main entry of hedging module
│   │   ├── bifu_private_ws.py    # BiFu private WebSocket client
│   │   └── websocket_client.py   # WebSocket client implementation
│   └── utils/             # Utility functions
│       ├── __init__.py          # Package initialization
│       ├── config_util.py        # Configuration utility
│       └── db_util.py            # Database utility
├── docs/                  # Documentation
│   ├── hedger_flowchart.md       # Hedging module flowchart
│   ├── market_maker_flowchart.md # Market making module flowchart
│   ├── quote_flowchart.md        # Market data module flowchart
│   └── self_trade_flowchart.md  # Self-trading module flowchart
├── examples/              # Examples
│   ├── hedger_params.json        # Hedging parameter example
│   ├── mm_params.json            # Market making parameter example
│   └── st_params_bn.json         # Self-trading parameter example
├── tests/                 # Tests
│   ├── bn_quote_test.py          # Binance quote test
│   ├── run_hedger.sh             # Hedger module run script
│   ├── run_market.sh             # Market data module run script
│   ├── run_marketmaker.sh        # Market making module run script
│   └── run_selftrader.sh         # Self-trading module run script
├── requirements.txt       # Dependencies
├── LICENSE                # License
└── README.md              # Project description
```

## Related Projects
### octopus-py
This project contains multiple exchange clients, and you can also develop your own exchange client based on octopus-py and reference it in tuna-py.
```
https://github.com/King-Jump/octopus-py
```

## Software Running Process

### 3.1 Market Data Module

#### 3.1.1 Startup Command

```bash
# Command format:
python tunapy/quote/market_main.py <exchange> --maker_json=<market maker params> --st_json=<self trade params>

# Examples:
# Subscribe to Binance spot market data
python tunapy/quote/market_main.py binance_spot --maker_json=examples/mm_params.json --st_json=examples/st_params_bn.json

# Subscribe to Binance futures market data
python tunapy/quote/market_main.py binance_future --maker_json=examples/mm_params.json --st_json=examples/st_params_bn.json

# Subscribe to OKX spot market data
python tunapy/quote/market_main.py okx_spot --maker_json=examples/mm_params.json --st_json=examples/st_params_bn.json

# Subscribe to OKX futures market data
python tunapy/quote/market_main.py okx_future --maker_json=examples/mm_params.json --st_json=examples/st_params_bn.json
```

#### 3.1.2 Market Data Module Parameter Description

Market data module parameters are specified through command line arguments:

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| exchange | Exchange type | binance_spot, binance_future, okx_spot, okx_future |
| --maker_json | Path to market maker parameters JSON file | docs/mm_params.json |
| --st_json | Path to self-trade parameters JSON file | docs/st_params_bn.json |

#### 3.1.3 Exchange Types

```
- binance_spot: Binance spot market data
- binance_future: Binance futures market data
- okx_spot: OKX spot market data
- okx_future: OKX futures market data
```

### 3.2 SelfTrade Module

#### 3.2.1 Startup Command

```bash
# Command format:
python tunapy/self_trader/self_trader.py <self trade params>

# Example:
python tunapy/self_trader/self_trader.py examples/st_params_bn.json
```

#### 3.2.2 SelfTrade Module Parameter Description

Self-trade module parameters are specified through JSON configuration files, example configuration:

```json
[
  {
    "Maker Exchange": "binance_spot",
    "API KEY": "your_api_key",
    "Secret": "your_api_secret",
    "Passphrase": "your_passphrase",
    "Follow Exchange": "binance_spot",
    "Follow Symbol": "BTCUSDT",
    "Maker Symbol": "BTCUSDT",
    "Term type": "SPOT",
    "Price Decimals": 2,
    "Qty Decimals": 6,
    "Position Side": "",
    "Interval": 1.0,
    "Qty Multiplier": 0.1,
    "Price Divergence": 0.001,
    "Max Amt Per Order": 1000.0,
    "Min Qty": 0.0001,
    "Min Amt": 10.0
  }
]
```

#### Main Parameter Description:

| Parameter | Description | Type |
|-----------|-------------|------|
| Maker Exchange | Market making exchange | String |
| API KEY | API key | String |
| Secret | API secret | String |
| Passphrase | Passphrase (required for OKX) | String |
| Follow Exchange | Exchange to follow for market data | String |
| Follow Symbol | Symbol to follow | String |
| Maker Symbol | Symbol for market making | String |
| Term type | Trading type (SPOT/FUTURE) | String |
| Price Decimals | Price decimal places | Integer |
| Qty Decimals | Quantity decimal places | Integer |
| Position Side | Position side (LONG/SHORT) | String |
| Interval | Trading interval (seconds) | Float |
| Qty Multiplier | Quantity multiplier | Float |
| Price Divergence | Price divergence threshold | Float |
| Max Amt Per Order | Maximum amount per order | Float |
| Min Qty | Minimum order quantity | Float |
| Min Amt | Minimum order amount | Float |

### 3.3 MarketMaking Module

#### 3.3.1 Startup Command

```bash
# Command format:
python tunapy/maker/market_maker.py <market maker params>

# Example:
python tunapy/maker/market_maker.py examples/mm_params.json
```

#### 3.3.2 MarketMaking Module Parameter Description

Market making module parameters are specified through JSON configuration files, example configuration:

```json
[
  {
    "Maker Exchange": "binance_spot",
    "API KEY": "your_api_key",
    "Secret": "your_api_secret",
    "Passphrase": "your_passphrase",
    "Follow Exchange": "binance_spot",
    "Follow Symbol": "BTCUSDT",
    "Maker Symbol": "BTCUSDT",
    "Term type": "SPOT",
    "Maker Price Decimals": 2,
    "Maker Qty Decimals": 6,
    "Position Side": "",
    "Far Interval": 5.0,
    "Far Quote Timeout": 10.0,
    "Far Side": "BOTH",
    "Far TIF": "GTX",
    "Far Strategy": "SPREAD",
    "Far Buy Price Margin": 10,
    "Far Sell Price Margin": 10,
    "Far Qty Multiplier": 0.1,
    "Far Ask Size": 5,
    "Far Bid Size": 5,
    "Far Max Amt Per Order": 1000.0,
    "Far Min Qty": 0.0001,
    "Far Min Amt": 10.0,
    "Far Diff Per Round": 50,
    "Near Interval": 1.0,
    "Near Quote Timeout": 5.0,
    "Near Side": "BOTH",
    "Near TIF": "GTX",
    "Near Strategy": "SPREAD",
    "Near Buy Price Margin": 1,
    "Near Sell Price Margin": 1,
    "Near Qty Multiplier": 0.1,
    "Near Ask Size": 3,
    "Near Bid Size": 3,
    "Near Max Amt Per Order": 1000.0,
    "Near Min Qty": 0.0001,
    "Near Min Amt": 10.0,
    "Near Diff Per Round": 10,
    "Force Refresh Num": 10
  }
]
```

#### Main Parameter Description:

| Parameter | Description | Type |
|-----------|-------------|------|
| Maker Exchange | Market making exchange | String |
| API KEY | API key | String |
| Secret | API secret | String |
| Passphrase | Passphrase (required for OKX) | String |
| Follow Exchange | Exchange to follow for market data | String |
| Follow Symbol | Symbol to follow | String |
| Maker Symbol | Symbol for market making | String |
| Term type | Trading type (SPOT/FUTURE) | String |
| Maker Price Decimals | Price decimal places | Integer |
| Maker Qty Decimals | Quantity decimal places | Integer |
| Position Side | Position side (LONG/SHORT) | String |

**Far-end Order Parameters**:

| Parameter | Description | Type |
|-----------|-------------|------|
| Far Interval | Far-end order update interval (seconds) | Float |
| Far Quote Timeout | Far-end market data timeout (seconds) | Float |
| Far Side | Far-end order direction (BUY/SELL/BOTH) | String |
| Far TIF | Far-end order time in force (GTX/GTC) | String |
| Far Strategy | Far-end market making strategy | String |
| Far Buy Price Margin | Far-end buy order price margin | Integer |
| Far Sell Price Margin | Far-end sell order price margin | Integer |
| Far Qty Multiplier | Far-end order quantity multiplier | Float |
| Far Ask Size | Number of far-end ask levels | Integer |
| Far Bid Size | Number of far-end bid levels | Integer |
| Far Max Amt Per Order | Maximum amount per far-end order | Float |
| Far Min Qty | Minimum far-end order quantity | Float |
| Far Min Amt | Minimum far-end order amount | Float |
| Far Diff Per Round | Far-end order price difference threshold | Integer |

**Near-end Order Parameters**:

| Parameter | Description | Type |
|-----------|-------------|------|
| Near Interval | Near-end order update interval (seconds) | Float |
| Near Quote Timeout | Near-end market data timeout (seconds) | Float |
| Near Side | Near-end order direction (BUY/SELL/BOTH) | String |
| Near TIF | Near-end order time in force (GTX/GTC) | String |
| Near Strategy | Near-end market making strategy | String |
| Near Buy Price Margin | Near-end buy order price margin | Integer |
| Near Sell Price Margin | Near-end sell order price margin | Integer |
| Near Qty Multiplier | Near-end order quantity multiplier | Float |
| Near Ask Size | Number of near-end ask levels | Integer |
| Near Bid Size | Number of near-end bid levels | Integer |
| Near Max Amt Per Order | Maximum amount per near-end order | Float |
| Near Min Qty | Minimum near-end order quantity | Float |
| Near Min Amt | Minimum near-end order amount | Float |
| Near Diff Per Round | Near-end order price difference threshold | Integer |
| Force Refresh Num | Force refresh rounds | Integer |

### 3.4 Hedging Module

#### 3.4.1 Startup Command

```bash
# Command format:
python tunapy/hedger/hedger_main.py <config_file>

# Example:
python tunapy/hedger/hedger_main.py examples/hedger_params.json
```

#### 3.4.2 Hedging Module Overview

The hedging module is designed to manage risk exposure by executing hedge trades on different exchanges. It monitors execution reports through WebSocket and automatically executes hedge orders to offset risk positions.

#### Key Features:

- **Real-time Risk Monitoring**: Monitors trade executions through WebSocket for timely risk assessment
- **Cross-Exchange Hedging**: Supports hedging across different exchanges using normalized API interface
- **Batch Order Execution**: Uses batch_make_orders API for efficient order execution
- **Consistent Client Order IDs**: Generates consistent client_order_id for reliable tracking
- **Multi-threaded Execution**: Uses thread pool for asynchronous hedge execution
- **Comprehensive Error Handling**: Robust error handling and logging for reliable operation

#### Configuration Requirements:

The hedging module requires a JSON configuration file with two main sections:

1. **token_parameter**: Contains parameters for the maker account and hedge settings
2. **private_ws_client**: Contains WebSocket connection parameters for execution report streaming

For detailed configuration parameters, refer to the [hedging module flowchart](./docs/hedger_flowchart.md).

## Installation and Dependencies

### Dependencies

- redis: Used for storing market data and order information
- requests: Used for API requests
- python-binance: Binance API client
- binance-connector: Binance official connector
- binance-futures-connector: Binance futures API client
- python-okx: OKX API client
- ujson: High-performance JSON parsing
- octopus-py: Trading interface implementation (local dependency)

### Install Dependencies

```bash
pip install -r requirements.txt

```

## Running Process

### 1. Start Market Data Module

First start the market data module to subscribe to exchange market data:

```bash
python tunapy/quote/market_main.py binance_spot --maker_json examples/mm_params.json --st_json examples/st_params_bn.json
```

### 2. Start Self-Trade Module (Optional)

If you need to test liquidity, you can start the self-trade module:

```bash
python tunapy/self_trader/self_trader.py examples/st_params_bn.json
```

### 3. Start Market Making Module

Finally start the market making module to begin providing liquidity:

```bash
python tunapy/maker/market_maker.py examples/mm_params.json
```

### 4. Start Hedging Module (Optional)

If you need to perform hedging operations, you can start the hedging module:

```bash
# Command format:
python tunapy/hedger/hedger_main.py <config_file>

# Example:
python tunapy/hedger/hedger_main.py examples/hedger_params.json
```

#### Hedging Module Parameter Description

Hedging module parameters are specified through JSON configuration files, example configuration:

```json
{
    "token_parameter": {
        "Maker Exchange": "",
        "API KEY": "",
        "Secret": "",
        "Passphrase": "",
        "Stream URL": "",
        "Maker Symbol": "",
        "Hedge Symbol": "",
        "Hedge Exchange": "",
        "Hedger Price Decimals": "",
        "Hedger Qty Decimals": "",
        "Min Qty": "",
        "Min Amt": "",
        "Slippage": 0.01
    },
    "private_ws_client": {
        "API KEY": "",
        "Secret": "",
        "Passphrase": "",
        "Stream URL": ""
    }
}
```

## Logs

System running logs are stored in the `log/` directory:

- `market_making.log`: Market making module logs
- `selftrade.log`: Self-trade module logs
- `hedger.log`: Hedging module logs
- `HedgeMonitor.log`: Hedging monitor logs
- `bn_pub_ws.log`: Binance spot market data logs
- `bn_future_pub_ws.log`: Binance futures market data logs
- `okx_pub_ws.log`: OKX spot market data logs
- `okx_future_pub_ws.log`: OKX futures market data logs

## Notes

1. **API Key Security**: Keep API keys secure and avoid storing them in plaintext in configuration files
2. **Parameter Tuning**: Adjust market making parameters based on market conditions and symbol characteristics to achieve optimal results
3. **Risk Control**: Set reasonable order sizes and price ranges to avoid excessive risk
4. **Network Stability**: Ensure stable network connection to avoid order execution anomalies due to network issues
5. **Redis Service**: Ensure Redis service is running properly, as market data and market making modules depend on Redis for data storage
6. **Exchange Limits**: Understand and comply with each exchange's API call limits and rules

## 5 Module Implementations
### 5.1 Market Data Module
Find details in [**market data flowchart**](./docs/quote_flowchart.md)
### 5.2 Self Trade Module
Find details in [**self trade flowchart**](./docs/self_trade_flowchart.md)
### 5.3 Market Maker Module
Find details in [**market maker flowchart**](./docs/market_maker_flowchart.md)
### 5.4 Hedging Module
Find details in [**hedging module flowchart**](./docs/hedger_flowchart.md)

## 6 License
This project is licensed under the MIT License. See the LICENSE file for details.

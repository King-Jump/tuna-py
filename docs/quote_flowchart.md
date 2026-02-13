# Quote Module Flow Chart

## Overall Process Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Start Quote Module                                             │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Parse Command Line Arguments                                   │
│ - exchange: Exchange type                                      │
│ - --maker_json: Maker params file path                         │
│ - --st_json: Self-trade params file path                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Load Parameter Configuration Files                             │
│ - Load maker parameters (maker_params)                         │
│ - Load self-trade parameters (selftrade_params)                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Extract Trading Symbols                                        │
│ - Extract follow_symbol from maker parameters                  │
│ - Extract follow_symbol from self-trade parameters             │
│ - Remove duplicates                                            │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Select Subscription Function Based on Exchange Type            │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│ │ Binance    │  │ Binance    │  │ OKX        │  │ OKX         ││
│ │ Spot       │  │ Future     │  │ Spot       │  │ Future      ││
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Execute Market Data Subscription                               │
│ - Establish WebSocket connection                               │
│ - Subscribe to market data for trading symbols                 │
│ - Store market data to Redis                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Process Description

### 1. Start Quote Module

Start the quote module via command line, specifying exchange type and parameter files:

```bash
# Subscribe to Binance spot market data
python tunapy/quote/market_main.py binance_spot --maker_json docs/mm_params.json --st_json docs/st_params_bn.json

# Subscribe to Binance futures market data
python tunapy/quote/market_main.py binance_future --maker_json docs/mm_params.json --st_json docs/st_params_bn.json

# Subscribe to OKX spot market data
python tunapy/quote/market_main.py okx_spot --maker_json docs/mm_params.json --st_json docs/st_params_bn.json

# Subscribe to OKX futures market data
python tunapy/quote/market_main.py okx_future --maker_json docs/mm_params.json --st_json docs/st_params_bn.json
```

### 2. Parse Command Line Arguments

Use `argparse` library to parse command line arguments:

| Parameter | Description | Example Value |
|-----------|-------------|---------------|
| exchange | Exchange type | binance_spot, binance_future, okx_spot, okx_future |
| --maker_json | Path to maker parameters JSON file | docs/mm_params.json |
| --st_json | Path to self-trade parameters JSON file | docs/st_params_bn.json |

### 3. Load Parameter Configuration

- **Load maker parameters**: Load maker parameters from the file specified by `--maker_json`
- **Load self-trade parameters**: Load self-trade parameters from the file specified by `--st_json`
- **Error handling**: If file loading fails, print error message but continue execution

### 4. Extract Trading Symbols

- Extract `follow_symbol` from maker parameters
- Extract `follow_symbol` from self-trade parameters
- Remove duplicates to ensure each symbol is subscribed only once

### 5. Select Subscription Function

Select the corresponding subscription function based on exchange type:

| Exchange Type | Subscription Function |
|---------------|-----------------------|
| binance_spot | bn_subscribe() |
| binance_future | bn_future_subscribe() |
| okx_spot | okx_subscribe() |
| okx_future | okx_future_subscribe() |

### 6. Execute Market Data Subscription

- **Establish WebSocket connection**: Connect to the exchange's WebSocket server
- **Subscribe to market data**: Subscribe to real-time market data for specified symbols
- **Data processing**: Receive and process market data
- **Store to Redis**: Store processed market data to Redis for use by other modules

## Core Function Description

### main() Function

```python
def main(exchange, maker_params: list[MakerParameter], selftrade_params: list[SelftradeParameter]):
    """ main workflow of market data """
    # Extract symbols and remove duplicates
    maker_symbols = list(set([param.follow_symbol for param in maker_params]))
    selftrade_symbols = list(set([param.follow_symbol for param in selftrade_params]))
    
    # Select subscription function based on exchange type
    if exchange == EXCHANGE_BN:
        bn_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_BN_FUTURE:
        bn_future_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_OKX:
        okx_subscribe(maker_symbols, selftrade_symbols)
    elif exchange == EXCHANGE_OKX_FUTURE:
        okx_future_subscribe(maker_symbols, selftrade_symbols)
    else:
        return
```

### Subscription Functions

Each exchange's subscription function is responsible for:
1. Establishing WebSocket connection
2. Subscribing to market data for specified symbols
3. Processing received market data
4. Storing data to Redis

## Data Flow

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Exchange  │────>│ WebSocket │────>│ Data      │────>│ Redis    │
│ WebSocket│     │ Client    │     │ Processing│     │ Storage  │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
                                                                 │
                                                                 │
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Maker     │<────│ Other     │<────│ Data      │<────│ Redis    │
│ Module    │     │ Modules   │     │ Reading   │     │ Storage  │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
```

## Configuration File Examples

### Maker Parameters File (mm_params.json)

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

### Self-Trade Parameters File (st_params_bn.json)

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

## Notes

1. **WebSocket Connection**: Ensure stable network connection, WebSocket connections may disconnect due to network issues
2. **Redis Service**: Ensure Redis service is running properly, quote module depends on Redis for data storage
3. **Parameter Configuration**: Configure trading symbols and exchange types correctly to avoid subscribing to non-existent symbols
4. **API Limits**: Be aware of each exchange's API limits to avoid being restricted due to excessive subscriptions
5. **Log Monitoring**: Regularly check log files to discover and resolve issues in a timely manner

## Common Issues

### 1. Cannot Connect to Exchange WebSocket
- Check network connection
- Verify exchange WebSocket address is correct
- Check firewall settings

### 2. No Market Data in Redis
- Check if Redis service is running
- Check if quote module started successfully
- View quote module logs to confirm if there are any error messages

### 3. Wrong Subscription Function Selected
- Ensure exchange parameter matches actual symbol type
- Use binance_spot for Binance spot
- Use binance_future for Binance futures
- Use okx_spot for OKX spot
- Use okx_future for OKX futures

# Hedger Module Flowchart

## Overall Flow Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Start Hedger Module                                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Parse Command Line Arguments                                   │
│ - Read config file path                                         │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Load Config File                                               │
│ - Parse JSON config to TokenParameter object                   │
│ - Create BiFuPrivateWSClient instance                          │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Initialize HedgerAgent                                         │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. Initialize API keys and config                          ││
│ │ 2. Create loggers                                          ││
│ │ 3. Initialize data structures                              ││
│ │ 4. Start WebSocket client                                  ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Run Main Loop (run_forever method)                            │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. Check config updates                                    ││
│ │ 2. Handle risk positions (_handle_risk_positions method)   ││
│ │ 3. Check hedge task status                                 ││
│ │ 4. Periodically clean trade IDs                            ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Handle Risk Positions (_handle_risk_positions method)          │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. Aggregate risk positions                                ││
│ │ 2. Calculate hedge quantity and amount                     ││
│ │ 3. Execute hedge operation                                 ││
│ │ 4. Update risk position status                             ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Handle Trade Events (handle_trade_filled method)               │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. Deduplicate trade IDs                                   ││
│ │ 2. Parse trade data                                        ││
│ │ 3. Update risk positions                                   ││
│ │ 4. Record trade information                                ││
│ └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Flow Explanation

### 1. Start Hedger Module

Start the Hedger module via command line, specifying the config file path:

```bash
# Command line format
python tunapy/hedger/hedger_main.py <config_file>

# Example
python tunapy/hedger/hedger_main.py tests/test_hedger_params.json
```

### 2. Parse Command Line Arguments

The program parses command line arguments to get the config file path:

```python
if len(sys.argv) != 2:
    print("Usage: python hedger_main.py <config_file>")
    sys.exit(1)

config_file = sys.argv[1]
```

### 3. Load Config File

The program loads and parses the JSON config file, creating TokenParameter and BiFuPrivateWSClient instances:

```python
try:
    with open(config_file, 'r') as f:
        config = json.load(f)
        param = TokenParameter(config['token_parameter'])
        # Monitor BiFu trade executions
        logger = create_logger(BASE_PATH, "hedger.log", 'JPM_MM')
        ws_client = BiFuPrivateWSClient(config['private_ws_client'], logger)
except Exception as e:
    print(f"Error: failed to load config file {config_file}: {e}")
    sys.exit(1)
```

### 4. Initialize HedgerAgent

Create and initialize the HedgerAgent instance:

1. **Initialize API keys and config**: Set hedge API keys, loggers, and config
2. **Create data structures**: Initialize risk position dictionary, thread pool, and task management
3. **Initialize hedge client**: Create normalized hedge client using get_private_client
4. **Start WebSocket client**: Connect to exchange execution report stream

### 5. Run Main Loop

HedgerAgent runs the main loop to handle risk positions and hedge tasks:

1. **Check config updates**: Periodically check if config has been updated
2. **Handle risk positions**: Call `_handle_risk_positions` method to process unhedged positions
3. **Check hedge task status**: Call `wait_for_hedge_multithread` method to check execution status of hedge tasks
4. **Periodically clean trade IDs**: Clean trade IDs from 2 hours ago to reduce memory usage

### 6. Handle Risk Positions

The `_handle_risk_positions` method processes risk positions:

1. **Aggregate risk positions**: Aggregate risk positions by trading pair
2. **Calculate hedge quantity and amount**: Calculate required hedge quantity and amount based on risk positions
3. **Generate client order ID**: Generate consistent client_order_id based on unique identifiers of risk positions (order ID, trading pair, direction)
4. **Execute hedge operation**: Create NewOrder object and execute hedge using batch_make_orders method via thread pool
5. **Update risk position status**: Mark positions as hedged

### 7. Handle Trade Events

When WebSocket receives trade execution events, the `handle_trade_filled` method is called:

1. **Deduplicate trade IDs**: Avoid processing the same trade multiple times
2. **Parse trade data**: Extract trade price, quantity, direction, etc.
3. **Update risk positions**: Add trade to risk position dictionary
4. **Record trade information**: Log trade details

## Data Flow

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Exchange  │────>│ WebSocket │────>│ Hedger   │────>│ Exchange  │
│ Execution │     │ Client    │     │ Agent    │     │ Hedge     │
│ Report    │     │           │     │          │     │ Trade     │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
                                                                 │
                                                                 │
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Log       │<────│ Hedger   │<────│ Config   │<────│ Command   │
│ Records   │     │ Agent    │     │ File     │     │ Line      │
│           │     │          │     │          │     │ Parameters│
└───────────┘     └───────────┘     └───────────┘     └───────────┘
```

## Config File Example

```json
{
    "token_parameter" :{
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
    "private_ws_client" :{
        "API KEY": "",
        "Secret": "",
        "Passphrase": "",
        "Stream URL": ""
    }
}
```

## Main Parameter Description

| Parameter | Description | Type |
|-----------|-------------|------|
| Maker Exchange | Maker exchange | String |
| API KEY | API key | String |
| Secret | API secret | String |
| Passphrase | Passphrase (required for OKX) | String |
| Stream URL | WebSocket stream URL | String |
| Maker Symbol | Maker trading pair | String |
| Hedge Symbol | Hedge trading pair | String |
| Hedge Exchange | Hedge exchange | String |
| Hedger Price Decimals | Hedge price decimals | Integer |
| Hedger Qty Decimals | Hedge quantity decimals | Integer |
| Min Qty | Minimum order quantity | Float |
| Min Amt | Minimum order amount | Float |
| Slippage | Slippage setting | Float |

## Hedge Logic Explanation

### 1. Risk Position Calculation

1. **Single trade**: Each executed trade is added to the risk position dictionary
2. **Position aggregation**: Aggregate risk positions by trading pair, calculate net position
3. **Hedge threshold**: Execute hedge when risk position exceeds minimum order threshold

### 2. Hedge Execution

1. **Hedge direction**: Determine hedge direction based on risk position direction (long → sell, short → buy)
2. **Hedge price**: Determine hedge price based on average price of risk position
3. **Hedge quantity**: Determine hedge quantity based on risk position quantity
4. **Create NewOrder object**: Build NewOrder named tuple with all necessary fields
5. **Use batch_make_orders**: Call normalized client's batch_make_orders method to execute hedge
6. **Thread pool execution**: Asynchronously execute hedge operation via thread pool
7. **Handle response**: Extract order ID from returned OrderID object

### 3. Task Management

1. **Task tracking**: Track all executing hedge tasks
2. **Status checking**: Periodically check execution status of hedge tasks
3. **Result processing**: Process execution results of hedge tasks, update logs

### 4. Normalized Client

1. **get_private_client**: Use this function to create normalized hedge client
2. **Unified interface**: All exchange clients implement batch_make_orders unified interface
3. **Cross-exchange compatibility**: Achieve cross-exchange hedging through NewOrder named tuple and unified interface
4. **Simplified maintenance**: Unified interface reduces code complexity, facilitates future maintenance

### 5. WebSocket Client

1. **UserWebsocketStreamClient**: Implements WebSocket connection management and message processing
2. **Automatic reconnection**: Automatically tries to reconnect when connection fails
3. **Asynchronous processing**: Runs WebSocket in a separate thread to avoid blocking main thread
4. **Message parsing**: Automatically parses JSON format messages and passes to callback functions
5. **Error handling**: Comprehensive exception catching and error logging

## Notes

1. **WebSocket dependency**: Ensure WebSocket connection is stable, as the hedge module relies on it to get execution events
2. **API key security**: Properly secure API keys, avoid storing them in plaintext in config files
3. **Parameter tuning**: Adjust minimum order threshold and slippage settings based on market conditions
4. **Risk control**: Set reasonable hedge parameters to avoid over-hedging
5. **Network stability**: Ensure network connection is stable to avoid hedge execution exceptions due to network issues
6. **Exchange limits**: Understand and comply with API call limits and rules of each exchange

## Common Issues

### 1. WebSocket connection failure
- Check if Stream URL is correct
- Confirm API key and signature are correct
- Check network connection stability

### 2. Hedge execution failure
- Check if hedge trading pair exists
- Confirm account balance is sufficient
- Verify API permissions include trading permission

### 3. Risk position calculation error
- Check if trade data parsing is correct
- Confirm risk position aggregation logic is correct
- Verify hedge threshold settings are reasonable

### 4. High memory usage
- Check if trade ID cleaning logic is working properly
- Confirm risk position dictionary is correctly cleaning hedged positions
- Consider increasing cleaning frequency

### 5. Config update not taking effect
- Check if config update logic is correct
- Confirm config file format is correct
- Verify config version number is incrementing

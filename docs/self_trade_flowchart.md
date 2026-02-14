# Self-Trader Module Flowchart

## Overall Process Overview

```
┌─────────────────────────────────────────────────────────────────┐
│ Start Self-Trader Module                                       │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Parse Command Line Arguments                                   │
│ - Read configuration file path                                  │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Load Configuration File                                         │
│ - Parse JSON configuration to SelftradeParameter objects        │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Start Main Loop (main function)                                 │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. Check update frequency                                   ││
│ │ 2. Initialize trading pair context                          ││
│ │ 3. Create self-trading tasks                                 ││
│ │ 4. Execute self-trading tasks in parallel                    ││
│ │ 5. Sleep when idle                                           ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Execute Self-Trading (self_trade function)                     │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. Get trading data of followed pair from Redis             ││
│ │ 2. Get order book of maker trading pair                     ││
│ │ 3. Calculate trading price and quantity                     ││
│ │ 4. Adjust trading price and quantity                        ││
│ │ 5. Execute trade (_trade function)                          ││
│ │ 6. Cancel maker orders (_cancel_orders function)            ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Execute Trade (_trade function)                                │
│ - Randomly select trade direction                              │
│ - Create trading orders                                        │
│ - Place batch orders                                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ Cancel Maker Orders (_cancel_orders function)                  │
│ - Attempt to cancel orders                                     │
│ - Retry up to 3 times                                          │
└─────────────────────────────────────────────────────────────────┘
```

## Detailed Process Description

### 1. Start Self-Trader Module

Start the Self-Trader module via command line, specifying the configuration file path:

### 2. Parse Command Line Arguments

### 3. Load Configuration File

### 4. Main Loop (main function)

### 5. Execute Self-Trading (self_trade function)

### 6. Execute Trade (_trade function)

### 7. Cancel Maker Orders (_cancel_orders function)

## Data Flow

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Exchange  │────>│ Redis     │────>│ Self-    │────>│ Exchange  │
│ Market Data│     │ Storage   │     │ Trader   │     │ Trading   │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
                                                                 │
                                                                 │
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ Log       │<────│ Self-    │<────│ Exchange  │<────│ Order     │
│ Recording │     │ Trader   │     │ Order Book│     │ Response  │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
```

## Configuration File Example

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

## Main Parameter Description

| Parameter | Description | Type |
|-----------|-------------|------|
| Maker Exchange | Maker exchange | String |
| API KEY | API key | String |
| Secret | API secret | String |
| Passphrase | Passphrase (required for OKX) | String |
| Follow Exchange | Follow exchange for market data | String |
| Follow Symbol | Follow trading pair | String |
| Maker Symbol | Maker trading pair | String |
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

## Trading Logic Explanation

### 1. Price Calculation Logic

1. **Base Price**: Use the latest trading price of the followed pair
2. **Price Adjustment**:
   - If consecutive prices are the same, slightly adjust price
   - If price deviation is too large, limit price change range
   - Ensure price is within valid order book range (not exceeding highest bid, not lower than lowest ask)

### 2. Quantity Calculation Logic

1. **Base Quantity**: Follow pair trading quantity × quantity multiplier
2. **Random Adjustment**: Apply random coefficient (0.9995-1.0005)
3. **Range Limit**:
   - Not less than minimum order quantity
   - Not greater than maximum amount/price
   - If consecutive quantities are the same, slightly adjust quantity

### 3. Trade Execution Logic

1. **Order Types**:
   - Maker order: LIMIT type, GTX (maker only)
   - Taker order: LIMIT type, IOC (immediate or cancel)
2. **Trade Direction**: Randomly select BUY or SELL
3. **Order Cancellation**: Cancel maker order after successful trade

## Notes

1. **Redis Dependency**: Ensure Redis service is running properly, self-trading module depends on Redis for market data
2. **API Key Security**: Safely store API keys, avoid plaintext storage in configuration files
3. **Parameter Tuning**: Adjust parameters based on market conditions, especially quantity multiplier and price divergence threshold
4. **Risk Control**: Set reasonable maximum order amount to avoid excessive risk
5. **Network Stability**: Ensure stable network connection to avoid trading execution exceptions due to network issues
6. **Exchange Limitations**: Understand and comply with API call limits and rules of each exchange

## Common Issues

### 1. Failed to Get Market Data
- Check if Redis service is running
- Confirm that followed pair market data is properly stored in Redis
- Verify Follow Exchange and Follow Symbol parameters are correct

### 2. Failed to Get Order Book Data
- Check if exchange API connection is normal
- Confirm Maker Symbol parameter is correct
- Verify API permissions are sufficient

### 3. Trade Execution Failed
- Check if API key and signature are correct
- Confirm if trading pair supports current trading type
- Check if account balance is sufficient

### 4. Price or Quantity Abnormal
- Adjust Price Divergence parameter to control price change range
- Adjust Qty Multiplier parameter to control order size
- Check if followed pair trading data is abnormal

### 5. Failed to Cancel Orders
- Check if order ID is correct
- Confirm if order still exists
- Verify API permissions include order cancellation
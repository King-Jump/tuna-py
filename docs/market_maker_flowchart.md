# market_maker.py Flow Diagram

## Overall Process Overview

```
┌──────────────────────────────────────────────────────────────────┐
│ Startup Process                                                  │
├──────────────────────────────────────────────────────────────────┤
│ 1. Load configuration file (tests/test_mm_params_bn.json)        │
│ 2. Parse configuration into TokenParameter object list           │
│ 3. Call asyncio.run(main(params))                                │
└───────────────┬──────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ main() Function                                                  │
├──────────────────────────────────────────────────────────────────┤
│ 1. Create logger                                                 │
│ 2. Initialize context:                                           │
│    - _last_operating_ts: Record timestamp for each trading pair  │
│    - _prev_context: Store context info for each trading pair     │
│ 3. Enter infinite loop:                                          │
│    a. Check update frequency for each trading pair               │
│    b. Create market making tasks for eligible pairs              │
│    c. Execute all tasks in parallel (asyncio.gather)             │
│    d. Error handling and logging                                 │
└───────────────┬──────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ market_making() Function                                         │
├──────────────────────────────────────────────────────────────────┤
│ 1. Get order book data from Redis (DATA_REDIS_CLIENT.get_order_book) │
│ 2. Validate order book data                                      │
│ 3. Generate near-end orders:                                     │
│    a. gen_ask_orders(): Generate sell orders                     │
│    b. gen_bid_orders(): Generate buy orders                      │
│ 4. Generate client order IDs                                     │
│ 5. Filter valid orders (avoid self-trading)                      │
│ 6. Call handle_orders() to process near-end orders               │
│ 7. If needed, generate and process far-end orders:               │
│    a. gen_far_liquidity(): Generate far-end liquidity orders     │
│    b. Call handle_orders() to process far-end orders             │
│ 8. Exception handling: Cancel all near-end open orders           │
└───────────────┬──────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────────────┐
│ handle_orders() Function                                         │
├──────────────────────────────────────────────────────────────────┤
│ 1. Scan top bid/ask prices of new orders                         │
│ 2. Get previous orders and refresh count                         │
│ 3. Calculate price difference rate and force refresh threshold   │
│ 4. Determine order processing strategy:                          │
│    a. Force refresh: Cancel all previous orders, use all new orders │
│    b. Regular update: Only replace orders with large price differences │
│ 5. Mix buy/sell orders (mix_ask_bid_orders)                      │
│ 6. Batch place orders (_make_orders)                             │
│ 7. Update context (store new order information)                  │
│ 8. Batch cancel orders to be canceled (_cancel_orders)           │
│ 9. Update top ask/bid price information                          │
│ 10. Handle far-end order exceptions (rollback mechanism)         │
└──────────────────────────────────────────────────────────────────┘
```

## Detailed Process Description

### 1. Startup and Initialization

| Step | Description | Key Code |
|------|-------------|----------|
| 1.1 | Load configuration file | `json.load(f)` to read JSON config |
| 1.2 | Create TokenParameter objects | `TokenParameter(item)` to parse config |
| 1.3 | Initialize main function | `asyncio.run(main(params))` |

### 2. Main Loop (main function)

| Step | Description | Key Code |
|------|-------------|----------|
| 2.1 | Check update frequency | `op_ts['near_opts'] + param.near_interval > ts` |
| 2.2 | Check if far-end orders need update | `op_ts['far_opts'] + param.far_interval <= ts` |
| 2.3 | Initialize trading pair context | Create private client, set mock mode |
| 2.4 | Create market making tasks | `asyncio.create_task(market_making(...))` |
| 2.5 | Execute all tasks | `await asyncio.gather(*tasks)` |

### 3. Market Making Core (market_making function)

| Step | Description | Key Code |
|------|-------------|----------|
| 3.1 | Get order book data | `DATA_REDIS_CLIENT.get_order_book(symbol_key)` |
| 3.2 | Generate near-end orders | `gen_ask_orders()`, `gen_bid_orders()` |
| 3.3 | Filter valid orders | `price > top_bid` (sell orders), `price < top_ask` (buy orders) |
| 3.4 | Process near-end orders | `await handle_orders(..., is_far=False)` |
| 3.5 | Generate far-end orders | `gen_far_liquidity()` |
| 3.6 | Process far-end orders | `await handle_orders(..., is_far=True)` |

### 4. Order Processing (handle_orders function)

| Step | Description | Key Code |
|------|-------------|----------|
| 4.1 | Determine refresh strategy | `diff_rate_per_round <= 0 or no_force_refresh_num >= force_refresh_num` |
| 4.2 | Force refresh mode | Cancel all previous orders, use all new orders |
| 4.3 | Regular update mode | `diff_prev_new_orders()` to calculate differences |
| 4.4 | Mix orders | `mix_ask_bid_orders()` to mix buy/sell orders |
| 4.5 | Batch place orders | `await _make_orders()` |
| 4.6 | Update context | Store new order info in `ctx` |
| 4.7 | Batch cancel orders | `await _cancel_orders()` |
| 4.8 | Handle far-end order exceptions | Rollback unexpected orders |

### 5. Helper Functions

| Function Name | Description | Key Operations |
|---------------|-------------|----------------|
| _make_orders | Batch place orders | `client.batch_make_orders()` |
| _cancel_orders | Batch cancel orders | `client.batch_cancel()` |
| _open_orders | Get open orders | `client.open_orders()` |
| _clear_all_open_orders | Cancel all open orders | Get all order IDs then batch cancel |
| _clear_all_ner_open_orders | Cancel all near-end open orders | Only cancel non-far-end orders |

## Key Data Structures

1. **TokenParameter**: Stores all market making configuration parameters
2. **CachedOrder**: Named tuple for storing order price and ID
3. **NewOrder**: Data structure for new orders (from octopuspy)
4. **Context dictionary (ctx)**: Stores state information for each trading pair
   - `client`: Private client instance
   - `prev_asks`/`prev_bids`: Previous near-end orders
   - `prev_farasks`/`prev_farbids`: Previous far-end orders
   - `no_force_refresh_num`: Number of rounds without forced refresh
   - `top_ask`/`top_bid`: Current best ask and bid prices

## Exception Handling Mechanism

1. **main function**: Catch and log all exceptions
2. **market_making function**: Catch exceptions, log errors, and cancel all near-end open orders
3. **handle_orders function**: Handle far-end order exceptions with rollback mechanism

## Time Control Mechanism

1. **Near-end order update frequency**: `param.near_interval`
2. **Far-end order update frequency**: `param.far_interval`
3. **Force refresh threshold**: `param.force_refresh_num`
4. **Price difference rate**: `param.near_diff_rate_per_round` (used to determine order replacement)

This flow diagram illustrates the complete workflow of market_maker.py, from startup to order processing, helping to understand the market making strategy implementation.
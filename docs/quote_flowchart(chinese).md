# 行情模块流程图

## 整体流程概览

```
┌─────────────────────────────────────────────────────────────────┐
│ 启动行情模块                                                   │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 解析命令行参数                                                 │
│ - exchange: 交易所类型                                         │
│ - --maker_json: 做市参数文件路径                              │
│ - --st_json: 自成交参数文件路径                                │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 加载参数配置文件                                               │
│ - 加载做市参数 (maker_params)                                  │
│ - 加载自成交参数 (selftrade_params)                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 提取交易对符号                                                 │
│ - 从做市参数中提取 follow_symbol                               │
│ - 从自成交参数中提取 follow_symbol                             │
│ - 去重处理                                                     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 根据交易所类型选择订阅函数                                     │
│ ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐│
│ │ Binance    │  │ Binance    │  │ OKX        │  │ OKX         ││
│ │ 现货        │  │ 期货        │  │ 现货        │  │ 期货        ││
│ └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 执行行情订阅                                                   │
│ - 建立 WebSocket 连接                                          │
│ - 订阅交易对的行情数据                                         │
│ - 将行情数据存储到 Redis                                       │
└─────────────────────────────────────────────────────────────────┘
```

## 详细流程说明

### 1. 启动行情模块

通过命令行启动行情模块，指定交易所类型和参数文件：

```bash
# 订阅 Binance 现货行情
python tunapy/quote/market_main.py binance_spot --maker_json docs/mm_params.json --st_json docs/st_params_bn.json

# 订阅 Binance 期货行情
python tunapy/quote/market_main.py binance_future --maker_json docs/mm_params.json --st_json docs/st_params_bn.json

# 订阅 OKX 现货行情
python tunapy/quote/market_main.py okx_spot --maker_json docs/mm_params.json --st_json docs/st_params_bn.json

# 订阅 OKX 期货行情
python tunapy/quote/market_main.py okx_future --maker_json docs/mm_params.json --st_json docs/st_params_bn.json
```

### 2. 解析命令行参数

使用 `argparse` 库解析命令行参数：

| 参数 | 说明 | 示例值 |
|------|------|--------|
| exchange | 交易所类型 | binance_spot, binance_future, okx_spot, okx_future |
| --maker_json | 做市参数 JSON 文件路径 | docs/mm_params.json |
| --st_json | 自成交参数 JSON 文件路径 | docs/st_params_bn.json |

### 3. 加载参数配置

- **加载做市参数**：从 `--maker_json` 指定的文件中加载做市参数
- **加载自成交参数**：从 `--st_json` 指定的文件中加载自成交参数
- **异常处理**：如果文件加载失败，会打印错误信息但继续执行

### 4. 提取交易对符号

- 从做市参数中提取 `follow_symbol`
- 从自成交参数中提取 `follow_symbol`
- 去重处理，确保每个交易对只订阅一次

### 5. 选择订阅函数

根据交易所类型选择相应的订阅函数：

| 交易所类型 | 订阅函数 |
|------------|----------|
| binance_spot | bn_subscribe() |
| binance_future | bn_future_subscribe() |
| okx_spot | okx_subscribe() |
| okx_future | okx_future_subscribe() |

### 6. 执行行情订阅

- **建立 WebSocket 连接**：与交易所的 WebSocket 服务器建立连接
- **订阅行情数据**：订阅指定交易对的实时行情
- **数据处理**：接收行情数据并进行处理
- **存储到 Redis**：将处理后的行情数据存储到 Redis 中，供其他模块使用

## 核心函数说明

### main() 函数

```python
def main(exchange, maker_params: list[MakerParameter], selftrade_params: list[SelftradeParameter]):
    """ main workflow of market data """
    # 提取交易对并去重
    maker_symbols = list(set([param.follow_symbol for param in maker_params]))
    selftrade_symbols = list(set([param.follow_symbol for param in selftrade_params]))
    
    # 根据交易所类型选择订阅函数
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

### 订阅函数

各交易所的订阅函数负责：
1. 建立 WebSocket 连接
2. 订阅指定交易对的行情
3. 处理收到的行情数据
4. 将数据存储到 Redis

## 数据流向

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ 交易所    │────>│ WebSocket │────>│ 数据处理  │────>│ Redis    │
│ WebSocket│     │ 客户端     │     │ 模块      │     │ 存储      │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
                                                                 │
                                                                 │
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ 做市模块  │<────│ 其他模块  │<────│ 数据读取  │<────│ Redis    │
│ Market   │     │           │     │ 模块      │     │ 存储      │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
```

## 配置文件示例

### 做市参数文件 (mm_params.json)

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

### 自成交参数文件 (st_params_bn.json)

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

## 注意事项

1. **WebSocket 连接**：确保网络连接稳定，WebSocket 连接可能会因网络问题断开
2. **Redis 服务**：确保 Redis 服务正常运行，行情模块依赖 Redis 存储数据
3. **参数配置**：正确配置交易对符号和交易所类型，避免订阅不存在的交易对
4. **API 限制**：注意各交易所的 API 调用限制，避免过度订阅导致被限制
5. **日志监控**：定期查看日志文件，及时发现和解决问题

## 常见问题

### 1. 无法连接到交易所 WebSocket
- 检查网络连接
- 确认交易所 WebSocket 地址是否正确
- 检查防火墙设置

### 2. Redis 中没有行情数据
- 检查 Redis 服务是否运行
- 检查行情模块是否正常启动
- 查看行情模块日志，确认是否有错误信息

### 3. 订阅函数选择错误
- 确保 exchange 参数与实际交易对类型匹配
- Binance 现货使用 binance_spot
- Binance 期货使用 binance_future
- OKX 现货使用 okx_spot
- OKX 期货使用 okx_future

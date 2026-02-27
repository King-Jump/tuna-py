# tuna-py

## 项目介绍

tuna-py 是一个专业的加密货币做市交易系统，主要用于在加密货币交易所提供流动性和执行自成交测试。系统包含三个核心模块：行情订阅模块、自成交模块和做市模块，支持多个主流交易所的现货和合约市场。

### 主要功能

- **行情订阅**：实时从 Binance、OKX 等交易所订阅行情数据，存储到 Redis
- **自成交测试**：模拟交易行为，测试市场流动性和交易执行
- **智能做市**：基于实时行情数据，自动生成买卖订单，提供市场流动性
- **多交易所支持**：支持 Binance 和 OKX 的现货和合约市场
- **参数化配置**：通过 JSON 配置文件灵活调整策略参数

## 目录结构

```
tuna-py/
├── tunapy/
│   ├── quote/             # 行情订阅模块
│   │   ├── market_main.py     # 行情模块主入口
│   │   ├── bn_public_ws.py    # Binance 现货行情订阅
│   │   ├── bn_future_public_ws.py # Binance 合约行情订阅
│   │   ├── okx_public_ws.py   # OKX 现货行情订阅
│   │   └── okx_future_public_ws.py # OKX 合约行情订阅
│   ├── self_trader/       # 自成交模块
│   │   └── self_trader.py     # 自成交模块主入口
│   ├── maker/             # 做市模块
│   │   ├── market_maker.py    # 做市模块主入口
│   │   └── maker_libs.py      # 做市工具函数
│   ├── management/        # 管理模块
│   │   ├── market_making.py   # 做市参数定义
│   │   ├── self_trade.py      # 自成交参数定义
│   │   ├── redis_client.py    # Redis 客户端
│   │   └── hedging.py         # 对冲参数定义
│   ├── cexapi/            # 交易所 API
│   │   └── helper.py          # API 客户端辅助函数
│   ├── hedger/            # 对冲模块
│   │   └── hedger_main.py     # 对冲模块主入口
│   └── utils/             # 工具函数
│       ├── config_util.py     # 配置工具
│       └── db_util.py         # 数据库工具
├── docs/                  # 文档
│   ├── mm_params.json         # 做市参数示例
│   ├── st_params_bn.json      # 自成交参数示例
│   └── README.md              # 文档说明
├── examples/              # 示例
├── tests/                 # 测试
├── log/                   # 日志目录
├── requirements.txt       # 依赖包
├── LICENSE                # 许可证
└── README.md              # 项目说明
```

## 相关项目
### octopus-py
这个项目包含了多个交易所客户端，也可以基于 octopus-py 开发自己的交易所客户端在 tuna-py 中引用。
```
https://github.com/King-Jump/octopus-py
```
## 软件运行过程

### 3.1 行情模块

#### 3.1.1 启动命令行

```bash
# 命令行格式:
python tunapy/quote/market_main.py <exchange> --maker_json=<market maker params> --st_json=<self trade params>

# 例:
# 订阅 Binance 现货行情
python tunapy/quote/market_main.py binance_spot --maker_json=docs/mm_params.json --st_json=docs/st_params_bn.json

# 订阅 Binance 合约行情
python tunapy/quote/market_main.py binance_future --maker_json=docs/mm_params.json --st_json=docs/st_params_bn.json

# 订阅 OKX 现货行情
python tunapy/quote/market_main.py okx_spot --maker_json=docs/mm_params.json --st_json=docs/st_params_bn.json

# 订阅 OKX 合约行情
python tunapy/quote/market_main.py okx_future --maker_json=docs/mm_params.json --st_json=docs/st_params_bn.json
```
#### 3.1.2 行情模块参数说明

行情模块通过命令行参数指定：

| 参数 | 说明 | 示例值 |
|------|------|--------|
| exchange | 交易所类型 | binance_spot, binance_future, okx_spot, okx_future |
| --maker_json | 做市参数 JSON 文件路径 | docs/mm_params.json |
| --st_json | 自成交参数 JSON 文件路径 | docs/st_params_bn.json |

#### 3.1.3 交易所类型

```
- binance_spot: Binance 现货行情
- binance_future: Binance 合约行情
- okx_spot: OKX 现货行情
- okx_future: OKX 合约行情
```

### 3.2 SelfTrade 模块

#### 3.2.1 启动命令

```bash
# 命令行格式:
python tunapy/self_trader/self_trader.py <self trade params>

# 例:
python tunapy/self_trader/self_trader.py docs/st_params_bn.json
```

#### 3.2.2 SelfTrade 模块参数说明

自成交模块通过 JSON 配置文件指定参数，示例配置：

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

#### 主要参数说明：

| 参数 | 说明 | 类型 |
|------|------|------|
| Maker Exchange | 做市交易所 | 字符串 |
| API KEY | API 密钥 | 字符串 |
| Secret | API 密钥密码 | 字符串 |
| Passphrase | 密码短语（OKX 需要） | 字符串 |
| Follow Exchange | 行情跟随交易所 | 字符串 |
| Follow Symbol | 跟随的交易对 | 字符串 |
| Maker Symbol | 做市的交易对 | 字符串 |
| Term type | 交易类型（SPOT/FUTURE） | 字符串 |
| Price Decimals | 价格小数位数 | 整数 |
| Qty Decimals | 数量小数位数 | 整数 |
| Position Side | 持仓方向（LONG/SHORT） | 字符串 |
| Interval | 交易间隔（秒） | 浮点数 |
| Qty Multiplier | 数量乘数 | 浮点数 |
| Price Divergence | 价格偏离阈值 | 浮点数 |
| Max Amt Per Order | 每笔订单最大金额 | 浮点数 |
| Min Qty | 最小订单数量 | 浮点数 |
| Min Amt | 最小订单金额 | 浮点数 |

### 3.3 MarketMaking 做市模块

#### 3.3.1 启动命令行

```bash
# 命令行格式:
python tunapy/maker/market_maker.py <market maker params>

# 例:
python tunapy/maker/market_maker.py docs/mm_params.json
```

#### 3.3.2 MarketMaking 模块参数说明

做市模块通过 JSON 配置文件指定参数，示例配置：

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

#### 主要参数说明：

| 参数 | 说明 | 类型 |
|------|------|------|
| Maker Exchange | 做市交易所 | 字符串 |
| API KEY | API 密钥 | 字符串 |
| Secret | API 密钥密码 | 字符串 |
| Passphrase | 密码短语（OKX 需要） | 字符串 |
| Follow Exchange | 行情跟随交易所 | 字符串 |
| Follow Symbol | 跟随的交易对 | 字符串 |
| Maker Symbol | 做市的交易对 | 字符串 |
| Term type | 交易类型（SPOT/FUTURE） | 字符串 |
| Maker Price Decimals | 价格小数位数 | 整数 |
| Maker Qty Decimals | 数量小数位数 | 整数 |
| Position Side | 持仓方向（LONG/SHORT） | 字符串 |

**远端订单参数**：

| 参数 | 说明 | 类型 |
|------|------|------|
| Far Interval | 远端订单更新间隔（秒） | 浮点数 |
| Far Quote Timeout | 远端行情超时时间（秒） | 浮点数 |
| Far Side | 远端订单方向（BUY/SELL/BOTH） | 字符串 |
| Far TIF | 远端订单有效期（GTX/GTC） | 字符串 |
| Far Strategy | 远端做市策略 | 字符串 |
| Far Buy Price Margin | 远端买单价格 margin | 整数 |
| Far Sell Price Margin | 远端卖单价格 margin | 整数 |
| Far Qty Multiplier | 远端订单数量乘数 | 浮点数 |
| Far Ask Size | 远端卖单层数 | 整数 |
| Far Bid Size | 远端买单层数 | 整数 |
| Far Max Amt Per Order | 远端每笔订单最大金额 | 浮点数 |
| Far Min Qty | 远端最小订单数量 | 浮点数 |
| Far Min Amt | 远端最小订单金额 | 浮点数 |
| Far Diff Per Round | 远端订单价格差异阈值 | 整数 |

**近端订单参数**：

| 参数 | 说明 | 类型 |
|------|------|------|
| Near Interval | 近端订单更新间隔（秒） | 浮点数 |
| Near Quote Timeout | 近端行情超时时间（秒） | 浮点数 |
| Near Side | 近端订单方向（BUY/SELL/BOTH） | 字符串 |
| Near TIF | 近端订单有效期（GTX/GTC） | 字符串 |
| Near Strategy | 近端做市策略 | 字符串 |
| Near Buy Price Margin | 近端买单价格 margin | 整数 |
| Near Sell Price Margin | 近端卖单价格 margin | 整数 |
| Near Qty Multiplier | 近端订单数量乘数 | 浮点数 |
| Near Ask Size | 近端卖单层数 | 整数 |
| Near Bid Size | 近端买单层数 | 整数 |
| Near Max Amt Per Order | 近端每笔订单最大金额 | 浮点数 |
| Near Min Qty | 近端最小订单数量 | 浮点数 |
| Near Min Amt | 近端最小订单金额 | 浮点数 |
| Near Diff Per Round | 近端订单价格差异阈值 | 整数 |
| Force Refresh Num | 强制刷新轮数 | 整数 |

## 安装与依赖

### 依赖说明

- redis: 用于存储行情数据和订单信息
- requests: 用于 API 请求
- python-binance: Binance API 客户端
- binance-connector: Binance 官方连接器
- binance-futures-connector: Binance 合约 API 客户端
- python-okx: OKX API 客户端
- ujson: 高性能 JSON 解析
- octopus-py: 交易接口实现（本地依赖）

### 安装依赖

```bash
pip install -r requirements.txt

```

## 运行流程

### 1. 启动行情模块

首先启动行情模块，订阅交易所行情数据：

```bash
python tunapy/quote/market_main.py binance_spot --maker_json docs/mm_params.json --st_json docs/st_params_bn.json
```

### 2. 启动自成交模块（可选）

如果需要测试流动性，可以启动自成交模块：

```bash
python tunapy/self_trader/self_trader.py docs/st_params_bn.json
```

### 3. 启动做市模块

最后启动做市模块，开始提供流动性：

```bash
python tunapy/maker/market_maker.py docs/mm_params.json
```

### 4. 启动对冲模块（可选）

如果需要进行对冲操作，可以启动对冲模块：

```bash
python tunapy/hedger/hedger_main.py <config_file>
```

## 日志

系统运行日志存储在 `log/` 目录下：

- `market_making.log`: 做市模块日志
- `selftrade.log`: 自成交模块日志
- `bn_pub_ws.log`: Binance 现货行情日志
- `bn_future_pub_ws.log`: Binance 合约行情日志
- `okx_pub_ws.log`: OKX 现货行情日志
- `okx_future_pub_ws.log`: OKX 合约行情日志

## 注意事项

1. **API 密钥安全**：请妥善保管 API 密钥，避免在配置文件中明文存储
2. **参数调优**：根据市场情况和交易对特性，调整做市参数以获得最佳效果
3. **风险控制**：设置合理的订单大小和价格范围，避免过大风险
4. **网络稳定性**：确保网络连接稳定，避免因网络问题导致订单执行异常
5. **Redis 服务**：确保 Redis 服务正常运行，行情模块和做市模块依赖 Redis 存储数据
6. **交易所限制**：了解并遵守各交易所的 API 调用限制和规则

## 许可证

## 5 模块说明

本项目采用 MIT 许可证，详见 LICENSE 文件。


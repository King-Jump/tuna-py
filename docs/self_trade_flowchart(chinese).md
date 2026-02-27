# Self-Trader 模块流程图

## 整体流程概览

```
┌─────────────────────────────────────────────────────────────────┐
│ 启动 Self-Trader 模块                                           │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 解析命令行参数                                                 │
│ - 读取配置文件路径                                             │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 加载配置文件                                                   │
│ - 解析 JSON 配置为 SelftradeParameter 对象                      │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 启动主循环 (main 函数)                                          │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. 检查更新频率                                             ││
│ │ 2. 初始化交易对上下文                                        ││
│ │ 3. 创建自成交任务                                           ││
│ │ 4. 并行执行自成交任务                                       ││
│ │ 5. 空闲时休眠                                               ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 执行自成交 (self_trade 函数)                                    │
│ ┌─────────────────────────────────────────────────────────────┐│
│ │ 1. 从 Redis 获取跟随交易对的成交数据                         ││
│ │ 2. 获取做市交易对的订单簿                                   ││
│ │ 3. 计算交易价格和数量                                         ││
│ │ 4. 调整交易价格和数量                                         ││
│ │ 5. 执行交易 (_trade 函数)                                     ││
│ │ 6. 取消做市订单 (_cancel_orders 函数)                         ││
│ └─────────────────────────────────────────────────────────────┘│
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 执行交易 (_trade 函数)                                          │
│ - 随机选择交易方向                                             │
│ - 创建交易订单                                                 │
│ - 批量下单                                                     │
└───────────────────────┬─────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│ 取消做市订单 (_cancel_orders 函数)                               │
│ - 尝试取消订单                                                 │
│ - 最多重试 3 次                                                │
└─────────────────────────────────────────────────────────────────┘
```

## 详细流程说明

### 1. 启动 Self-Trader 模块

通过命令行启动 Self-Trader 模块，指定配置文件路径：

```bash
# 命令行格式
python tunapy/self_trader/self_trader.py <config_file>

# 示例
python tunapy/self_trader/self_trader.py docs/st_params_bn.json
```

### 2. 解析命令行参数

```python
if len(sys.argv) != 2:
    print("usage: python self_trader.py <config_file>")
    exit(1)

config_file = sys.argv[1]
```

### 3. 加载配置文件

```python
with open(config_file, 'r') as f:
    _params = json.load(f)
selftrade_params = [SelftradeParameter(param) for param in _params]
asyncio.run(main(selftrade_params))
```

### 4. 主循环 (main 函数)

```python
async def main(params: list[SelftradeParameter]):
    # 创建日志记录器
    logger = create_logger(BASE_DIR, "selftrade.log", 'TUNA_SELFTRADE', backup_cnt=10)
    
    # 初始化上下文变量
    _last_operating_ts = {}  # 记录操作时间戳
    _prev_context = {}       # 存储上下文信息
    
    while 1:
        ts = time.time()
        tasks = []
        
        for param in params:
            symbol_key = f"{param.maker_exchange}_{param.maker_symbol}"
            
            # 检查更新频率
            if _last_operating_ts.get(symbol_key, 0) + param.interval > ts:
                continue
            
            # 初始化交易对上下文
            if symbol_key not in _prev_context:
                client = get_private_client(
                    exchange=param.maker_exchange,
                    api_key=param.api_key,
                    api_secret=param.api_secret,
                    passphrase=param.passphrase,
                    logger=logger,
                )
                client.mock = False
                _prev_context[symbol_key] = {
                    'client': client, 
                    'price': 0, 
                    'minute': 0, 
                    'qty': 0, 
                    'follow_exchange': param.follow_exchange
                }
            
            # 创建自成交任务
            tasks.append(asyncio.create_task(self_trade(
                param, _prev_context[symbol_key], logger)))
            
            # 更新操作时间戳
            _last_operating_ts[symbol_key] = ts
        
        # 并行执行自成交任务
        if tasks:
            await asyncio.gather(*tasks)
        else:
            await asyncio.sleep(0.05)  # 空闲时休眠
```

### 5. 执行自成交 (self_trade 函数)

```python
async def self_trade(param: SelftradeParameter, ctx: dict, logger: Logger) -> bool:
    # 1. 从 Redis 获取跟随交易对的成交数据
    if ctx['follow_exchange'] == "binance_UMFuture" or ctx['follow_exchange'] == "binance_portfolio_margin":
        _exchange_prefix = "binance_future"
    else:
        _exchange_prefix = ctx['follow_exchange']
    symbol_key = f'{_exchange_prefix}_{EXCHANGE_TICKER_PREFIX}{param.follow_symbol}'
    trade = DATA_REDIS_CLIENT.get_ticker(symbol_key)
    
    if not trade or not trade.get('price') or not trade.get('qty'):
        logger.warning('fail to get ticker [%s] with symbol_key %s', param.follow_symbol, symbol_key)
        return False
    
    # 2. 获取做市交易对的订单簿
    symbol = param.maker_symbol
    ob: AskBid = ctx['client'].top_askbid(symbol)
    
    if not ob:
        logger.warning('no order book %s', symbol)
        return False
    
    top_ask, top_ask_qty = float(ob[0].ap), float(ob[0].aq)
    top_bid, top_bid_aty = float(ob[0].bp), float(ob[0].bq)
    
    # 3. 计算交易价格和数量
    qty = float(trade['qty']) * param.qty_multiplier
    _random_coef = 0.9995 + 0.00001 * random.randrange(0, 100)
    price_decimals = param.price_decimals
    qty_decimals = param.qty_decimals
    
    if trade['price']:
        price = float(trade['price'])
        
        # 处理价格连续相同的情况
        if ctx['price'] == price:
            if price == top_ask:
                price -= 1.0 / 10 ** price_decimals
            else:
                price += 1.0 / 10 ** price_decimals
        
        # 处理价格偏离过大的情况
        elif ctx['price'] > 0:
            if abs(price / ctx['price'] - 1) > param.price_divergence:
                logger.error("Abnormal Ticker Volatility %s: pre price=%s, price=%s",
                    symbol, ctx['price'], price)
                if price > ctx['price']:
                    price = ctx['price'] * (1 + param.price_divergence)
                else:
                    price = ctx['price'] * (1 - param.price_divergence)
        
        qty *= _random_coef
    else:
        # 使用之前的价格和订单簿深度
        price = ctx['price']
        qty = 0.5 * (top_ask_qty + top_bid_aty) * _random_coef
    
    if price <= 0:
        return False
    
    # 4. 调整交易价格和数量
    qty = min(round(max(1.0 / 10 ** qty_decimals, qty), qty_decimals),
              round(float(param.max_amt_per_order) / price, qty_decimals))
    
    if qty > 0:
        # 处理分钟切换的情况
        current_minute = int(int(time.time()) / 60) % 60
        if current_minute != ctx['minute']:
            price = ctx['price']
        
        ctx['minute'] = current_minute
        # 确保价格在有效范围内
        price = max(min(price, top_ask), top_bid)
        ctx['price'] = price
        
        # 处理数量连续相同的情况
        if qty == ctx['qty']:
            qty *= 1.0001
        ctx['qty'] = qty
        
        # 5. 执行交易
        res = await _trade(ctx, symbol, param.term_type,
                           str(round(price, price_decimals) if price_decimals else int(price)),
                           str(round(qty, qty_decimals) if qty_decimals else int(qty)),
                           logger)
        
        # 6. 取消做市订单
        if res:
            await _cancel_orders(ctx, symbol, res[0].order_id, logger)
        
        return True
    
    return False
```

### 6. 执行交易 (_trade 函数)

```python
async def _trade(ctx: dict, symbol: str, term_type: str, price: str, qty: str, logger: Logger):
    # 随机选择交易方向
    side = random.choice(SIDES)
    ts = int(time.time() * 1000)
    contract_size = 0.1
    leverage = 2
    
    # 根据交易类型创建订单
    if term_type == 'SPOT':
        orders = [
            NewOrder(
                symbol=symbol,
                client_id=f'M{symbol}_{ts}',
                side='BUY' if side == 'SELL' else 'SELL',
                type="LIMIT",
                quantity=qty,
                price=price,
                biz_type="SPOT",
                tif='GTX',
                position_side='',
            ),
            NewOrder(
                symbol=symbol,
                client_id=f'T{symbol}_{ts}',
                side=side,
                type="LIMIT",
                quantity=qty,
                price=price,
                biz_type="SPOT",
                tif='IOC',
                position_side='',
            )
        ]
    elif term_type == 'FUTURE':
        orders = [
            NewOrder(
                symbol=symbol,
                client_id=f'M{symbol}_{ts}',
                side='BUY' if side == 'SELL' else 'SELL',
                type="LIMIT",
                quantity=str(int((float(qty) * leverage) / contract_size)),
                price=price,
                biz_type="FUTURE",
                tif='GTX',
                position_side='LONG' if side == 'SELL' else 'SHORT',
            ),
            NewOrder(
                symbol=symbol,
                client_id=f'T{symbol}_{ts}',
                side=side,
                type="LIMIT",
                quantity=str(int((float(qty) * leverage) / contract_size)),
                price=price,
                biz_type="FUTURE",
                tif='IOC',
                position_side='SHORT' if side == 'SELL' else 'LONG',
            )
        ]
    else:
        logger.error("Unknown term_type: %s", term_type)
        return None
    
    # 批量下单
    return ctx['client'].batch_make_orders(orders, symbol)
```

### 7. 取消做市订单 (_cancel_orders 函数)

```python
async def _cancel_orders(ctx, symbol, order_id, logger: Logger):
    # 最多重试 3 次
    for _retry in range(3):
        try:
            res = ctx['client'].cancel_order(order_id, symbol)
            if res.order_id == order_id:
                logger.debug("cancel_orders: %s", order_id)
                return True
        except Exception as e:
            logger.error("cancel_orders: %s; error: %s", order_id, e)
        time.sleep(0.5)  # 重试间隔
    return False
```

## 数据流向

```
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ 交易所    │────>│ Redis     │────>│ Self-    │────>│ 交易所    │
│ 行情      │     │ 存储      │     │ Trader   │     │ 交易      │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
                                                                 │
                                                                 │
┌───────────┐     ┌───────────┐     ┌───────────┐     ┌───────────┐
│ 日志      │<────│ Self-    │<────│ 交易所    │<────│ 订单      │
│ 记录      │     │ Trader   │     │ 订单簿    │     │ 响应      │
└───────────┘     └───────────┘     └───────────┘     └───────────┘
```

## 配置文件示例

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

## 主要参数说明

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

## 交易逻辑说明

### 1. 价格计算逻辑

1. **基础价格**：使用跟随交易对的最新成交价格
2. **价格调整**：
   - 如果连续两次交易价格相同，微调价格
   - 如果价格偏离过大，限制价格变动范围
   - 确保价格在订单簿的有效范围内（不超过最高买价，不低于最低卖价）

### 2. 数量计算逻辑

1. **基础数量**：跟随交易对的成交数量 × 数量乘数
2. **随机调整**：应用随机系数（0.9995-1.0005）
3. **范围限制**：
   - 不小于最小订单数量
   - 不大于最大金额/价格
   - 如果连续两次交易数量相同，微调数量

### 3. 交易执行逻辑

1. **订单类型**：
   - 做市订单：LIMIT 类型，GTX（只做maker）
   - 成交订单：LIMIT 类型，IOC（立即成交否则取消）
2. **交易方向**：随机选择 BUY 或 SELL
3. **订单取消**：交易成功后取消做市订单

## 注意事项

1. **Redis 依赖**：确保 Redis 服务正常运行，自成交模块依赖 Redis 获取行情数据
2. **API 密钥安全**：妥善保管 API 密钥，避免在配置文件中明文存储
3. **参数调优**：根据市场情况调整参数，特别是数量乘数和价格偏离阈值
4. **风险控制**：设置合理的最大订单金额，避免过大风险
5. **网络稳定性**：确保网络连接稳定，避免因网络问题导致交易执行异常
6. **交易所限制**：了解并遵守各交易所的 API 调用限制和规则

## 常见问题

### 1. 无法获取行情数据
- 检查 Redis 服务是否运行
- 确认跟随交易对的行情数据是否正常存储到 Redis
- 检查 Follow Exchange 和 Follow Symbol 参数是否正确

### 2. 无法获取订单簿数据
- 检查交易所 API 连接是否正常
- 确认 Maker Symbol 参数是否正确
- 检查 API 权限是否足够

### 3. 交易执行失败
- 检查 API 密钥和签名是否正确
- 确认交易对是否支持当前交易类型
- 检查账户余额是否充足

### 4. 价格或数量异常
- 调整 Price Divergence 参数，控制价格变动范围
- 调整 Qty Multiplier 参数，控制订单大小
- 检查跟随交易对的成交数据是否异常

### 5. 取消订单失败
- 检查订单 ID 是否正确
- 确认订单是否仍然存在
- 检查 API 权限是否包含取消订单权限

# 详细实现设计文档：单股量化做 T 系统

## 1. 系统架构设计 (System Architecture)
系统采用典型的事件驱动量化架构，分为五层：
1. **数据中心 (Data Center)**：负责实时行情获取与历史数据清洗。
2. **核心策略引擎 (Strategy Engine)**：计算技术指标并生成买卖信号。
3. **回测与评价模块 (Backtest & Analytics)**：验证策略历史表现。
4. **执行与通知层 (Execution & Notify)**：负责风险控制、模拟/实盘下单逻辑及消息推送。
5. **交互面板 (Dashboard)**：基于 Web 的可视化监控与参数配置。

## 2. 技术栈与依赖库 (Technology Stack)
* **语言**: Python 3.10+
* **数据处理**: Pandas, NumPy
* **技术指标**: Pandas_TA
* **可视化**: Plotly, Streamlit
* **回测引擎**: VectorBT
* **任务调度**: APScheduler
* **通知接口**: Requests (Telegram/Bark API)
* **数据源**: AkShare (A股) / yfinance (美港股)

## 3. 模块化接口设计 (Detailed Module Design)

### 3.1 数据层 (data_provider.py)
* **主要类**: StockDataClient
* **核心方法**:
    * get_history(symbol, period, interval): 获取历史 K 线。
    * get_realtime_quote(symbol): 获取当前最新价及成交量。

### 3.2 策略层 (strategy.py)
* **核心类**: GridTStrategy
* **数学逻辑实现**:
    * 计算指标: EMA20, EMA60, ATR, RSI, Bollinger Bands。
    * 信号逻辑判断。

### 3.3 回测层 (backtester.py)
* **核心功能**:
    * 集成 VectorBT 进行回测。
    * 支持动态头寸模拟（底仓 + 滚动仓）。
    * 输出：累计收益率、最大回撤、夏普比率等。

### 3.4 任务调度与执行层 (engine.py)
* **核心流程**: 定时触发 Job -> 获取价格 -> 判断信号 -> 检查风控 -> 触发通知。

## 4. 核心类接口规范 (Interface Specification)
```python
class TradingSignal:
    def __init__(self, action, price, reason):
        self.action = action  # 'BUY', 'SELL', 'HOLD'
        self.price = price
        self.reason = reason

class IStrategy:
    def compute_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        pass
    def check_signals(self, df: pd.DataFrame) -> TradingSignal:
        pass
```

## 5. UI 交互设计 (app.py)
使用 Streamlit 构建单页面应用，包含：
* **侧边栏**: 参数配置。
* **主面板**: 实时图表 (Plotly)、回测报告、当前持仓状态。

## 6. 异常处理与鲁棒性设计
1. **数据断流处理**：超时重试机制。
2. **非交易时段自动休眠**：根据交易所日历判断。
3. **日志记录**：全过程信号与指标快照记录。

## 7. AI 编写指令 (Prompt for AI Implementation)
请根据设计文档，使用 Python 编写模块化做 T 工具。要求使用 pandas_ta 计算指标，vectorbt 进行回测，streamlit 做前端展示。代码需包含详细注释并遵循 PEP8。

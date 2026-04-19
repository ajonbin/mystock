# 详细实现设计文档：单股量化做 T 系统

## 1. 系统架构设计 (System Architecture)
系统采用分层模块化架构，分为五层：
1. **数据与持久化层 (Data & Persistence)**：负责从 API 获取行情，并通过 SQLite 实现增量缓存。
2. **策略引擎 (Strategy Engine)**：利用 `pandas_ta` 计算技术指标并生成多模式买卖信号。
3. **回测模块 (Backtest Engine)**：基于循环的逻辑模拟真实交易环境（含资金与单位限制）。
4. **国际化层 (i18n)**：支持多语言 UI 切换。
5. **交互面板 (Dashboard)**：基于 Streamlit 的可视化监控与参数配置。

## 2. 技术栈与依赖库 (Technology Stack)
* **语言**: Python 3.12+
* **数据处理**: Pandas, NumPy
* **持久化**: SQLite3
* **技术指标**: Pandas_TA
* **可视化**: Plotly, Streamlit
* **数据源**: AkShare (A股) / yfinance (美港股)

## 3. 模块化设计 (Detailed Module Design)

### 3.1 数据层 (data/)
* **storage.py**: 
    * 负责 SQLite 数据库操作。
    * 自动为不同股票和复权方式创建独立数据表。
* **data_provider.py**:
    * 核心类 `StockDataClient`。
    * 实现增量更新逻辑：`本地数据最后日期 + 1` 至 `今日`。

### 3.2 策略层 (strategy/strategy.py)
* **核心类**: `GridTStrategy`
* **支持模式**:
    * `standard`: 严格的指标共振触发。
    * `aggressive`: 宽松的趋势破位触发。

### 3.3 回测层 (backtest/backtester.py)
* **核心功能**:
    * 模拟“底仓 + 滚动仓”模式。
    * **真实性约束**: 
        * 100 股最小交易单位。
        * 严格现金购买力限制。
        * 自动过滤负值价格（针对 QFQ 数据）。
    * **指标稳定性**: 预留数据热身窗口，确保不同开始日期的信号一致性。

## 4. 核心接口规范 (Interface Specification)
```python
class TradingSignal:
    def __init__(self, action, price, reason):
        self.action = action  # 'BUY', 'SELL', 'HOLD'
        self.price = price
        self.reason = reason

class StockDataClient:
    def get_history(self, symbol, period, interval, adjust) -> pd.DataFrame:
        # 缓存优先逻辑
        pass
```

## 5. UI 交互设计 (app.py)
* **多语言切换**: 实时响应中英文切换。
* **复权统一**: 侧边栏统一控制图表与回测的复权方式。
* **资产穿透**: 回测结果展示现金、底仓、交易仓的详细价值拆解。

## 6. 鲁棒性与异常处理
1. **网络容错**: 在获取实时行情时加入异常捕获，防止 API 限制导致崩溃。
2. **数据完整性**: 使用 Pandas 的 `duplicated(keep='last')` 确保增量合并时无重复数据。
3. **资金安全**: 核心买入逻辑加入 90% 现金阈值保护，预留交易税费空间（未来扩展）。

# Strategy Documentation / 策略说明文档

This document provides a detailed explanation of the trading strategy used in this system, including parameters, signal logic, and backtesting mechanisms.

本项目详细介绍了系统中所使用的交易策略，包括参数设置、信号逻辑以及回测机制。

---

## 1. Strategy Parameters / 策略参数

| Parameter / 参数 | Default / 默认值 | Description / 描述 |
| :--- | :--- | :--- |
| **EMA Long (长期均线)** | 60 | Used as a trend filter. Generally, the strategy is more effective when the price is above this line (uptrend). <br> 用于趋势过滤。通常价格在均线上方时策略表现更佳。 |
| **EMA Mid (中期均线)** | 20 | Used as the baseline for Bollinger Bands and a secondary trend indicator. <br> 作为布林带的中轨基准以及中期趋势指标。 |
| **RSI Low (超卖阈值)** | 30 | The Relative Strength Index level indicating an oversold condition (potential buy). <br> 相对强弱指数，用于判断市场是否超卖（潜在买点）。 |
| **RSI High (超买阈值)** | 70 | The Relative Strength Index level indicating an overbought condition (potential sell). <br> 相对强弱指数，用于判断市场是否超买（潜在卖点）。 |
| **BB Std Dev (布林带标准差)** | 2.0 | Multiplier for volatility bands. Higher values require more extreme price moves to trigger signals. <br> 波动率通道乘数。值越高，需要越极端的波动才能触发信号。 |

---

## 2. Signal Trigger Logic / 信号触发逻辑

The system supports two modes of execution:

系统支持两种执行模式：

### Standard Mode (保守模式)
*Uses strict **AND** logic to minimize false signals.*
*使用严格的 **且(AND)** 逻辑，旨在减少误报。*

- **BUY (买入)**: 
    - Price < Bollinger Lower Band **AND** RSI < `RSI Low`
    - 价格 < 布林线下轨 **且** RSI < 超卖阈值
- **SELL (卖出)**: 
    - Price > Bollinger Upper Band **AND** RSI > `RSI High`
    - 价格 > 布林线上轨 **且** RSI > 超买阈值

### Aggressive Mode (激进模式)
*Uses looser **OR** logic to capture more opportunities in volatile markets.*
*使用宽松的 **或(OR)** 逻辑，以在波动市场中捕捉更多机会。*

- **BUY (买入)**: 
    - Price < Bollinger Lower Band **OR** (Price < EMA Mid **AND** RSI < `RSI Low` + 5)
    - 价格 < 布林线下轨 **或** (价格 < 中期均线 **且** RSI < 超卖阈值 + 5)
- **SELL (卖出)**: 
    - Price > Bollinger Upper Band **OR** (Price > EMA Mid **AND** RSI > `RSI High` - 5)
    - 价格 > 布林线上轨 **或** (价格 > 中期均线 **且** RSI > 超买阈值 - 5)

---

## 3. Backtest vs. Chart Signals / 回测与图表信号的区别

You may notice more signal markers on the chart than trades in the backtest report. This is due to the **Core + Trading** execution model:

您可能会发现图表上的信号标记多于回测报告中的成交记录。这是由“底仓+网格交易”模型决定的：

1.  **Initial Core (底仓购买)**: The very first "BUY" in the backtest is the **Core Position** setup. It occurs on day one regardless of indicators.
    *   **初始底仓**: 回测开始的第一笔“买入”是建立底仓，通常在回测的第一天执行，不受技术指标限制。
2.  **Cash Constraint (资金限制)**: A `BUY` signal is ignored if the account has insufficient cash to buy at least **100 shares**.
    *   **资金限制**: 如果账户剩余资金不足以购买至少 **100 股**（最小交易单位），则会忽略“买入”信号。
3.  **Position Constraint (持仓限制)**: A `SELL` signal is only executed if there is a **Trading Position** to sell. The strategy will NOT sell your "Core" shares during T+0 operations.
    *   **持仓限制**: “卖出”信号仅在持有“交易仓位”时执行。该策略在做 T 过程中不会卖出您的“底仓”份额。
4.  **Lot Size (整百交易)**: All trades are rounded down to the nearest 100 shares to reflect realistic stock market rules.
    *   **整百交易**: 所有交易都会向下取整至 100 股的整数倍，以符合真实的股票交易规则。

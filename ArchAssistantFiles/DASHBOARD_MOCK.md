# 🧠 FundRunner – CLI Dashboard Overview

## 📅 Live Portfolio View (Auto-Displayed on Launch)

**As of:** 2025-05-20 14:17:02

| Symbol | Qty | Avg Entry | Price  | \$ P/L |
| ------ | --- | --------- | ------ | ------ |
| AAPL   | 20  | 135.00    | 143.12 | +162   |
| TSLA   | 10  | 650.00    | 631.77 | -182   |

> 🔁 \[T] Launch Ticker — live tracking from positions + watchlists

---

## 🧭 Main Menu

| Key | Action                    |
| --- | ------------------------- |
| 1   | View Account Info         |
| 2   | Enter Trade               |
| 3   | Manage Watchlists         |
| 4   | Run Trading Bot           |
| 5   | Run Options Bot           |
| 6   | Ask Trading Advisor (LLM) |
| 7   | View Logs & History       |
| 8   | Utilities                 |
| 0   | Exit                      |

---

## 💰 \[1] Account Info Menu

**Balance Summary**

```
Cash:              $23,442.10
Buying Power:      $46,884.20
Equity:            $72,200.55
Portfolio Value:   $71,100.22
Overall P/L:       +$1,884.20
```

**Order Summary**

```
Open Orders: 3
Recent Orders: 10

ID       | Symbol | Side | Qty | Status
-------- |--------|------|-----|--------
A1B2C3   | TSLA   | Buy  | 10  | filled
D4E5F6   | AAPL   | Sell | 5   | open
G7H8I9   | NVDA   | Buy  | 2   | open
```

| Option | Action              |
| ------ | ------------------- |
| 1      | View Balance Only   |
| 2      | View Order History  |
| 3      | View Open Orders    |
| 0      | Return to Main Menu |

---

## 📝 \[2] Submit a Trade

**Trade Entry Prompt**

```
• Symbol         [e.g. TSLA]
• Quantity       [e.g. 10]
• Side           [buy / sell]
• Order Type     [market / limit]
• Time in Force  [gtc / day / ioc]
```

Example:

```
> Symbol: TSLA
> Qty: 5
> Side: buy
> Order Type: market
> Time in Force: gtc
```

\[0] Cancel & Return

---

## 📋 \[3] Watchlist Manager

| Option | Action                       |
| ------ | ---------------------------- |
| 1      | List All Watchlists          |
| 2      | Create New Watchlist         |
| 3      | Add Symbol to Watchlist      |
| 4      | Remove Symbol from Watchlist |
| 5      | Delete Watchlist             |
| 6      | View Watchlist by ID         |
| 0      | Return to Main Menu          |

---

## ⚙️ \[4] Trading Bot Menu

**Trading Bot Settings**

```
Vetting Enabled:    True
Vetter Source:      Local LLM
Auto-Confirm Orders: False
Default Symbols:     AAPL, TSLA
```

| Option | Description            |
| ------ | ---------------------- |
| 1      | Set Target Symbols     |
| 2      | Toggle Auto-Confirm    |
| 3      | Configure Vetting Mode |
| 4      | Review Risk Rules      |
| 5      | Launch Trading Bot     |
| 0      | Return to Main Menu    |

---

## 📈 \[5] Options Bot Menu

**Options Bot Setup**

```
Mode:             Analysis / Execution
Target Strategy:  Vertical Spreads
Default Symbols:  TSLA, SPY
```

| Option | Description             |
| ------ | ----------------------- |
| 1      | Set Target Options      |
| 2      | Configure Strategy Type |
| 3      | View Risk Summary       |
| 4      | Run Options Bot Now     |
| 0      | Return to Main Menu     |

---

## 🤖 \[6] Ask Trading Advisor (LLM)

- Prompt: “What’s the safest high-yield equity to rotate into?”
- Contextual logic powered by `chatgpt_advisor.py`
- Can pull portfolio positions + sentiment

---

## 📊 \[7] Logs & History Menu

| Option | View                      |
| ------ | ------------------------- |
| 1      | Transaction History Log   |
| 2      | Trade Execution Snapshots |
| 3      | AI Advisory History       |
| 4      | Debug + Error Logs        |
| 0      | Return to Main Menu       |

---

## 🧪 \[8] Utilities Menu

| Option | Tool                    |
| ------ | ----------------------- |
| 1      | Metrics Formatter       |
| 2      | Backtester              |
| 3      | Import/Export Snapshots |
| 4      | Launch Market Screener  |
| 5      | Configure Alerts        |
| 0      | Return to Main Menu     |

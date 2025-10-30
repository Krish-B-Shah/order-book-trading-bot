# 🧠 High-Frequency Trading Simulator & Live Trading Bot

This Python project simulates a high-frequency trading (HFT) environment with a realistic order book, market-making bot, and backtesting/visualization tools. It also includes a live trading module for real broker integration (Alpaca).

Inspired by real-world trading infrastructure, this project is ideal for experimenting with algorithmic strategies, market microstructure, and even live trading (with caution).

---

## 🚀 Features

- 📥 **Limit & Market Order Support**  
  Realistic trading actions through market and limit orders with full lifecycle tracking.

- ⚖️ **Priority-Based Matching**  
  Heap queues enforce strict price-time priority for bid/ask execution.

- 📊 **P&L Tracking**  
  Tracks cash, inventory, and unrealized gains/losses in real time per strategy agent.

- 🤖 **Bot Strategy Integration**  
  Plug in market-making strategies with inventory control and reactive logic.

- 📈 **Performance Visualization**  
  P&L, cash, inventory, and trade prices visualized round-by-round using `matplotlib`.

- 🧪 **Simulation with Noise**  
  Simulates realistic price movement using randomized spread, price drift, and symbol-specific volatility.

- 🧩 **Backtesting & Reporting**  
  Automated backtesting with HTML and PNG report generation.

- 🔌 **Live Trading (Alpaca)**  
  `live_trading.py` allows you to connect to Alpaca and trade live (paper or real money) with advanced risk controls and logging.

---

## 📂 Project Structure

```
order-book-trading-bot/
├── src/
│   ├── core/
│   │   ├── order_book.py
│   │   ├── order.py
│   │   ├── matching_engine.py
│   │   └── utils.py
│   ├── strategies/
│   │   ├── market_maker.py
│   │   └── mean_reversion.py   # if you have one later
│   ├── backtest/
│   │   ├── backtester.py
│   │   ├── execution_sim.py
│   │   └── analytics.py
│   └── main.py
│
├── tests/
│   ├── test_order_book.py
│   ├── test_matching_engine.py
│   └── test_strategy.py
│
├── data/
│   └── sample_orders.csv
│
├── logs/
│   └── execution.log
│
├── notebooks/        # research + plotting only
│   └── research.ipynb
│
├── assets/          # charts, reports
│   └── *.png
│
├── README.md
├── requirements.txt
├── .gitignore
```

---

## 🧠 How It Works

- **Order Book:**  
  Simulates a real exchange with price-time priority, partial/missed fills, and trade logging.

- **Market Data:**  
  Uses Alpaca historical data, yfinance, or synthetic data (with symbol-specific volatility).

- **Market-Making Bot:**  
  Places buy/sell orders, manages inventory, and is penalized for excessive risk. Easily extensible for new strategies.

- **Simulation & Backtesting:**  
  Run interactive or automated simulations, visualize results, and generate performance reports.

- **Live Trading:**  
  `live_trading.py` can connect to Alpaca for real or paper trading. Includes interactive setup, risk management, and advanced logging. **Use with caution and real API keys only if you understand the risks.**

---

## ⚠️ Simulation vs. Live Trading

- **main.py** and **backtester.py** are **simulated**—no real money is at risk.
- **live_trading.py** can place real trades if configured with valid API keys.  
  - By default, it uses Alpaca's paper trading mode.
  - Review and test thoroughly before using with real funds.

---

## 🛠️ Extending the Project

- Add new strategies (momentum, arbitrage, etc.) in `strategy.py`.
- Plug in new data sources or execution logic.
- Simulate multiple bots/agents.
- Integrate with a web dashboard for live monitoring.

---

## 👤 Author

Krish B. Shah  
📫 krshah828@gmail.com  
🔗 [LinkedIn](#)  
💻 [GitHub](#)  

---

**For questions, contributions, or to report issues, please open an issue or contact the author.**


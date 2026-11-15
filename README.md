# 📈 Quant Trading Bot

A Python-based quantitative trading bot that generates multi-indicator
trading signals for the Investopedia Stock Simulator.
Built for education, research, and strategy experimentation.

---

## 🚀 Features

- **Multi-indicator signals** — RSI, MACD, Bollinger Bands, SMA crossovers
- **Weighted signal scoring** — BUY / SELL / HOLD with strength percentage
- **Risk management** — position sizing, stop-loss, take-profit
- **Mock trading mode** — test strategies with zero risk
- **Streamlit dashboard** — live charts, indicators, watchlist signals
- **Unit tests** — pytest suite for the signal engine
- **Jupyter notebook** — sandbox for research and exploration
- **Optional LSTM signals** — one-step forecasts in `lstm`, or combined with
  indicators in `ensemble` mode
- **Per-user investment planning** — budget-based recommendations, manual
  stock selection, allocations, reserves, and optional downside alerts

---

## 📁 Project Structure

    quant-trading-bot/
    ├── .vscode/                  # VS Code run/debug configurations
    │   ├── launch.json
    │   └── settings.json
    ├── src/
    │   ├── __init__.py
    │   ├── api_client.py         # Mock client (+ future real API client)
    │   ├── signals.py            # Trading signal generation
    │   ├── strategies.py         # Strategies & position sizing
    │   ├── backtest.py           # Backtesting engine (WIP)
    │   └── utils.py              # Helpers (logging, formatting)
    ├── data/                     # Historical data storage
    ├── logs/                     # Trading logs
    ├── notebooks/
    │   └── analysis.ipynb        # Research notebook
    ├── tests/
    │   └── test_signals.py       # Unit tests
    ├── .env                      # Environment variables (secrets)
    ├── .gitignore
    ├── config.py                 # Watchlist + strategy parameters
    ├── dashboard.py              # Streamlit dashboard
    ├── main.py                   # Main entry point
    ├── requirements.txt
    ├── INVESTOPEDIA_API_SETUP.md # Real API integration guide
    └── README.md

---

## 🛠️ Setup

### 1. Prerequisites

- Python 3.9+ (3.12+ recommended)
- Git
- (Optional) Node.js — only needed for real Investopedia API integration

### 2. Install

    cd quant-trading-bot
    python -m venv venv
    .\venv\Scripts\Activate
    pip install -r requirements.txt

### 3. Configure

Edit .env with your settings:

    INVESTOPEDIA_USERNAME=your_email@example.com
    INVESTOPEDIA_PASSWORD=your_password
    DEFAULT_CASH=100000
    ENABLE_AUTO_TRADE=false

---

## 🎮 Usage

### Run the bot (one analysis cycle)

    python main.py

### Run the dashboard

    streamlit run dashboard.py

Then open http://localhost:8501

### Run the tests

    pytest tests/ -v

### Run the LSTM strategy

Install the optional ML dependency with `pip install -r requirements-lstm.txt`,
then set `SIGNAL_MODE=lstm` (or `SIGNAL_MODE=ensemble`) in `.env` and run
`python main.py`. The bot remains in mock mode unless `ENABLE_AUTO_TRADE=true`.
LSTM training uses a chronological validation split and does not use test
performance to adjust the learning rate. For a fair comparison, run the bot
once with `SIGNAL_MODE=technical`, then with `SIGNAL_MODE=lstm` or
`SIGNAL_MODE=ensemble`; use a dedicated backtest before enabling auto-trade.

### Personal investment planning

After signing in to the dashboard, each user can set an independent budget,
reserve amount, and stock selection. The planner ranks BUY signals from that
user's watchlist, but users may select any watchlist stock. It calculates
amounts and whole-share quantities without placing trades. Optional downside
alerts are saved per user and are advisory only; selling or buying remains a
manual decision.

### Test individual modules

    python src/signals.py
    python src/api_client.py

### Run via VS Code

Press Ctrl+Shift+D, pick a configuration (bot / dashboard / tests), press F5.

---

##  How Signals Work

Each indicator votes, and votes are weighted into a score (-7 to +7):

| Indicator | Buy condition | Sell condition | Weight |
|-----------|---------------|----------------|--------|
| RSI (14) | below 30 | above 70 | 2 |
| MACD cross | MACD crosses above signal | crosses below | 2 |
| SMA cross (50/200) | golden cross | death cross | 2 |
| Bollinger position | below 0.2 | above 0.8 | 1 |

- Score >= threshold  → BUY
- Score <= -threshold → SELL
- Otherwise           → HOLD

Tune thresholds and all parameters in config.py (STRATEGY_CONFIG).

---

## ➕ Adding Stocks

Edit the WATCHLIST in config.py:

    WATCHLIST = [
        "AAPL",
        "MSFT",
        "DIS",    # ← add your own tickers
    ]

Verify any ticker works:

    python -c "import yfinance as yf; df = yf.download('DIS', period='5d', progress=False); print('✅' if not df.empty else '❌')"

---

## 🔌 Real Investopedia Trading (Optional)

The bot currently runs in MOCK mode (paper trading with fake money).
To automate real simulator trades, follow INVESTOPEDIA_API_SETUP.md.

⚠️ Note: Investopedia now uses email verification codes for login,
which blocks the API's automated password login. Workarounds:
set a password via "Forgot password?", or trade manually using
the bot's signals.

---

## 🗺️ Roadmap

- [ ] Backtesting engine (src/backtest.py)
- [ ] Real Investopedia API integration
- [ ] Trade history & performance metrics (Sharpe, drawdown)
- [ ] Alerts (email / Telegram)

---

## ⚠️ Disclaimer

This project is for EDUCATIONAL purposes only. It is not financial
advice. Trading involves risk — always paper-trade first.
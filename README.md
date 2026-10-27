# Crypto Fibonacci + Simplified Elliott Wave Paper Trading Bot

**EDUCATIONAL PROJECT ONLY**

This bot implements a **conservative** strategy based on:
- Fibonacci retracement zones (50 % – 61.8 %)
- Simple swing / impulse detection (pragmatic approximation of Elliott-like structure)
- EMA trend filter
- Strict risk management (2 % risk per trade, max drawdown protection)

It is **not** a professional Elliott Wave system. Wave counting is highly subjective; this is a rule-based simplification for learning purposes.

---

## ⚠️ Important Disclaimers

- **No profit guarantee.** Most trading strategies lose money over time after fees and slippage.
- Past or paper-trading results do **not** predict future performance.
- This is for education and experimentation only.
- Never trade with money you cannot afford to lose.
- The author assumes no liability for any financial losses.

---

## Features

- Paper trading with virtual 1000 USDT
- Automatic signal generation + order simulation
- Fees + slippage simulation
- Position sizing based on 2 % risk
- Stop-loss and take-profit (Fib extensions)
- Max-drawdown halt
- Trade & equity logging
- Quick historical backtest mode
- **GitHub Actions support** → runs automatically every 4 hours, no server needed
- Ready for 60-day forward paper test

---

## Project Structure

```
crypto-fib-elliott-bot/
├── config.yaml           # All settings
├── main.py               # Entry point
├── requirements.txt
├── README.md
├── src/
│   ├── data_feed.py      # CCXT data
│   ├── indicators.py     # Fib + swing logic
│   ├── strategy.py       # Signal generation
│   ├── paper_broker.py   # Virtual exchange
│   └── risk_manager.py   # Risk controls
└── logs/                 # Output files
```

---

## Installation

```bash
# Clone or download the project
cd crypto-fib-elliott-bot

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate          # Linux/Mac
# venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Configuration

Edit `config.yaml`:

- `exchange.name`: `okx` (reliable from most locations; change to `binance` / `bybit` if preferred and reachable)
- `trading.symbol`: currently `BTC/USDT`
- `trading.timeframe`: `4h` (recommended)
- `trading.initial_capital`: `1000`
- `trading.risk_per_trade`: `0.02` (2 %)
- Strategy parameters are set to conservative defaults

---

## Usage

### Empfohlener Weg: GitHub Actions (kein eigener Rechner nötig)

1. Erstelle ein neues **privates** Repository auf GitHub.
2. Lade den kompletten Projektordner hoch (oder pushe ihn per Git).
3. Gehe im Repository auf den Tab **Actions**.
4. Aktiviere Workflows falls GitHub danach fragt.
5. Der Workflow `Paper Trading Bot` läuft automatisch **alle 4 Stunden**.
6. Du kannst ihn auch manuell starten: Actions → Paper Trading Bot → Run workflow.

Der Bot speichert nach jedem Lauf den aktuellen Zustand (Kapital, offene Position, Trades) im Ordner `logs/` und committed die Änderungen automatisch zurück ins Repository.

**Dateien, die du beobachten solltest:**
- `logs/state.json` → aktuelles Kapital + offene Position
- `logs/trades.csv` → alle abgeschlossenen Trades
- `logs/equity.csv` → Equity-Verlauf

---

### Lokal testen (optional)

#### 1. Quick historical backtest

```bash
python main.py --mode backtest
```

#### 2. Einzelner Check (wie GitHub Actions)

```bash
python main.py --mode once
```

#### 3. Kontinuierlicher Paper-Trading-Loop (braucht laufenden Rechner)

```bash
python main.py --mode paper --days 60 --interval 15
```

---

## Output

- `logs/bot.log` – full runtime log
- `logs/trades.csv` – all closed trades
- `logs/equity.csv` – equity curve
- `logs/backtest_trades.csv` – from backtest mode

---

## Going Live later (advanced)

The architecture is prepared so you can later replace `PaperBroker` with a real CCXT order executor.  
**Do this only after:**

1. Extensive paper testing
2. Understanding every part of the code
3. Adding proper API key security, error handling, and monitoring
4. Accepting that you can lose the entire capital

I strongly recommend staying in paper mode for a long time.

---

## Risk Management Summary

| Rule                    | Value          |
|-------------------------|----------------|
| Risk per trade          | 2 % of equity  |
| Max open positions      | 1              |
| Max drawdown halt       | 15 %           |
| Entry zone              | 50–61.8 % Fib  |
| Trend filter            | EMA 50 / 200   |
| Fees + slippage         | simulated      |

---

## License & Responsibility

This code is provided as-is for educational purposes.  
You are solely responsible for any use of this software and any financial decisions you make.

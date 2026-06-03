# 🦋 Glasswing v3 — NIFTY Momentum Scalper

Rule-based options trading bot evolved from **Vishwas Mali's strategy** via **Shadow Account backtest analysis**.

## 📊 What is Glasswing v3?

Glasswing v3 is a NIFTY options scalping bot that uses a strict rule-based approach, refined through analysis of a real intraday trader's 6 days of broker trade data (Vishwas Mali, BBLM51898, Angel One).

## 🎯 Strategy Rules

Tuned from Shadow Account backtest (6 days, 20 trades):

| Rule | Value | Why |
|------|-------|-----|
| **Stop Loss** | 10% strict | Mali's #1 broken rule — strict SL saves ~₹655 over 6 days |
| **Take Profit** | 20% | Mali's 15% too tight — cut May 31 winner short |
| **Max Hold** | 30 min | Mali's sweet spot was 1-15 min holds (73% WR) |
| **Strike** | ATM only (max 100 pts away) | Far OTM = disaster (Apr 9 CE 24200) |
| **Entry Window** | 9:20 AM - 2:30 PM IST | 90% of Mali's entries were after 10:00 AM (rule violation) |
| **Force Close** | 3:15 PM IST | EOD noise avoidance |
| **Position Size** | 1 lot NIFTY (65 qty) | Conservative sizing |
| **Max Positions** | 3 concurrent | Risk management |

## 📈 Key Findings from Shadow Account

Analyzed **20 real trades** across 6 days from Vishwas Mali's broker PDFs:

- **Actual P&L:** +₹1,061
- **Shadow (Strict Rules) P&L:** +₹1,717
- **Money left on table:** +₹656 (**+62% improvement**)
- **Win rate:** 50% (10W/10L)

### Top Money-Losing Rule Violations
1. **Apr 9: CE 24200** — Lost ₹1,103 (held to -32.9% instead of -10% SL)
2. **May 19: CE 23850** — Lost ₹1,063 (held to -23.2% instead of -10% SL)
3. **May 28: CE 24000** — Lost ₹658 (held to -17.5% instead of -10% SL)

## 🚀 Quick Start

```bash
# Install
git clone https://github.com/panditvirchandra77-lgtm/glasswing-v3.git
cd glasswing-v3

# Run single scan
python3 glasswing_v3.py

# Connect to Shoonya paper broker (₹0 brokerage)
python3 shoonya_runner.py

# Run continuous scanning (60 sec interval)
python3 shoonya_runner.py loop 60
```

## 📁 Files

- `glasswing_v3.py` — Main bot logic (NIFTY Momentum Scalper)
- `shoonya_runner.py` — Integration with Shoonya paper broker
- `SKILL.md` — OpenClaw skill definition
- `README.md` — This file

## 🔌 Broker Support

### Paper Trading (default)
- Real NIFTY prices via Yahoo Finance
- Simulated order fills
- Full P&L tracking with Indian transaction costs

### Live Trading (Shoonya — ₹0 brokerage)
- **Broker:** Shoonya (Finvasia) — zero brokerage on all segments
- **API:** Free, no monthly subscription
- **Setup:** Create Shoonya account, install `NorenRestApiPy` + `pyotp`
- **Why Shoonya vs Dhan:** Dhan charges ₹20/order + subscription; Shoonya is 100% free

## 📜 License

MIT

## 🙏 Credits

- **Vishwas Mali** — Real trader whose strategies were reverse-engineered
- **Jeetu Parmar** — Project sponsor, broker PDF provider
- **Shadow Account Analysis** — 6-day backtest methodology

---
*Built with ❤️ by Glasswing 🦋*

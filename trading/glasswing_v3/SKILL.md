---
name: glasswing-v3
description: Glasswing v3 NIFTY Momentum Scalper — rule-based options trading bot tuned from Vishwas Mali's Shadow Account analysis. Use for paper/live NIFTY options trading with strict 10% SL, 20% TP, ATM-only strikes.
---

# Glasswing v3 — NIFTY Momentum Scalper

Rule-based options trading bot, evolved from Vishwas Mali's strategy via Shadow Account backtest.

## Strategy Rules (tuned from 6-day backtest)
- **Stop Loss:** 10% strict (Mali's #1 broken rule)
- **Take Profit:** 20% (vs Mali's 15% — let winners run)
- **Max Hold:** 30 minutes (Mali sweet spot was 1-15 min)
- **Strike:** ATM only, max 100 pts from spot
- **Time Window:** 9:20 AM - 2:30 PM IST
- **Force Close:** 3:15 PM IST
- **Max Positions:** 3 concurrent
- **Position Size:** 1 lot NIFTY (65 qty)

## Quick Start
```bash
cd glasswing-v3
python3 glasswing_v3.py          # Run single scan
python3 shoonya_runner.py        # Single scan with Shoonya paper broker
python3 shoonya_runner.py loop 60  # Continuous scanning
```

## Key Findings from Shadow Account
- Strict 10% SL would have **saved ₹656** over 6 days (+62% improvement)
- Apr 9 CE 24200 disaster (-₹1,586) would have been -₹482 with strict SL
- 90% of Mali's entries were after 10:00 AM (rule violation)
- 73% win rate on 1-15 min holds (Mali's edge)

## Files
- `glasswing_v3.py` — Main bot logic
- `shoonya_runner.py` — Shoonya paper broker integration
- `README.md` — Full documentation

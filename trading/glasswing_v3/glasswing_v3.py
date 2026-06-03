"""
Glasswing v3 — NIFTY Momentum Scalper
Based on Vishwas Mali's strategy + Shadow Account analysis findings.

Key rules (tuned from 6-day backtest):
  - Strict 10% Stop Loss (saves ~₹1,600 on disaster days)
  - 20% Take Profit (lets winners run, vs Mali's 15%)
  - ATM/ATM+1 strike only (skip far OTM disasters)
  - Max hold: 30 min (Mali's 1-15 min sweet spot + buffer)
  - Time window: 9:20 AM - 2:30 PM IST
  - 3:15 PM mandatory close
  - 1 lot NIFTY (65 qty) per trade
  - Max 3 concurrent positions

Mali's actual edge:
  - 9:20-9:30 AM entries: 100% win rate (best window)
  - 1-15 min holds: 73% win rate
  - ATM strikes: 70% win rate
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Indian transaction costs
STT_RATE = 0.0005          # 0.05% on sell side
BROKERAGE = 20             # ₹20 per executed order (discount broker)
GST_RATE = 0.18            # 18% on brokerage
STAMP_DUTY = 0.00003       # 0.003% on buy side
SEBI_CHARGE = 0.000001     # 0.0001% (tiny)
NSE_TXN_CHARGE = 0.000035  # 0.0035%


class GlasswingV3:
    """NIFTY Momentum Scalper — rule-based options trading bot."""

    def __init__(self, paper: bool = True, capital: float = 100000):
        self.paper = paper
        self.capital = capital
        self.cash = capital
        self.positions = []  # Open positions
        self.trade_log = []
        self.daily_pnl = 0.0
        self.wins = 0
        self.losses = 0

        # Strategy parameters (tuned from Shadow Account)
        self.STOP_LOSS_PCT = 10.0       # Mali actual: 7/10 losses exceeded this
        self.TAKE_PROFIT_PCT = 20.0     # Mali actual: 15% was too tight
        self.MAX_HOLD_MINUTES = 30      # Mali sweet spot was 1-15 min
        self.MAX_POSITIONS = 3          # Risk management
        self.LOT_SIZE = 65               # NIFTY 1 lot

        # Time windows (IST)
        self.EARLIEST_ENTRY = "09:20"   # Wait for opening volatility
        self.LATEST_ENTRY = "14:30"     # Stop new entries after this
        self.FORCE_CLOSE = "15:15"      # Mandatory square-off

        # Strike selection
        self.MAX_DISTANCE_FROM_ATM = 100  # ATM/ATM+1 only (50-100 pts max)

        # Daily limits
        self.DAILY_LOSS_LIMIT = 2000
        self.MAX_TRADES_PER_DAY = 10

    def get_nifty_ltp(self) -> float:
        """Fetch current NIFTY price from Yahoo Finance."""
        try:
            url = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1m&range=1d"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            return data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        except Exception:
            return 0.0

    def get_atm_strike(self, nifty_price: float) -> int:
        """Round to nearest 50 for ATM strike."""
        return round(nifty_price / 50) * 50

    def is_trading_window(self, now: datetime) -> bool:
        """Check if we're in a valid entry window."""
        current = now.strftime("%H:%M")
        return self.EARLIEST_ENTRY <= current <= self.LATEST_ENTRY

    def estimate_premium(self, nifty: float, strike: int, opt_type: str, time_str: str) -> float:
        """Estimate option premium using intrinsic + time value."""
        # Intrinsic
        if opt_type == "CE":
            intrinsic = max(0, nifty - strike)
        else:
            intrinsic = max(0, strike - nifty)

        # Time value (ATM gets highest, decays with distance)
        distance = abs(nifty - strike)
        if distance <= 50:
            tv = 120
        elif distance <= 100:
            tv = 70
        else:
            tv = 30

        # Time decay
        try:
            h, m = map(int, time_str.split(":"))
            mins = max(0, (h - 9) * 60 + m - 15)
            decay = max(0.5, 1.0 - mins / 400)
        except Exception:
            decay = 1.0

        return round(intrinsic + tv * decay, 2)

    def calc_costs(self, sell_price: float, qty: int) -> float:
        """Indian transaction costs for an options trade."""
        turnover = sell_price * qty * 2  # buy + sell
        stt = sell_price * qty * STT_RATE
        brokerage = BROKERAGE * 2
        gst = brokerage * GST_RATE
        stamp = sell_price * qty * STAMP_DUTY
        sebi = turnover * SEBI_CHARGE
        nse = turnover * NSE_TXN_CHARGE
        return stt + brokerage + gst + stamp + sebi + nse

    def check_entry_signal(self, nifty: float, history: list) -> Optional[dict]:
        """Check if there's a valid entry signal based on price action."""
        if not self.is_trading_window(datetime.now()):
            return None
        if len(self.positions) >= self.MAX_POSITIONS:
            return None
        if abs(self.daily_pnl) >= self.DAILY_LOSS_LIMIT and self.daily_pnl < 0:
            return None

        # Simple trend detection: NIFTY vs VWAP approximation
        # In real version, use proper VWAP from intraday data
        if len(history) < 5:
            return None

        # Recent 5 candles average
        recent_avg = sum(history[-5:]) / 5
        momentum = (nifty - recent_avg) / recent_avg * 100

        atm = self.get_atm_strike(nifty)

        # Bullish signal: momentum > 0.1%
        if momentum > 0.1:
            return {
                "action": "BUY_CE",
                "strike": atm,
                "reason": f"Bullish momentum: +{momentum:.2f}%",
                "nifty": nifty,
            }
        # Bearish signal: momentum < -0.1%
        elif momentum < -0.1:
            return {
                "action": "BUY_PE",
                "strike": atm,
                "reason": f"Bearish momentum: {momentum:.2f}%",
                "nifty": nifty,
            }
        return None

    def enter_trade(self, signal: dict) -> Optional[dict]:
        """Enter a new trade based on signal."""
        nifty = signal["nifty"]
        opt_type = "CE" if signal["action"] == "BUY_CE" else "PE"
        strike = signal["strike"]
        entry_time = datetime.now().strftime("%H:%M")

        # Validate ATM distance
        if abs(nifty - strike) > self.MAX_DISTANCE_FROM_ATM:
            return None

        # Estimate entry premium
        entry_premium = self.estimate_premium(nifty, strike, opt_type, entry_time)
        if entry_premium < 10:  # Too cheap = illiquid
            return None

        # Check capital
        required = entry_premium * self.LOT_SIZE
        if required > self.cash * 0.3:  # Max 30% per trade
            return None

        # Open position
        position = {
            "id": f"V3-{datetime.now().strftime('%H%M%S')}",
            "type": opt_type,
            "strike": strike,
            "entry_time": entry_time,
            "entry_premium": entry_premium,
            "qty": self.LOT_SIZE,
            "stop_loss": round(entry_premium * (1 - self.STOP_LOSS_PCT / 100), 2),
            "take_profit": round(entry_premium * (1 + self.TAKE_PROFIT_PCT / 100), 2),
            "highest_premium": entry_premium,
            "trailing_active": False,
            "nifty_at_entry": nifty,
        }
        self.positions.append(position)
        self.cash -= required
        return position

    def check_exit(self, position: dict, current_premium: float) -> Optional[str]:
        """Check if position should be exited."""
        # Stop loss
        if current_premium <= position["stop_loss"]:
            return "STOP_LOSS"
        # Take profit
        if current_premium >= position["take_profit"]:
            return "TAKE_PROFIT"
        # Time exit
        h1, m1 = map(int, position["entry_time"].split(":"))
        h2, m2 = map(int, datetime.now().strftime("%H:%M").split(":"))
        held = (h2 * 60 + m2) - (h1 * 60 + m1)
        if held >= self.MAX_HOLD_MINUTES:
            return "TIME_EXIT"
        # Force close at 3:15
        if datetime.now().strftime("%H:%M") >= self.FORCE_CLOSE:
            return "FORCE_CLOSE"
        return None

    def exit_trade(self, position: dict, reason: str, exit_premium: float) -> dict:
        """Close a position and book P&L."""
        diff = exit_premium - position["entry_premium"]
        gross_pnl = diff * position["qty"]
        costs = self.calc_costs(exit_premium, position["qty"])
        net_pnl = gross_pnl - costs
        self.cash += exit_premium * position["qty"]
        self.daily_pnl += net_pnl
        if net_pnl > 0:
            self.wins += 1
        else:
            self.losses += 1

        trade = {
            "id": position["id"],
            "type": position["type"],
            "strike": position["strike"],
            "entry_time": position["entry_time"],
            "exit_time": datetime.now().strftime("%H:%M"),
            "entry_premium": position["entry_premium"],
            "exit_premium": exit_premium,
            "gross_pnl": round(gross_pnl, 2),
            "costs": round(costs, 2),
            "net_pnl": round(net_pnl, 2),
            "pnl_pct": round(diff / position["entry_premium"] * 100, 2),
            "reason": reason,
        }
        self.trade_log.append(trade)
        self.positions.remove(position)
        return trade

    def scan(self) -> dict:
        """Main scanning method — run periodically."""
        nifty = self.get_nifty_ltp()
        if nifty == 0:
            return {"status": "no_data"}

        # Check exits for open positions
        now = datetime.now()
        time_str = now.strftime("%H:%M")
        for pos in list(self.positions):
            current = self.estimate_premium(nifty, pos["strike"], pos["type"], time_str)
            exit_reason = self.check_exit(pos, current)
            if exit_reason:
                self.exit_trade(pos, exit_reason, current)

        # Check for new entries
        signal = self.check_entry_signal(nifty, [nifty] * 5)  # simplified
        if signal:
            self.enter_trade(signal)

        return {
            "status": "ok",
            "nifty": nifty,
            "time": time_str,
            "open_positions": len(self.positions),
            "daily_pnl": round(self.daily_pnl, 2),
            "wins": self.wins,
            "losses": self.losses,
        }

    def get_status(self) -> dict:
        """Get current bot status."""
        return {
            "cash": round(self.cash, 2),
            "open_positions": [
                {
                    "id": p["id"],
                    "type": p["type"],
                    "strike": p["strike"],
                    "entry": p["entry_premium"],
                    "sl": p["stop_loss"],
                    "tp": p["take_profit"],
                }
                for p in self.positions
            ],
            "daily_pnl": round(self.daily_pnl, 2),
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": round(self.wins / (self.wins + self.losses) * 100, 1) if (self.wins + self.losses) > 0 else 0,
        }


if __name__ == "__main__":
    bot = GlasswingV3(paper=True, capital=100000)
    print("🦋 Glasswing v3 — NIFTY Momentum Scalper")
    print("=" * 50)
    print(f"Paper trading: ₹{bot.capital:,.0f} capital")
    print(f"Rules: {bot.STOP_LOSS_PCT}% SL | {bot.TAKE_PROFIT_PCT}% TP | {bot.MAX_HOLD_MINUTES}min max hold")
    print(f"Window: {bot.EARLIEST_ENTRY} - {bot.LATEST_ENTRY} IST")
    print(f"Strike: ATM only (max {bot.MAX_DISTANCE_FROM_ATM} pts away)")
    print()
    
    # Status check
    status = bot.scan()
    print(f"Scan result: {json.dumps(status, indent=2)}")

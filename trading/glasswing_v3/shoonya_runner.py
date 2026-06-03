"""
Glasswing v3 + Shoonya Paper Broker — Live paper trading runner
Uses real NIFTY data via Yahoo Finance + Shoonya zero-brokerage paper mode.
"""

import json
import time
import sys
from datetime import datetime
from pathlib import Path

# Import both modules
sys.path.insert(0, str(Path(__file__).parent.parent))
from glasswing_v3.glasswing_v3 import GlasswingV3
from shoonya_paper_trader import ShoonyaPaperBroker


class GlasswingShoonyaRunner:
    """Glasswing v3 strategy + Shoonya paper broker integration."""
    
    def __init__(self):
        self.strategy = GlasswingV3(paper=True, capital=100000)
        self.broker = ShoonyaPaperBroker(paper=True)
        self.log = []
    
    def run_scan(self) -> dict:
        """Run one scan: check exits, check entries."""
        nifty = self.broker.get_nifty_spot()
        if nifty == 0:
            return {"status": "no_data"}
        
        time_str = datetime.now().strftime("%H:%M")
        
        # Check exits for positions in Glasswing
        exits = []
        for pos in list(self.strategy.positions):
            current = self.broker.estimate_premium(nifty, pos["strike"], pos["type"], time_str)
            exit_reason = self.strategy.check_exit(pos, current)
            if exit_reason:
                # Close via broker
                close_result = self.broker.place_order(
                    f"NIFTY {pos['strike']} {pos['type']}",
                    f"SELL_{pos['type']}",
                    pos["strike"],
                    pos["qty"]
                )
                trade = self.strategy.exit_trade(pos, exit_reason, current)
                exits.append(trade)
        
        # Check for new entries
        entries = []
        signal = self.strategy.check_entry_signal(nifty, [nifty] * 5)
        if signal:
            # Validate with broker
            opt_type = "CE" if signal["action"] == "BUY_CE" else "PE"
            if abs(nifty - signal["strike"]) <= self.strategy.MAX_DISTANCE_FROM_ATM:
                order_result = self.broker.place_order(
                    f"NIFTY {signal['strike']} {opt_type}",
                    signal["action"],
                    signal["strike"],
                    self.strategy.LOT_SIZE
                )
                if order_result["status"] == "ok":
                    pos = self.strategy.enter_trade(signal)
                    if pos:
                        entries.append({
                            "order": order_result,
                            "position": pos,
                        })
        
        # Sync strategy positions with broker
        self.strategy.positions = [
            p for p in self.strategy.positions
            if any(bp["strike"] == p["strike"] and bp["type"] == p["type"]
                   for bp in self.broker.positions)
        ]
        
        return {
            "status": "ok",
            "nifty": nifty,
            "time": time_str,
            "exits": exits,
            "entries": entries,
            "strategy": self.strategy.get_status(),
            "broker": self.broker.get_account(),
        }
    
    def run_continuous(self, interval_sec: int = 60):
        """Run continuous scanning loop."""
        print("🦋 Glasswing v3 + Shoonya Paper Trader")
        print("="*60)
        print(f"Scanning every {interval_sec}s. Press Ctrl+C to stop.")
        print()
        
        try:
            while True:
                result = self.run_scan()
                if result["status"] == "ok":
                    print(f"[{result['time']}] NIFTY: ₹{result['nifty']:.2f} | "
                          f"Open: {result['strategy']['open_positions']} | "
                          f"P&L: ₹{result['strategy']['daily_pnl']:+.2f} | "
                          f"W/L: {result['strategy']['wins']}/{result['strategy']['losses']}")
                    for e in result["exits"]:
                        print(f"   EXIT: {e['type']} {e['strike']} → {e['reason']} "
                              f"P&L ₹{e['net_pnl']:+.2f}")
                    for entry in result["entries"]:
                        o = entry["order"]
                        print(f"   ENTRY: {o['symbol']} @ ₹{o['price']:.2f} "
                              f"(₹{o['value']:,.0f}, brokerage ₹0)")
                else:
                    print(f"[{datetime.now().strftime('%H:%M')}] No data")
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\n\nFinal Status:")
            print(json.dumps(self.strategy.get_status(), indent=2))


if __name__ == "__main__":
    runner = GlasswingShoonyaRunner()
    
    if len(sys.argv) > 1 and sys.argv[1] == "loop":
        interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        runner.run_continuous(interval)
    else:
        # Single scan
        print("🦋 Glasswing v3 + Shoonya Paper Trader (Single Scan)")
        print("="*60)
        result = runner.run_scan()
        print(json.dumps(result, indent=2))

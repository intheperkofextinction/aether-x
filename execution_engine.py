import time
import numpy as np

class HighFrequencyMatchingEngine:
    """
    Simulated Low-Latency Execution & Matching Engine.
    Models order queue priority, slippage, trade execution fills, and real-time PnL.
    """
    def __init__(self, initial_capital: float = 100_000.0, maker_fee: float = 0.0001):
        self.cash = initial_capital
        self.position = 0          # Number of units held (+ is Long, - is Short)
        self.entry_price = 0.0     # Average fill price
        self.realized_pnl = 0.0
        self.maker_fee = maker_fee # 0.01% fee per trade
        
        # Performance Tracking
        self.trade_history = []

    def process_signal(self, signal: str, best_bid: float, best_ask: float, quantity: int = 1):
        """
        Processes buy/sell signals with realistic execution slippage and fill simulation.
        
        signal: 'BUY', 'SELL', or 'HOLD'
        """
        if signal == "HOLD" or best_bid <= 0 or best_ask <= 0:
            return

        timestamp = time.perf_counter_ns()

        if signal == "BUY" and self.position <= 0:
            # Assume cross spread for aggressive fill (Market Order with slippage)
            fill_price = best_ask * 1.00005  # 0.5 bps execution slippage
            cost = fill_price * quantity
            fee = cost * self.maker_fee

            # Close short position if open
            if self.position < 0:
                pnl = (self.entry_price - fill_price) * abs(self.position) - fee
                self.realized_pnl += pnl
                self.cash += (self.entry_price * abs(self.position)) + pnl
                self.position = 0

            # Open Long
            self.cash -= (cost + fee)
            self.position = quantity
            self.entry_price = fill_price

            self.trade_history.append({
                "timestamp": timestamp, "side": "BUY", "price": fill_price, "qty": quantity
            })

        elif signal == "SELL" and self.position >= 0:
            # Assume cross spread for aggressive fill
            fill_price = best_bid * 0.99995  # 0.5 bps execution slippage
            revenue = fill_price * quantity
            fee = revenue * self.maker_fee

            # Close long position if open
            if self.position > 0:
                pnl = (fill_price - self.entry_price) * self.position - fee
                self.realized_pnl += pnl
                self.cash += revenue - fee
                self.position = 0

            # Open Short
            self.cash += (revenue - fee)
            self.position = -quantity
            self.entry_price = fill_price

            self.trade_history.append({
                "timestamp": timestamp, "side": "SELL", "price": fill_price, "qty": quantity
            })

    def get_unrealized_pnl(self, current_mid_price: float) -> float:
        """Calculates mark-to-market unrealized gain/loss."""
        if self.position > 0:
            return (current_mid_price - self.entry_price) * self.position
        elif self.position < 0:
            return (self.entry_price - current_mid_price) * abs(self.position)
        return 0.0

    def get_account_summary(self, current_mid_price: float) -> dict:
        u_pnl = self.get_unrealized_pnl(current_mid_price)
        total_pnl = self.realized_pnl + u_pnl
        
        return {
            "Cash Balance": f"${self.cash:,.2f}",
            "Current Position": self.position,
            "Entry Price": f"${self.entry_price:,.2f}",
            "Realized PnL": f"${self.realized_pnl:,.2f}",
            "Unrealized PnL": f"${u_pnl:,.2f}",
            "Net Total PnL": f"${total_pnl:,.2f}",
            "Total Trades Executed": len(self.trade_history)
        }


# -------------------------------------------------------------------
# Quick Simulation Verification
# -------------------------------------------------------------------
if __name__ == "__main__":
    engine = HighFrequencyMatchingEngine(initial_capital=100_000.0)
    
    print("[*] Running Execution Engine Warmup...")
    
    # Simulate a Buy Signal on BTC at $63,720 / $63,721
    engine.process_signal(signal="BUY", best_bid=63720.0, best_ask=63721.0, quantity=1)
    
    # Mid-price ticks up to $63,800
    mid_price = 63800.0
    print("\n--- Account Snapshot (Open Long Position) ---")
    for k, v in engine.get_account_summary(mid_price).items():
        print(f"{k}: {v}")
        
    # Simulate Sell Signal to lock in profit
    engine.process_signal(signal="SELL", best_bid=63810.0, best_ask=63811.0, quantity=1)
    
    print("\n--- Account Snapshot (After Position Exit) ---")
    for k, v in engine.get_account_summary(63810.0).items():
        print(f"{k}: {v}")

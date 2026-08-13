import time
import numpy as np
import polars as pl
import pyarrow as pa
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

from memory_arena import ZeroAllocationArena
from order_book import update_limit_order_book, MAX_DEPTH
from ws_ingestion import LiveMarketIngestion
from execution_engine import HighFrequencyMatchingEngine

console = Console()

# -------------------------------------------------------------------
# Fast Vectorized OFI Signal Extraction
# -------------------------------------------------------------------
def calculate_ofi_signal(bids, asks) -> tuple[str, float]:
    """
    Computes real-time Order Flow Imbalance (OFI) on top of book levels.
    Returns: (signal_type, ofi_value)
    """
    best_bid_p = bids[0, 0]
    best_bid_q = bids[0, 1]
    best_ask_p = asks[0, 0]
    best_ask_q = asks[0, 1]

    if best_bid_p == 0 or best_ask_p == 0:
        return "HOLD", 0.0

    # Volume Imbalance Ratio
    tot_vol = best_bid_q + best_ask_q
    if tot_vol == 0:
        return "HOLD", 0.0

    imbalance = (best_bid_q - best_ask_q) / tot_vol

    # Generate signals on extreme imbalance thresholds
    if imbalance > 0.35:
        return "BUY", imbalance
    elif imbalance < -0.35:
        return "SELL", imbalance
    
    return "HOLD", imbalance


# -------------------------------------------------------------------
# Dashboard Rendering Engine
# -------------------------------------------------------------------
def build_book_table(bids, asks) -> Table:
    table = Table(title="[bold green]Live L2/L3 Limit Order Book (BTC-USD)[/bold green]", expand=True)
    table.add_column("Bid Size", justify="right", style="cyan")
    table.add_column("Bid Price", justify="right", style="bold green")
    table.add_column("Ask Price", justify="left", style="bold red")
    table.add_column("Ask Size", justify="left", style="magenta")

    for i in range(5):
        b_p = f"${bids[i, 0]:,.2f}" if bids[i, 0] > 0 else "-"
        b_q = f"{int(bids[i, 1])}" if bids[i, 1] > 0 else "-"
        a_p = f"${asks[i, 0]:,.2f}" if asks[i, 0] > 0 else "-"
        a_q = f"{int(asks[i, 1])}" if asks[i, 1] > 0 else "-"
        table.add_row(b_q, b_p, a_p, a_q)

    return table


def build_account_panel(summary: dict, ofi_val: float, latencies_ns: list) -> Panel:
    text = Text()
    text.append("--- Microstructure Alpha Signal ---\n", style="bold yellow")
    text.append(f"• Real-Time Imbalance Ratio: {ofi_val:+.3f}\n\n", style="cyan")
    
    text.append("--- Execution Engine Status ---\n", style="bold yellow")
    for k, v in summary.items():
        style = "bold green" if "Total PnL" in k and "$" in str(v) and "-" not in str(v) else "bold white"
        text.append(f"• {k}: {v}\n", style=style)

    if len(latencies_ns) > 0:
        lat_us = np.array(latencies_ns[-100:]) / 1000.0
        text.append("\n--- Hardware Latency Metrics ---\n", style="bold yellow")
        text.append(f"• Mean Mutation Latency: {np.mean(lat_us):.3f} µs\n", style="white")
        text.append(f"• P99 Tail Latency:     {np.percentile(lat_us, 99):.3f} µs\n", style="bold red")

    return Panel(text, title="[bold cyan]System Control & Risk Metrics[/bold cyan]")


# -------------------------------------------------------------------
# System Launcher
# -------------------------------------------------------------------
def main():
    arena = ZeroAllocationArena(capacity=100_000)
    ingestor = LiveMarketIngestion(arena=arena, symbol="BTC-USD")
    matching_engine = HighFrequencyMatchingEngine(initial_capital=100_000.0)

    bids = np.zeros((MAX_DEPTH, 2), dtype=np.float64)
    asks = np.zeros((MAX_DEPTH, 2), dtype=np.float64)

    # Numba JIT Warmup
    update_limit_order_book(bids, asks, 60000.0, 1, 0, 0)
    bids.fill(0)
    asks.fill(0)

    ingestor.start()
    time.sleep(2)  # Allow WebSocket socket connection warmup

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="body", ratio=1)
    )
    layout["body"].split_row(
        Layout(name="book", ratio=1),
        Layout(name="metrics", ratio=1)
    )

    header_panel = Panel(
        "[bold cyan]PROJECT AETHER-X: PRODUCTION LIVE TRADING ENGINE[/bold cyan]\n"
        "[dim]Coinbase WS Stream | Zero-Alloc Arena | Numba LOB | Polars Alpha | Execution Engine[/dim]",
        style="bold white on blue"
    )
    layout["header"].update(header_panel)

    processed_head = 0
    latencies = []

    with Live(layout, refresh_per_second=12) as live:
        try:
            while True:
                # Read new incoming ticks from ring buffer
                current_head = arena.head
                if processed_head < current_head:
                    buffer = arena.arena
                    
                    for idx in range(processed_head, current_head):
                        tick_idx = idx % arena.capacity
                        tick = buffer[tick_idx]
                        
                        t0 = time.perf_counter_ns()
                        update_limit_order_book(
                            bids, asks, 
                            tick['price'], tick['quantity'], 
                            tick['side'], tick['action']
                        )
                        t1 = time.perf_counter_ns()
                        latencies.append(t1 - t0)

                    processed_head = current_head

                # Signal Evaluation & Order Execution
                best_bid = bids[0, 0]
                best_ask = asks[0, 0]
                mid_price = (best_bid + best_ask) / 2.0 if (best_bid > 0 and best_ask > 0) else 63000.0

                signal, ofi_val = calculate_ofi_signal(bids, asks)
                matching_engine.process_signal(signal, best_bid, best_ask, quantity=1)

                # UI Updates
                summary = matching_engine.get_account_summary(mid_price)
                layout["book"].update(build_book_table(bids, asks))
                layout["metrics"].update(build_account_panel(summary, ofi_val, latencies))

                time.sleep(0.05)

        except KeyboardInterrupt:
            print("\n[*] Engine Terminated Safely.")


if __name__ == "__main__":
    main()

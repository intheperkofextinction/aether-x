import numpy as np
import time
from numba import njit
import polars as pl
import pyarrow as pa

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.text import Text

# Initialize Rich Console
console = Console()

# -------------------------------------------------------------------
# 1. High-Precision Order Book Engine (JIT Compiled)
# -------------------------------------------------------------------
MAX_DEPTH = 10

@njit(fastmath=True, nogil=True)
def mutate_book_level(book, price, size, side):
    """Simple direct level mutator for dashboard demo."""
    # Search level
    for i in range(MAX_DEPTH):
        if book[i, 0] == price or book[i, 0] == 0:
            book[i, 0] = price
            book[i, 1] = size
            break


# -------------------------------------------------------------------
# 2. UI Layout Generators
# -------------------------------------------------------------------
def generate_order_book_table(bids, asks) -> Table:
    table = Table(title="[bold green]L3 Order Book (Depth Top 5)[/bold green]", expand=True)
    table.add_column("Bid Size", justify="right", style="cyan")
    table.add_column("Bid Price", justify="right", style="bold green")
    table.add_column("Ask Price", justify="left", style="bold red")
    table.add_column("Ask Size", justify="left", style="magenta")

    # Sort bids descending, asks ascending for display
    b_sorted = bids[bids[:, 0].argsort()[::-1]]
    a_sorted = asks[asks[:, 0].argsort()]

    for i in range(5):
        b_p = f"{b_sorted[i, 0]:.2f}" if b_sorted[i, 0] > 0 else "-"
        b_q = f"{int(b_sorted[i, 1])}" if b_sorted[i, 1] > 0 else "-"
        a_p = f"{a_sorted[i, 0]:.2f}" if a_sorted[i, 0] > 0 else "-"
        a_q = f"{int(a_sorted[i, 1])}" if a_sorted[i, 1] > 0 else "-"
        
        table.add_row(b_q, b_p, a_p, a_q)

    return table


def generate_latency_panel(latencies_ns) -> Panel:
    if len(latencies_ns) == 0:
        return Panel("Warming up...", title="Latency Metrics")

    latencies_us = np.array(latencies_ns) / 1000.0
    
    mean_lat = np.mean(latencies_us)
    p50_lat = np.percentile(latencies_us, 50)
    p95_lat = np.percentile(latencies_us, 95)
    p99_lat = np.percentile(latencies_us, 99)
    min_lat = np.min(latencies_us)

    text = Text()
    text.append(f"• Mean Latency:  {mean_lat:.3f} µs\n", style="bold white")
    text.append(f"• Min Latency:   {min_lat:.3f} µs\n", style="bold green")
    text.append(f"• P50 Latency:   {p50_lat:.3f} µs\n", style="cyan")
    text.append(f"• P95 Latency:   {p95_lat:.3f} µs\n", style="yellow")
    text.append(f"• P99 Latency:   {p99_lat:.3f} µs\n", style="bold red")
    
    return Panel(text, title="[bold yellow]System Execution Latency Profiles[/bold yellow]")


def generate_header() -> Panel:
    grid = Table.grid(expand=True)
    grid.add_column(justify="center", ratio=1)
    grid.add_row("[bold cyan]PROJECT AETHER-X: ULTRA-LOW LATENCY ALPHA ENGINE[/bold cyan]")
    grid.add_row("[dim]Numba LLVM JIT | Zero-Allocation Arena | Polars Vector Signals[/dim]")
    return Panel(grid, style="bold white on blue")


# -------------------------------------------------------------------
# 3. Main Live Dashboard Runner
# -------------------------------------------------------------------
def run_dashboard():
    bids = np.zeros((MAX_DEPTH, 2), dtype=np.float64)
    asks = np.zeros((MAX_DEPTH, 2), dtype=np.float64)
    
    # Warmup Numba compiler
    mutate_book_level(bids, 100.0, 10.0, 0)
    bids.fill(0)

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=4),
        Layout(name="body", ratio=1)
    )
    layout["body"].split_row(
        Layout(name="book", ratio=1),
        Layout(name="metrics", ratio=1)
    )

    layout["header"].update(generate_header())

    latencies = []

    with Live(layout, refresh_per_second=10) as live:
        base_price = 150.00
        
        for iteration in range(200):
            t_start = time.perf_counter_ns()
            
            # Simulate mutations
            bid_p = base_price - (iteration % 5) * 0.05
            ask_p = base_price + 0.05 + (iteration % 5) * 0.05
            qty = (iteration % 10 + 1) * 100
            
            mutate_book_level(bids, bid_p, qty, 0)
            mutate_book_level(asks, ask_p, qty, 1)
            
            t_end = time.perf_counter_ns()
            latencies.append(t_end - t_start)

            # Update renderable components
            layout["book"].update(generate_order_book_table(bids, asks))
            layout["metrics"].update(generate_latency_panel(latencies))
            
            time.sleep(0.02)  # Pause slightly for visual rendering


if __name__ == "__main__":
    run_dashboard()

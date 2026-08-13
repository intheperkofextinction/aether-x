import numpy as np
import polars as pl
import pyarrow as pa
import time

# -------------------------------------------------------------------
# 1. Simulate Order Book Snapshots (Best Bid/Ask Price & Size)
# -------------------------------------------------------------------
def generate_mock_book_snapshots(n_samples: int = 100_000):
    np.random.seed(42)
    
    # Generate random price steps
    price_changes = np.random.choice([-0.01, 0.0, 0.01], size=n_samples, p=[0.25, 0.50, 0.25])
    
    bid_prices = 100.0 + np.cumsum(price_changes)
    ask_prices = bid_prices + 0.01  # Fixed 1-cent spread
    
    bid_sizes = np.random.randint(10, 500, size=n_samples).astype(np.float64)
    ask_sizes = np.random.randint(10, 500, size=n_samples).astype(np.float64)
    timestamps = np.arange(n_samples, dtype=np.uint64) + 1700000000000000000
    
    return timestamps, bid_prices, bid_sizes, ask_prices, ask_sizes


# -------------------------------------------------------------------
# 2. Ultra-Fast Vectorized OFI Calculation using Apache Arrow & Polars
# -------------------------------------------------------------------
def compute_vectorized_alpha(timestamps, bid_p, bid_q, ask_p, ask_q):
    # Zero-copy conversion from NumPy arrays to Apache Arrow Table
    arrow_table = pa.Table.from_arrays(
        [
            pa.array(timestamps),
            pa.array(bid_p),
            pa.array(bid_q),
            pa.array(ask_p),
            pa.array(ask_q)
        ],
        names=["timestamp", "bid_p", "bid_q", "ask_p", "ask_q"]
    )
    
    # Zero-copy wrap into Polars LazyFrame
    df = pl.from_arrow(arrow_table)
    
    # Vectorized compute using Polars Expressions
    result = df.with_columns([
        # Shift prices and quantities by 1 tick to get t-1
        pl.col("bid_p").shift(1).alias("prev_bid_p"),
        pl.col("bid_q").shift(1).alias("prev_bid_q"),
        pl.col("ask_p").shift(1).alias("prev_ask_p"),
        pl.col("ask_q").shift(1).alias("prev_ask_q"),
    ]).with_columns([
        # Delta Bid Flow
        pl.when(pl.col("bid_p") > pl.col("prev_bid_p"))
          .then(pl.col("bid_q"))
          .when(pl.col("bid_p") == pl.col("prev_bid_p"))
          .then(pl.col("bid_q") - pl.col("prev_bid_q"))
          .otherwise(-pl.col("prev_bid_q"))
          .alias("delta_b"),

        # Delta Ask Flow
        pl.when(pl.col("ask_p") < pl.col("prev_ask_p"))
          .then(pl.col("ask_q"))
          .when(pl.col("ask_p") == pl.col("prev_ask_p"))
          .then(pl.col("ask_q") - pl.col("prev_ask_q"))
          .otherwise(-pl.col("prev_ask_q"))
          .alias("delta_a"),

        # Volume Imbalance Ratio: (Bid Size - Ask Size) / (Bid Size + Ask Size)
        ((pl.col("bid_q") - pl.col("ask_q")) / (pl.col("bid_q") + pl.col("ask_q"))).alias("volume_imbalance")
    ]).with_columns([
        # Final Order Flow Imbalance (OFI)
        (pl.col("delta_b") - pl.col("delta_a")).alias("ofi")
    ])

    return result


if __name__ == "__main__":
    N = 100_000
    print(f"[*] Generating {N:,} mock order book snapshots...")
    timestamps, bid_p, bid_q, ask_p, ask_q = generate_mock_book_snapshots(N)
    
    start_time = time.perf_counter_ns()
    
    # Compute vector signals
    alpha_df = compute_vectorized_alpha(timestamps, bid_p, bid_q, ask_p, ask_q)
    
    end_time = time.perf_counter_ns()
    
    total_ms = (end_time - start_time) / 1e6
    per_snapshot_ns = (end_time - start_time) / N
    
    print("\n--- Module 3 Benchmark Results ---")
    print(f"Total Processing Time for {N:,} Ticks: {total_ms:.2f} ms")
    print(f"Average Alpha Latency: {per_snapshot_ns:.2f} ns per tick signal calculation")
    
    print("\nSample Computed Microstructure Signals:")
    print(alpha_df[["timestamp", "bid_p", "ask_p", "volume_imbalance", "ofi"]].head(5))

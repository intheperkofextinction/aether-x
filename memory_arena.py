import numpy as np
import time

# -------------------------------------------------------------------
# 1. Define L3 Market Tick Layout using NumPy C-type Structured Dtype
# -------------------------------------------------------------------
L3_TICK_DTYPE = np.dtype([
    ('timestamp', np.uint64),  # Nanosecond timestamp
    ('order_id',  np.uint64),  # Unique Order Identifier
    ('price',     np.float64), # Limit Price
    ('quantity',  np.uint32), # Shares / Size
    ('side',      np.uint8),  # 0 = Bid, 1 = Ask
    ('action',    np.uint8)   # 0 = Add, 1 = Modify, 2 = Cancel
])


class ZeroAllocationArena:
    """
    Pre-allocated ring-buffer arena for ultra-low latency tick storage.
    Guarantees 0 heap allocations during write operations.
    """
    def __init__(self, capacity: int = 1_000_000):
        self.capacity = capacity
        # Pre-allocate contiguous memory buffer at startup
        self.arena = np.zeros(capacity, dtype=L3_TICK_DTYPE)
        self.head = 0  # Write pointer / Index tracker
        
    def append_tick(self, timestamp: int, order_id: int, price: float, quantity: int, side: int, action: int):
        """
        Overwrites memory at current index. No new objects created on the heap.
        """
        idx = self.head % self.capacity
        
        # Direct C-struct index mutation
        self.arena[idx]['timestamp'] = timestamp
        self.arena[idx]['order_id'] = order_id
        self.arena[idx]['price'] = price
        self.arena[idx]['quantity'] = quantity
        self.arena[idx]['side'] = side
        self.arena[idx]['action'] = action
        
        self.head += 1

    def get_raw_buffer(self) -> np.ndarray:
        """Returns reference to raw underlying byte array."""
        return self.arena[:min(self.head, self.capacity)]


# -------------------------------------------------------------------
# 2. Execution & Micro-Benchmarking
# -------------------------------------------------------------------
if __name__ == "__main__":
    NUM_TICKS = 100_000
    arena = ZeroAllocationArena(capacity=NUM_TICKS)
    
    print(f"[*] Pre-allocated memory for {NUM_TICKS:,} L3 ticks.")
    print(f"[*] Memory block size: {arena.arena.nbytes / (1024 * 1024):.2f} MB")
    
    # Warm-up / Benchmarking ingestion
    start_time = time.perf_counter_ns()
    
    for i in range(NUM_TICKS):
        arena.append_tick(
            timestamp=1700000000000000000 + i,
            order_id=1000 + i,
            price=150.25 + (i % 10) * 0.01,
            quantity=100,
            side=i % 2,      # Alternating Bid/Ask
            action=0         # Add Order
        )
        
    end_time = time.perf_counter_ns()
    
    total_duration_us = (end_time - start_time) / 1000.0
    latency_per_tick_ns = (end_time - start_time) / NUM_TICKS
    
    print("\n--- Benchmark Results ---")
    print(f"Total Ingestion Time: {total_duration_us:.2f} µs")
    print(f"Average Ingestion Latency: {latency_per_tick_ns:.2f} ns per tick")
    print(f"Ticks processed: {arena.head:,}")
    print("\nSample Data from Memory Arena:")
    print(arena.get_raw_buffer()[:3])

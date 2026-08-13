import numpy as np
from numba import njit
import time

# Define array capacities
MAX_DEPTH = 500  # Fixed depth for bid/ask levels

# -------------------------------------------------------------------
# Core Order Book Logic JIT-Compiled directly to LLVM Assembly
# -------------------------------------------------------------------
@njit(fastmath=True, nogil=True)
def update_limit_order_book(bids, asks, price, quantity, side, action):
    """
    Mutates bid/ask arrays directly in memory without Python Interpreter / GIL.
    
    side: 0 = Bid, 1 = Ask
    action: 0 = Add, 1 = Cancel/Reduce
    """
    book = bids if side == 0 else asks
    
    # 1. Look for existing price level
    found_idx = -1
    for i in range(MAX_DEPTH):
        if book[i, 0] == price:
            found_idx = i
            break
        if book[i, 0] == 0:  # Empty slot reached
            break

    # 2. Add or Update Order Quantity
    if action == 0:  # Add
        if found_idx != -1:
            book[found_idx, 1] += quantity
        else:
            # Find first empty slot
            for i in range(MAX_DEPTH):
                if book[i, 0] == 0:
                    book[i, 0] = price
                    book[i, 1] = quantity
                    break

    # 3. Cancel / Reduce Order Quantity
    elif action == 1:  # Cancel
        if found_idx != -1:
            if book[found_idx, 1] <= quantity:
                # Clear level and shift up remaining levels
                book[found_idx, 0] = 0.0
                book[found_idx, 1] = 0.0
            else:
                book[found_idx, 1] -= quantity

    # 4. In-place sorting to keep book structured
    # Bids sorted descending, Asks sorted ascending
    if side == 0:
        # Simple insertion sort for bids
        for i in range(1, MAX_DEPTH):
            key_p = book[i, 0]
            key_q = book[i, 1]
            if key_p == 0:
                continue
            j = i - 1
            while j >= 0 and (book[j, 0] < key_p or book[j, 0] == 0):
                book[j + 1, 0] = book[j, 0]
                book[j + 1, 1] = book[j, 1]
                j -= 1
            book[j + 1, 0] = key_p
            book[j + 1, 1] = key_q
    else:
        # Simple insertion sort for asks
        for i in range(1, MAX_DEPTH):
            key_p = book[i, 0]
            key_q = book[i, 1]
            if key_p == 0:
                continue
            j = i - 1
            while j >= 0 and (book[j, 0] > key_p or book[j, 0] == 0):
                book[j + 1, 0] = book[j, 0]
                book[j + 1, 1] = book[j, 1]
                j -= 1
            book[j + 1, 0] = key_p
            book[j + 1, 1] = key_q


# -------------------------------------------------------------------
# Benchmark Comparison: Python Warmup vs JIT Native Speed
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Fixed memory pre-allocation
    bids = np.zeros((MAX_DEPTH, 2), dtype=np.float64)
    asks = np.zeros((MAX_DEPTH, 2), dtype=np.float64)

    # 1. Warm-up pass (Triggers Numba LLVM Compilation)
    print("[*] Compiling Order Book function with LLVM...")
    update_limit_order_book(bids, asks, 100.0, 10, 0, 0)
    print("[*] Compilation complete!\n")

    # Reset book state
    bids.fill(0)
    asks.fill(0)

    NUM_OPERATIONS = 100_000

    # Benchmark compiled speed
    start_time = time.perf_counter_ns()

    for i in range(NUM_OPERATIONS):
        side = i % 2
        price = 150.0 + (i % 20) * 0.25
        qty = 50 + (i % 5) * 10
        action = 0 if (i % 3 != 0) else 1  # Mix adds and cancels
        
        update_limit_order_book(bids, asks, price, qty, side, action)

    end_time = time.perf_counter_ns()

    total_us = (end_time - start_time) / 1000.0
    latency_ns = (end_time - start_time) / NUM_OPERATIONS

    print("--- Module 2 Benchmark Results ---")
    print(f"Total Operations: {NUM_OPERATIONS:,}")
    print(f"Total Time: {total_us:.2f} µs")
    print(f"Average Order Book Mutation Latency: {latency_ns:.2f} ns per update")
    
    print("\nTop 3 Bid Levels [Price, Size]:")
    print(bids[:3])
    print("\nTop 3 Ask Levels [Price, Size]:")
    print(asks[:3])

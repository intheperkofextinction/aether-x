import time
import numpy as np
from order_book import update_limit_order_book as numba_lob, MAX_DEPTH
import aether_cpp_core

def benchmark_lob():
    N_ITERATIONS = 50_000

    # Allocate books
    bids_numba = np.zeros((MAX_DEPTH, 2), dtype=np.float64)
    asks_numba = np.zeros((MAX_DEPTH, 2), dtype=np.float64)

    bids_cpp = np.zeros((MAX_DEPTH, 2), dtype=np.float64)
    asks_cpp = np.zeros((MAX_DEPTH, 2), dtype=np.float64)

    # Synthetic tick updates
    prices = np.random.uniform(63000.0, 64000.0, N_ITERATIONS)
    quantities = np.random.randint(1, 100, N_ITERATIONS)
    sides = np.random.choice([0, 1], N_ITERATIONS)
    actions = np.random.choice([0, 2], N_ITERATIONS)

    # 1. Warmup
    numba_lob(bids_numba, asks_numba, 63500.0, 10, 0, 0)
    aether_cpp_core.update_limit_order_book(bids_cpp, asks_cpp, 63500.0, 10, 0, 0)

    # 2. Benchmark Numba JIT
    t0 = time.perf_counter_ns()
    for i in range(N_ITERATIONS):
        numba_lob(bids_numba, asks_numba, prices[i], quantities[i], sides[i], actions[i])
    t1 = time.perf_counter_ns()
    numba_avg_ns = (t1 - t0) / N_ITERATIONS

    # 3. Benchmark Native C++ Extension
    t0 = time.perf_counter_ns()
    for i in range(N_ITERATIONS):
        aether_cpp_core.update_limit_order_book(bids_cpp, asks_cpp, prices[i], quantities[i], sides[i], actions[i])
    t1 = time.perf_counter_ns()
    cpp_avg_ns = (t1 - t0) / N_ITERATIONS

    print("\n" + "="*50)
    print("      AETHER-X HARDWARE LATENCY BENCHMARK        ")
    print("="*50)
    print(f"• Total Iterations Processed: {N_ITERATIONS:,}")
    print(f"• Numba LLVM JIT Engine : {numba_avg_ns / 1000.0:.4f} µs per mutation")
    print(f"• Native C++20 Core     : {cpp_avg_ns / 1000.0:.4f} µs per mutation")
    print("-" * 50)
    
    speedup = numba_avg_ns / cpp_avg_ns if cpp_avg_ns > 0 else 0
    print(f"🚀 C++ Core Performance Multiplier: {speedup:.2f}x Faster")
    print("="*50 + "\n")

if __name__ == "__main__":
    benchmark_lob()

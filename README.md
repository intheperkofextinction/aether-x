# ⚡ Project Aether-X: Ultra-Low Latency Order Book & Execution Engine

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![C++](https://img.shields.io/badge/C++-20-00599C?style=flat&logo=cplusplus&logoColor=white)
![pybind11](https://img.shields.io/badge/pybind11-v2.12-blue?style=flat)
![Build](https://img.shields.io/badge/GCC/g++-v11+-green?style=flat)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**Aether-X** is a high-performance quantitative trading engine built from scratch. It features real-time WebSocket market data ingestion, a zero-heap-allocation memory arena, an order book mutation core written in **Modern C++20 (via pybind11)**, vectorized Order Flow Imbalance (OFI) alpha signals, and a simulated matching engine with real-time slippage & PnL accounting.

---

##  Key Systems Architecture

```text
[ Coinbase Live WS ] ──> Dedicated Socket Thread
                               │
                               ▼
                 [ Zero-Allocation Memory Arena ]
                               │
            ┌──────────────────┴──────────────────┐
            ▼                                     ▼
 [ Numba LLVM JIT Engine ]               [ Native C++20 Core ]
       (~3.79 µs/op)                         (~1.84 µs/op)
            │                                     │
            └──────────────────┬──────────────────┘
                               ▼
                 [ Vectorized OFI Signal Engine ]
                               │
                               ▼
               [ Matching & Execution Engine ]
                               │
                               ▼
                 [ Terminal Profiling Dashboard ]
```

---

##  Benchmark Performance Summary

Benchmarked across **50,000 continuous limit order book mutations**:

| Implementation Engine | Average Execution Latency | Performance Multiplier |
| :--- | :--- | :--- |
| **Numba LLVM JIT** | `3.7931 µs` | `1.00x` |
| **Native C++20 Core (pybind11)** | **`1.8445 µs`** | **`2.06x Faster`**  |

---

##  Module Breakdown

1. **`memory_arena.py`**: Pre-allocated C-struct NumPy ring buffer eliminating runtime Garbage Collection (GC) latency pauses.
2. **`order_book_cpp.cpp`**: Ultra-low latency L3 Limit Order Book compiled via C++20 with `-O3 -march=native` CPU optimizations.
3. **`ws_ingestion.py`**: Multi-threaded WebSocket client streaming live level-2 market depth from Coinbase Pro.
4. **`execution_engine.py`**: High-frequency matching engine with order priority queue modeling, slippage simulation, and PnL metrics.
5. **`main.py`**: Production orchestrator featuring dynamic C++20 engine selection with Numba fallback, rendering real-time terminal diagnostics, OFI signals, and hardware latency profile distributions.

---

##  Production Live Terminal Dashboard

![Aether-X Live Dashboard](https://github.com/user-attachments/assets/dc26aa4a-a8b8-41c6-8a46-4c86fa802701)

##  Building & Running

### Requirements
* **GCC / g++** with C++17 or C++20 support
* **Python 3.10+**

### Setup & Compilation

```bash
# 1. Clone repository
git clone [https://github.com/YOUR_USERNAME/aether-x.git](https://github.com/YOUR_USERNAME/aether-x.git)
cd aether-x

# 2. Create virtual environment & install requirements
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Compile C++ Order Book Core Extension
python setup.py build_ext --inplace

# 4. Run Hardware Latency Benchmark
python benchmark.py

# 5. Launch Production Live Engine
python main.py

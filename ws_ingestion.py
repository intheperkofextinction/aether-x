import json
import time
import threading
import websocket
import numpy as np

from memory_arena import ZeroAllocationArena, L3_TICK_DTYPE

class LiveMarketIngestion:
    """
    High-throughput WebSocket ingestor.
    Connects to live Coinbase L2/L3 order book stream and streams updates into Memory Arena.
    """
    def __init__(self, arena: ZeroAllocationArena, symbol: str = "BTC-USD"):
        self.arena = arena
        self.symbol = symbol
        self.ws_url = "wss://ws-feed.exchange.coinbase.com"
        self.ws = None
        self.thread = None
        self.running = False
        self.tick_count = 0

    def _on_message(self, ws, message):
        """Callback executed on every incoming network frame."""
        t_recv = time.perf_counter_ns()
        data = json.loads(message)
        
        msg_type = data.get("type")
        
        if msg_type == "l2update":
            changes = data.get("changes", [])
            for change in changes:
                side_str, price_str, size_str = change
                
                side = 0 if side_str == "buy" else 1
                price = float(price_str)
                size = float(size_str)
                
                # Action: 0 = Add/Update, 2 = Delete (if size == 0)
                action = 2 if size == 0.0 else 0
                
                # Fast direct memory store
                self.arena.append_tick(
                    timestamp=t_recv,
                    order_id=self.tick_count,
                    price=price,
                    quantity=int(size * 1000), # Store scale integer for accuracy
                    side=side,
                    action=action
                )
                self.tick_count += 1

    def _on_open(self, ws):
        print(f"[*] WebSocket Connected to Coinbase. Subscribing to {self.symbol}...")
        subscribe_msg = {
            "type": "subscribe",
            "product_ids": [self.symbol],
            "channels": ["level2_batch"]
        }
        ws.send(json.dumps(subscribe_msg))

    def _on_error(self, ws, error):
        print(f"[!] WebSocket Error: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print("[*] WebSocket Connection Closed.")

    def start(self):
        """Launches the socket loop in a dedicated background thread."""
        self.running = True
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close
        )
        self.thread = threading.Thread(target=self.ws.run_forever, daemon=True)
        self.thread.start()


# -------------------------------------------------------------------
# Benchmark Live Ingestion into Memory Arena
# -------------------------------------------------------------------
if __name__ == "__main__":
    # Pre-allocate memory for 50,000 live ticks
    arena = ZeroAllocationArena(capacity=50_000)
    ingestor = LiveMarketIngestion(arena=arena, symbol="BTC-USD")
    
    print("[*] Starting Live Ingestion Engine...")
    ingestor.start()
    
    # Run ingestion for 10 seconds
    try:
        for i in range(10):
            time.sleep(1)
            print(f"[+] Live Ticks Streamed into Memory: {ingestor.tick_count:,} ticks")
    except KeyboardInterrupt:
        pass
        
    print("\n--- Live Data Sample in Pre-Allocated Ring Buffer ---")
    active_buffer = arena.get_raw_buffer()
    print(active_buffer[:5])
